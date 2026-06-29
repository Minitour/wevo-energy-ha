from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_BASE_URL,
    CONF_CHARGER_IDENTIFIER,
    CONF_COGNITO_CLIENT_ID,
    CONF_COGNITO_USERNAME,
    CONF_COGNITO_REGION,
    CONF_CONNECTOR,
    CONF_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TOKEN_REFRESH_MARGIN_SECONDS,
)
from .wevo_api import WevoApiClient, WevoApiError


def _monthly_energy_kwh(transactions: list[dict[str, Any]]) -> tuple[float, int]:
    """Sum totalEnergyKwh for transactions that started in the current local month.

    The session start (``plugInTime``) is epoch milliseconds. Returns
    (total_kwh, session_count).
    """
    now = dt_util.now()
    total = 0.0
    count = 0

    for tx in transactions:
        plug_in = tx.get("plugInTime")
        if not isinstance(plug_in, (int, float)):
            continue

        when = dt_util.as_local(dt_util.utc_from_timestamp(plug_in / 1000))
        if when.year != now.year or when.month != now.month:
            continue

        try:
            total += float(tx.get("totalEnergyKwh") or 0)
        except (TypeError, ValueError):
            continue
        count += 1

    return total, count


class WevoCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        data = entry.data

        self._access_token = data[CONF_ACCESS_TOKEN]
        self._refresh_token = data.get(CONF_REFRESH_TOKEN)
        self._expires_at = int(data.get(CONF_EXPIRES_AT, 0))
        self._cognito_username = data.get(CONF_COGNITO_USERNAME, "")

        self._charger_identifier = data[CONF_CHARGER_IDENTIFIER]
        self._connector = str(data.get(CONF_CONNECTOR, 1))

        session = async_get_clientsession(hass)
        self._api = WevoApiClient(
            session=session,
            base_url=data[CONF_BASE_URL],
            cognito_region=data[CONF_COGNITO_REGION],
            cognito_client_id=data[CONF_COGNITO_CLIENT_ID],
        )

        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )

    async def _ensure_fresh_token(self) -> None:
        now = int(time.time())
        should_refresh = (
            self._refresh_token is not None
            and self._expires_at > 0
            and now >= (self._expires_at - TOKEN_REFRESH_MARGIN_SECONDS)
        )
        if not should_refresh:
            return

        tokens = await self._api.refresh_access_token(self._refresh_token, self._cognito_username)
        self._access_token = tokens.access_token
        self._expires_at = tokens.expires_at

        new_data = {
            **self.entry.data,
            CONF_ACCESS_TOKEN: self._access_token,
            CONF_EXPIRES_AT: self._expires_at,
        }
        self.hass.config_entries.async_update_entry(self.entry, data=new_data)

    async def authorize(self) -> None:
        await self._ensure_fresh_token()
        try:
            await self._api.authorize(self._access_token, self._charger_identifier, self._connector)
            await self.async_request_refresh()
        except WevoApiError as err:
            raise UpdateFailed(f"Authorize failed: {err}") from err

    async def _async_update_data(self) -> dict:
        await self._ensure_fresh_token()
        try:
            data = await self._api.get_state(self._access_token, self._charger_identifier, self._connector)

            tx = data.get("transactionData") or {}
            rate_kw = tx.get("rateKw")
            energy_kwh = tx.get("totalEnergyKwh")

            transactions = await self._api.get_transactions(self._access_token)
            if transactions:
                latest = transactions[0]
                if rate_kw in (None, 0, 0.0):
                    rate_kw = latest.get("avgRateKW")
                if energy_kwh in (None, 0, 0.0):
                    energy_kwh = latest.get("totalEnergyKwh")

            monthly_kwh, monthly_sessions = _monthly_energy_kwh(transactions)

            data["rate_kw"] = rate_kw
            data["total_energy_kwh"] = energy_kwh
            data["monthly_energy_kwh"] = monthly_kwh
            data["monthly_session_count"] = monthly_sessions
            return data
        except WevoApiError as err:
            raise UpdateFailed(str(err)) from err

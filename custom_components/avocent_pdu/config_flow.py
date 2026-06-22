"""Config flow for the Avocent PM3000 PDU integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_COMMUNITY,
    CONF_PDU_ID,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_COMMUNITY,
    DEFAULT_PDU_ID,
    DEFAULT_SCAN_INTERVAL,
)
from .sensor import AvocentPDUCoordinator


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=d.get(CONF_NAME, "PDU")): cv.string,
            vol.Required(CONF_HOST, default=d.get(CONF_HOST, "")): cv.string,
            vol.Optional(
                CONF_COMMUNITY, default=d.get(CONF_COMMUNITY, DEFAULT_COMMUNITY)
            ): cv.string,
            vol.Optional(CONF_PORT, default=d.get(CONF_PORT, DEFAULT_PORT)): cv.port,
            vol.Optional(
                CONF_PDU_ID, default=d.get(CONF_PDU_ID, DEFAULT_PDU_ID)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=d.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=10)),
        }
    )


class AvocentPDUConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Avocent PM3000 PDU."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a PDU via the UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = f"{user_input[CONF_HOST]}_{user_input[CONF_PDU_ID]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            if not await _test_connection(self.hass, user_input):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=_user_schema(user_input), errors=errors
        )

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Import a PDU from a legacy configuration.yaml sensor block."""
        unique_id = f"{import_data[CONF_HOST]}_{import_data[CONF_PDU_ID]}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=import_data.get(CONF_NAME, "PDU"), data=import_data
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return AvocentPDUOptionsFlow()


class AvocentPDUOptionsFlow(OptionsFlow):
    """Allow editing the scan interval after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=current
                    ): vol.All(vol.Coerce(int), vol.Range(min=10)),
                }
            ),
        )


async def _test_connection(hass, cfg: dict[str, Any]) -> bool:
    """Return True if a single poll of the PDU succeeds."""
    coordinator = AvocentPDUCoordinator(
        hass,
        host=cfg[CONF_HOST],
        port=cfg.get(CONF_PORT, DEFAULT_PORT),
        community=cfg.get(CONF_COMMUNITY, DEFAULT_COMMUNITY),
        pdu_id=cfg.get(CONF_PDU_ID, DEFAULT_PDU_ID),
        name=cfg.get(CONF_NAME, "PDU"),
        scan_interval=cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    try:
        await coordinator._fetch_all()
        return True
    except Exception:  # noqa: BLE001
        return False

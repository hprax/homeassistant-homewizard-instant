"""Config flow for HomeWizard Instant (API v2)."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components import onboarding
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector
import voluptuous as vol

from .api import AuthError, CreationNotEnabledError, HomeWizardEnergyV2, RequestError
from .const import CONF_PRODUCT_NAME, CONF_PRODUCT_TYPE, CONF_SERIAL, CONF_TOKEN, DOMAIN, LOGGER

# Only P1 meters support the v2 local API at this time.
SUPPORTED_PRODUCT_TYPES = ["HWE-P1"]

# Username registered on the device.  Must start with "local/".
_USER_NAME = "local/homeassistant"


class HomeWizardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeWizard Instant (API v2)."""

    # Bump to 2 so existing v1 entries are migrated / re-configured.
    VERSION = 2

    ip_address: str | None = None
    product_name: str | None = None
    product_type: str | None = None
    serial: str | None = None

    # ------------------------------------------------------------------
    # User-initiated (manual) flow
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1 – ask for the device's IP address."""
        errors: dict[str, str] = {}

        if user_input is not None:
            ip = user_input[CONF_IP_ADDRESS].strip()
            # Store the IP and move on to the authorization step.
            self.ip_address = ip
            return await self.async_step_authorize()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_IP_ADDRESS): TextSelector()}
            ),
            errors=errors,
        )

    async def async_step_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2 – press the button on the device, then submit to obtain a token."""
        errors: dict[str, str] = {}

        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            try:
                token = await HomeWizardEnergyV2.create_user(
                    host=self.ip_address,
                    name=_USER_NAME,
                    session=async_get_clientsession(self.hass),
                )
            except CreationNotEnabledError:
                errors["base"] = "button_not_pressed"
            except RequestError:
                errors["base"] = "network_error"
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Unexpected exception during authorization")
                raise AbortFlow("unknown_error")
            else:
                return await self._async_finish_setup(token)

        return self.async_show_form(
            step_id="authorize",
            description_placeholders={CONF_IP_ADDRESS: self.ip_address},
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Zeroconf (mDNS) discovery flow
    # ------------------------------------------------------------------

    async def async_step_zeroconf(self, discovery_info: Any) -> ConfigFlowResult:
        """Handle Zeroconf discovery."""
        if (
            CONF_PRODUCT_NAME not in discovery_info.properties
            or CONF_PRODUCT_TYPE not in discovery_info.properties
            or CONF_SERIAL not in discovery_info.properties
        ):
            return self.async_abort(reason="invalid_discovery_parameters")

        product_type = discovery_info.properties[CONF_PRODUCT_TYPE]
        if product_type not in SUPPORTED_PRODUCT_TYPES:
            return self.async_abort(reason="device_not_supported")

        self.ip_address = discovery_info.host
        self.product_type = product_type
        self.product_name = discovery_info.properties[CONF_PRODUCT_NAME]
        self.serial = discovery_info.properties[CONF_SERIAL]

        await self.async_set_unique_id(f"{DOMAIN}_{self.product_type}_{self.serial}")
        self._abort_if_unique_id_configured(
            updates={CONF_IP_ADDRESS: discovery_info.host}
        )

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered device, then request button press to authorize."""
        if (
            self.ip_address is None
            or self.product_name is None
            or self.product_type is None
            or self.serial is None
        ):
            return self.async_abort(reason="unknown_error")

        self.context["title_placeholders"] = {"name": self.product_name}

        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            # User confirmed – move to the authorization (button press) step.
            return await self.async_step_authorize()

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                CONF_PRODUCT_TYPE: self.product_type,
                CONF_SERIAL: self.serial,
                CONF_IP_ADDRESS: self.ip_address,
            },
        )

    # ------------------------------------------------------------------
    # DHCP discovery – only updates the IP for existing entries
    # ------------------------------------------------------------------

    async def async_step_dhcp(self, discovery_info: Any) -> ConfigFlowResult:
        """Update the IP address of an already-configured device."""
        session = async_get_clientsession(self.hass)

        # We need a token to call the device API; at this point we don't have
        # one (DHCP fires before configuration).  Query the device to get its
        # serial so we can locate the existing entry.
        #
        # v2: try to get device info. Without a token we can't, so just try to
        # match by serial embedded in the unique_id if we have a discovered one.
        # Fall back to updating all entries for this host if we can't verify.
        ip = discovery_info.ip

        # Iterate existing entries; update IP if we find a matching one.
        for entry in self._async_current_entries():
            if entry.data.get(CONF_IP_ADDRESS) != ip:
                # Try to verify this is the same device by connecting with its token.
                try:
                    api = HomeWizardEnergyV2(
                        host=ip,
                        token=entry.data.get(CONF_TOKEN, ""),
                        session=session,
                    )
                    device = await api.get_device()
                    entry_serial = entry.unique_id or ""
                    if f"{DOMAIN}_{device.product_type}_{device.serial}" in entry_serial:
                        self._abort_if_unique_id_configured(
                            updates={CONF_IP_ADDRESS: ip}
                        )
                except Exception:  # noqa: BLE001
                    pass

        return self.async_abort(reason="unknown_error")

    # ------------------------------------------------------------------
    # Reconfigure – change the IP address (token stays)
    # ------------------------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow the user to update the device's IP address."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            ip = user_input[CONF_IP_ADDRESS].strip()
            try:
                api = HomeWizardEnergyV2(
                    host=ip,
                    token=reconfigure_entry.data[CONF_TOKEN],
                    session=async_get_clientsession(self.hass),
                )
                device = await api.get_device()
            except AuthError:
                errors["base"] = "invalid_token"
            except RequestError:
                errors["base"] = "network_error"
            else:
                await self.async_set_unique_id(
                    f"{DOMAIN}_{device.product_type}_{device.serial}"
                )
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates={CONF_IP_ADDRESS: ip},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IP_ADDRESS,
                        default=reconfigure_entry.data.get(CONF_IP_ADDRESS),
                    ): TextSelector()
                }
            ),
            description_placeholders={"title": reconfigure_entry.title},
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Re-auth – token was revoked; go through button-press again
    # ------------------------------------------------------------------

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when the stored token is no longer valid."""
        self.ip_address = entry_data[CONF_IP_ADDRESS]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Press button again to obtain a fresh token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                token = await HomeWizardEnergyV2.create_user(
                    host=self.ip_address,
                    name=_USER_NAME,
                    session=async_get_clientsession(self.hass),
                )
            except CreationNotEnabledError:
                errors["base"] = "button_not_pressed"
            except RequestError:
                errors["base"] = "network_error"
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Unexpected exception during re-auth")
                raise AbortFlow("unknown_error")
            else:
                reauth_entry = self._get_reauth_entry()
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_TOKEN: token},
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={CONF_IP_ADDRESS: self.ip_address},
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _async_finish_setup(self, token: str) -> ConfigFlowResult:
        """Fetch device info, set unique_id and create the config entry."""
        session = async_get_clientsession(self.hass)
        try:
            api = HomeWizardEnergyV2(
                host=self.ip_address,
                token=token,
                session=session,
            )
            device = await api.get_device()
        except (AuthError, RequestError) as err:
            LOGGER.error("Could not fetch device info after authorizing: %s", err)
            raise AbortFlow("unknown_error") from err

        if device.product_type not in SUPPORTED_PRODUCT_TYPES:
            return self.async_abort(reason="device_not_supported")

        await self.async_set_unique_id(
            f"{DOMAIN}_{device.product_type}_{device.serial}"
        )
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=device.product_name,
            data={
                CONF_IP_ADDRESS: self.ip_address,
                CONF_TOKEN: token,
            },
        )


class RecoverableError(HomeAssistantError):
    """Raised when a connection attempt failed but can be retried."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code

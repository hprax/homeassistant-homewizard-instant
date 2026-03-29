"""WebSocket-based update coordinator for HomeWizard Instant."""

from __future__ import annotations

import asyncio
import ssl

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthError, HomeWizardEnergyV2, RequestError
from .const import DOMAIN, LOGGER
from .models import DeviceResponseV2, MeasurementV2

type HomeWizardConfigEntry = ConfigEntry[HWInstantCoordinator]

# Seconds to wait before reconnecting after a WebSocket disconnect.
_WS_RECONNECT_DELAY = 5


class HWInstantCoordinator(DataUpdateCoordinator[DeviceResponseV2]):
    """Coordinator that fetches initial data via REST then streams updates over WebSocket."""

    api: HomeWizardEnergyV2
    config_entry: HomeWizardConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: HomeWizardConfigEntry,
        api: HomeWizardEnergyV2,
    ) -> None:
        """Initialise the coordinator (no polling interval – push only)."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            # update_interval intentionally omitted: data arrives via WebSocket.
        )
        self.api = api
        self._ws_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # DataUpdateCoordinator overrides
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> DeviceResponseV2:
        """Fetch initial data via REST and (re)start the WebSocket listener."""
        try:
            device = await self.api.get_device()
            system = await self.api.get_system()
            measurement = await self.api.get_measurement()
        except AuthError as err:
            raise UpdateFailed(str(err)) from err
        except RequestError as err:
            raise UpdateFailed(
                err, translation_domain=DOMAIN, translation_key="communication_error"
            ) from err

        data = DeviceResponseV2(device=device, measurement=measurement, system=system)

        # Start the WebSocket listener if it is not already running.
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = self.hass.async_create_background_task(
                self._async_run_websocket(),
                "homewizard_instant_websocket",
            )

        return data

    async def async_shutdown(self) -> None:
        """Cancel the WebSocket background task before shutting down."""
        self._cancel_ws_task()
        await super().async_shutdown()

    # ------------------------------------------------------------------
    # WebSocket management
    # ------------------------------------------------------------------

    def _cancel_ws_task(self) -> None:
        """Cancel the WebSocket task if it is running."""
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()

    async def _async_run_websocket(self) -> None:
        """Run the WebSocket loop with automatic reconnection."""
        while True:
            try:
                await self._async_websocket_session()
            except asyncio.CancelledError:
                LOGGER.debug("WebSocket task cancelled")
                return
            except Exception as err:  # noqa: BLE001
                LOGGER.warning(
                    "WebSocket disconnected, reconnecting in %ds: %s",
                    _WS_RECONNECT_DELAY,
                    err,
                )

            try:
                await asyncio.sleep(_WS_RECONNECT_DELAY)
            except asyncio.CancelledError:
                return

    async def _async_websocket_session(self) -> None:
        """Open one WebSocket session, authenticate, subscribe and process messages."""
        ws_ssl: ssl.SSLContext = ssl.create_default_context()
        ws_ssl.check_hostname = False
        ws_ssl.verify_mode = ssl.CERT_NONE

        async with self.api._session.ws_connect(
            self.api.websocket_url(),
            ssl=ws_ssl,
        ) as ws:
            LOGGER.debug("WebSocket connected to %s", self.api.websocket_url())

            # Step 1 – authenticate (must happen within 40 s).
            await ws.send_json({"type": "authorization", "data": self.api._token})

            # Step 2 – subscribe to measurement updates.
            await ws.send_json({"type": "subscribe", "data": "measurement"})

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_ws_message(msg.json())
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    LOGGER.debug("WebSocket closed/error: %s", msg.data)
                    break

    async def _handle_ws_message(self, msg: dict) -> None:
        """Parse and apply an incoming WebSocket message."""
        msg_type = msg.get("type")

        if msg_type == "error":
            LOGGER.warning("WebSocket error from device: %s", msg.get("data"))
            return

        if msg_type == "measurement":
            if self.data is None:
                return
            measurement = MeasurementV2.from_dict(msg.get("data") or {})
            self.async_set_updated_data(
                DeviceResponseV2(
                    device=self.data.device,
                    measurement=measurement,
                    system=self.data.system,
                )
            )

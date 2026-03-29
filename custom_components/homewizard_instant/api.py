"""HomeWizard Energy v2 API client."""

from __future__ import annotations

import ssl
from typing import Any, cast

import aiohttp

from .models import DeviceV2, MeasurementV2, SystemV2

# SSL context for HomeWizard self-signed certificates (local network only)
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

_HEADERS_BASE = {"X-Api-Version": "2"}


class HomeWizardError(Exception):
    """Base exception for HomeWizard v2 API errors."""


class RequestError(HomeWizardError):
    """Raised when an HTTP request fails (network or unexpected status)."""


class AuthError(HomeWizardError):
    """Raised when the stored token is rejected (401)."""


class CreationNotEnabledError(HomeWizardError):
    """Raised when token creation is not yet enabled (403 – button not pressed)."""


class HomeWizardEnergyV2:
    """Thin async client for the HomeWizard Energy local API v2."""

    def __init__(
        self,
        host: str,
        token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._host = host
        self._token = token
        self._session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {**_HEADERS_BASE, "Authorization": f"Bearer {self._token}"}

    async def _get(self, path: str) -> dict[str, Any]:
        """Perform an authenticated GET request."""
        try:
            async with self._session.get(
                f"https://{self._host}{path}",
                headers=self._auth_headers,
                ssl=_SSL_CONTEXT,
            ) as resp:
                if resp.status == 401:
                    raise AuthError("Token rejected by device")
                resp.raise_for_status()
                return cast(dict[str, Any], await resp.json())
        except AuthError:
            raise
        except aiohttp.ClientError as err:
            raise RequestError(f"Request to {path} failed: {err}") from err

    # ------------------------------------------------------------------
    # REST endpoints
    # ------------------------------------------------------------------

    async def get_device(self) -> DeviceV2:
        """Return device information from /api."""
        return DeviceV2.from_dict(await self._get("/api"))

    async def get_system(self) -> SystemV2:
        """Return system information from /api/system."""
        return SystemV2.from_dict(await self._get("/api/system"))

    async def get_measurement(self) -> MeasurementV2:
        """Return current measurement from /api/measurement."""
        return MeasurementV2.from_dict(await self._get("/api/measurement"))

    # ------------------------------------------------------------------
    # WebSocket
    # ------------------------------------------------------------------

    def websocket_url(self) -> str:
        """Return the WebSocket endpoint URL."""
        return f"wss://{self._host}/api/ws"

    # ------------------------------------------------------------------
    # Static helpers (used during onboarding, no token required)
    # ------------------------------------------------------------------

    @staticmethod
    async def create_user(
        host: str,
        name: str,
        session: aiohttp.ClientSession,
    ) -> str:
        """Request a new API token by posting to /api/user.

        Raises:
            CreationNotEnabledError: Device returned 403 – user must press the
                button on the device and then call this method again within
                30 seconds.
            RequestError: Network or unexpected HTTP error.
        """
        try:
            async with session.post(
                f"https://{host}/api/user",
                json={"name": name},
                headers=_HEADERS_BASE,
                ssl=_SSL_CONTEXT,
            ) as resp:
                if resp.status == 403:
                    raise CreationNotEnabledError(
                        "Token creation not enabled – press the button on the device"
                    )
                resp.raise_for_status()
                data = cast(dict[str, Any], await resp.json())
                return cast(str, data["token"])
        except (CreationNotEnabledError, AuthError):
            raise
        except aiohttp.ClientError as err:
            raise RequestError(f"Request to /api/user failed: {err}") from err

"""Abstract class to make authenticated requests."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError

from .const import TIMEOUT

_LOGGER = logging.getLogger(__name__)


class AbstractAuth(ABC):
    """Abstract class to make authenticated requests."""

    def __init__(self, websession: ClientSession) -> None:
        """Initialize the auth."""
        self.websession = websession

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def request(
        self,
        url: str,
        request_type: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Send a request to the Minut Point API."""
        request_kwargs = dict(kwargs)
        headers = dict(request_kwargs.pop("headers", {}) or {})

        access_token = await self.async_get_access_token()
        headers["authorization"] = f"Bearer {access_token}"

        try:
            _LOGGER.debug("Request %s %s %s", url, request_kwargs, headers)
            response = await self.websession.request(
                request_type,
                url,
                timeout=TIMEOUT.seconds,
                headers=headers,
                **request_kwargs,
            )
            response.raise_for_status()

            try:
                resp = await response.json()
            except ValueError:
                return None

            if not isinstance(resp, dict):
                return None

            _LOGGER.log(
                logging.NOTSET,
                "Response %s %s",
                response.status,
                response.headers.get("content-type"),
            )

            if "error" in resp:
                _LOGGER.error("Error for url: %s, %s", url, resp["error"])
            return resp
        except ClientConnectionError as error:
            _LOGGER.error("Client issue: %s", error)
            return None

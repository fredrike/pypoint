"""Abstract class to make authenticated requests."""

from abc import ABC, abstractmethod
import logging

from aiohttp import ClientResponse, ClientSession
from aiohttp.client_exceptions import ClientConnectionError

from .const import TIMEOUT

_LOGGER = logging.getLogger(__name__)


class AbstractAuth(ABC):
    """Abstract class to make authenticated requests."""

    def __init__(self, websession: ClientSession):
        """Initialize the auth."""
        self.websession = websession

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def request(self, url, request_type="GET", **kwargs) -> ClientResponse:
        """Send a request to the Minut Point API."""
        headers = kwargs.get("headers")

        if headers is None:
            headers = {}
        else:
            headers = dict(headers)

        access_token = await self.async_get_access_token()
        headers["authorization"] = f"Bearer {access_token}"

        try:
            _LOGGER.debug("Request %s %s %s", url, kwargs, headers)
            response = await self.websession.request(
                request_type, url, **kwargs, timeout=TIMEOUT.seconds, headers=headers
            )
            response.raise_for_status()
            resp = await response.json()
            _LOGGER.log(
                logging.NOTSET,
                "Response %s %s %s",
                response.status,
                response.headers["content-type"],
                resp.get("values")[-1]
                if kwargs.get("data") and resp.get("values")
                else response.text,
            )
            if "error" in resp:
                _LOGGER.error("Error for url: %s, %s", url, resp["error"])
            return resp
        except ClientConnectionError as error:
            _LOGGER.error("Client issue: %s", error)

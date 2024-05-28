"""Minut Point API."""

from datetime import timedelta
import logging

from threading import RLock

from aiohttp import ClientResponse, ClientSession
from aiohttp.client_exceptions import ClientConnectionError,ClientResponseError

_LOGGER = logging.getLogger(__name__)

MINUT_API_URL = "https://api.minut.com/v8/"
MINUT_AUTH_URL = MINUT_API_URL + "oauth/authorize"
MINUT_DEVICES_URL = MINUT_API_URL + "devices"
MINUT_USERS_URL = MINUT_API_URL + "users"
MINUT_TOKEN_URL = MINUT_API_URL + "oauth/token"
MINUT_WEBHOOKS_URL = MINUT_API_URL + "webhooks"
MINUT_HOMES_URL = MINUT_API_URL + "homes"

MAP_SENSORS = {
    "sound_pressure": "sound",
}

TIMEOUT = timedelta(seconds=10)

EVENTS = {
    "alarm": (  # On means alarm sound was recognised, Off means normal
        "alarm_heard",
        "alarm_silenced",
    ),
    "battery": ("battery_low", ""),  # On means low, Off means normal
    "button_press": (  # On means the button was pressed, Off means normal
        "short_button_press",
        "",
    ),
    "cold": (  # On means cold, Off means normal
        "temperature_low",
        "temperature_risen_normal",
    ),
    "connectivity": (  # On means connected, Off means disconnected
        "device_online",
        "device_offline",
    ),
    "dry": (  # On means too dry, Off means normal
        "humidity_low",
        "humidity_risen_normal",
    ),
    "glass": ("glassbreak", ""),  # The sound of glass break was detected
    "heat": (  # On means hot, Off means normal
        "temperature_high",
        "temperature_dropped_normal",
    ),
    "moisture": (  # On means wet, Off means dry
        "humidity_high",
        "humidity_dropped_normal",
    ),
    "motion": (  # On means motion detected, Off means no motion (clear)
        "pir_motion",
        "",
    ),
    "noise": (
        "disturbance_first_notice",  # The first alert of the noise monitoring
        "disturbance_ended",  # Created when the noise levels have gone back to normal
    ),
    "sound": (  # On means sound detected, Off means no sound (clear)
        "avg_sound_high",
        "sound_level_dropped_normal",
    ),
    "tamper_old": ("tamper", ""),  # On means the point was removed or attached
    "tamper": (
        "tamper_removed",  # Minut was mounted on the mounting plate (newer devices only)
        "tamper_mounted",  # Minute was removed from the mounting plate (newer devices only)
    ),
}

from abc import ABC, abstractmethod
from aiohttp import ClientSession, ClientResponse


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
                raise RequestError(resp["error"], request=url)
            return resp
        except ClientConnectionError as error:
            _LOGGER.error("Client issue: %s", error)


class PointSession():  # pylint: disable=too-many-instance-attributes
    """Point Session class used by the devices."""

    def __init__(
        self,
        auth: AbstractAuth,
    ) -> None:
        """Initialize the Minut Point Session."""
        self.auth = auth
        self._user = None
        self._webhook = {}
        self._device_state = {}
        self._homes = {}
        self._lock = RLock()
        self.metadata = {"token_endpoint": MINUT_TOKEN_URL}

    async def _request_devices(self, url, _type):
        """Request list of devices."""
        res = await self.auth.request(url)
        return res.get(_type) if res else {}

    async def read_sensor(self, device_id, sensor_uri):
        """Return sensor value based on sensor_uri."""
        sensor_uri = MAP_SENSORS.get(sensor_uri, sensor_uri)
        if device_id in self._device_state and sensor_uri in self._device_state[
            device_id
        ].get("latest_sensor_values", {}):
            _LOGGER.debug(
                "Cached sensor value for %s: %s",
                sensor_uri,
                self._device_state[device_id]["latest_sensor_values"][sensor_uri],
            )
            return self._device_state[device_id]["latest_sensor_values"][sensor_uri][
                "value"
            ]
        url = MINUT_DEVICES_URL + f"/{device_id}/{sensor_uri}"
        res = await self.auth.request(url, request_type="GET", data={"limit": 1})
        if not res or not res.get("values"):
            return None
        return res.get("values")[-1].get("value")

    async def user(self):
        """Update and returns the user data."""
        return await self.auth.request(f"{MINUT_USERS_URL}/{self.token['user_id']}")

    async def _register_webhook(self, webhook_url, events):
        """Register webhook."""
        response = await self.auth.request(
            MINUT_WEBHOOKS_URL,
            request_type="POST",
            json={
                "url": webhook_url,
                "events": events,
            },
        )
        return response

    async def remove_webhook(self):
        """Remove webhook."""
        if self._webhook and self._webhook.get("hook_id"):
            await self.auth.request(
                f"{MINUT_WEBHOOKS_URL}/{self._webhook['hook_id']}",
                request_type="DELETE",
            )

    async def update_webhook(self, webhook_url, webhook_id, events=None) -> ClientResponse | None:
        """Register webhook (if it doesn't exit)."""
        hooks = (await self.auth.request(MINUT_WEBHOOKS_URL, request_type="GET"))["hooks"]
        try:
            self._webhook = next(hook for hook in hooks if hook["url"] == webhook_url)
            _LOGGER.debug("Webhook: %s, %s", self._webhook, webhook_id)
        except StopIteration:  # Not found
            if events is None:
                events = [e for v in EVENTS.values() for e in v if e]
            try:
                self._webhook = await self._register_webhook(webhook_url, events)
                _LOGGER.debug("Registered hook: %s", self._webhook)
                return self._webhook
            except ClientResponseError:
                return None

    @property
    def webhook(self):
        """Return the webhook id and secret."""
        return self._webhook.get("hook_id")

    async def update(self):
        """Update all devices from server."""
        with self._lock:
            devices = await self._request_devices(MINUT_DEVICES_URL, "devices")

            if devices:
                self._device_state = {device["device_id"]: device for device in devices}
                _LOGGER.debug(
                    "Found devices: %s",
                    [
                        {k: self._device_state[k]["description"]}
                        for k in self._device_state
                    ],
                )
                homes = await self._request_devices(MINUT_HOMES_URL, "homes")
                if homes:
                    self._homes = homes
                    _LOGGER.debug(
                        "Found homes: %s",
                        [{home["home_id"]: home["name"]} for home in self._homes],
                    )
            return devices

    @property
    def homes(self):
        """Return all known homes."""
        return {
            home["home_id"]: home
            for home in self._homes
            if "alarm_status" in home.keys()
        }

    async def _set_alarm(self, status, home_id):
        """Set alarm satus."""
        response = await self.auth.request(
            f"{MINUT_HOMES_URL}/{home_id}",
            request_type="PUT",
            json={"alarm_status": status},
        )
        return response.get("alarm_status", "") == status

    async def alarm_arm(self, home_id):
        """Arm alarm."""
        return await self._set_alarm("on", home_id)

    async def alarm_disarm(self, home_id):
        """Disarm alarm."""
        return await self._set_alarm("off", home_id)

    @property
    def devices(self):
        """Request representations of all devices."""
        return (self.device(device_id) for device_id in self.device_ids)

    def device(self, device_id):
        """Return a device object."""
        if len(device_id) == 1:
            raise Exception("ERR FER")  # pylint: disable=broad-exception-raised
        return Device(self, device_id)

    @property
    def device_ids(self):
        """List of known device ids."""
        with self._lock:
            return self._device_state.keys()

    def device_raw(self, device_id):
        """Return the raw representaion of a device."""
        with self._lock:
            return self._device_state.get(device_id)


class Device:
    """Point device."""

    def __init__(self, session, device_id):
        """Initialize the Minut Point Device object."""
        self._session = session
        self._device_id = device_id

    def __str__(self):
        """Representaion of device."""
        return f"Device #{self.device_id} {self.name or ''}"

    async def sensor(self, sensor_type):
        """Update and return sensor value."""
        _LOGGER.debug("Reading %s sensor.", sensor_type)
        return await self._session.read_sensor(self.device_id, sensor_type)

    @property
    def device(self):
        """Return the raw representation of the device."""
        return self._session.device_raw(self.device_id)

    @property
    def ongoing_events(self):
        """Return ongoing events of device."""
        return self.device["ongoing_events"]

    @property
    def device_id(self):
        """Id of device."""
        return self._device_id

    @property
    def last_update(self):
        """Last update from device."""
        return self.device["last_heard_from_at"]

    @property
    def name(self):
        """Name of device."""
        return self.device.get("description")

    @property
    def battery_level(self):
        """Battery level of device."""
        return self.device["battery"]["percent"]

    @property
    def device_info(self):
        """Info about device."""
        return {
            "connections": {("mac", self.device["device_mac"])},
            "identifieres": self.device["device_id"],
            "manufacturer": "Minut",
            "model": f"Point v{self.device['hardware_version']}",
            "name": self.device["description"],
            "sw_version": self.device["firmware"]["installed"],
        }

    @property
    def device_status(self):
        """Status of device."""
        return {
            "active": self.device["active"],
            "offline": self.device["offline"],
            "last_update": self.last_update,
            "battery_level": self.battery_level,
        }

    @property
    def webhook(self):
        """Return the webhook id and secret."""
        return self._session.webhook

    async def remove_webhook(self):
        """Remove the session webhook."""
        return await self._session.remove_webhook()

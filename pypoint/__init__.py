"""
Minut Point API
"""

import logging
from datetime import timedelta
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import MissingTokenError

_LOGGER = logging.getLogger(__name__)

MINUT_API_URL = "https://api.minut.com"
MINUT_AUTH_URL = MINUT_API_URL + "/v1/oauth/authorize"
MINUT_DEVICES_URL = MINUT_API_URL + "/v1/devices"
MINUT_USERS_URL = MINUT_API_URL + "/v1/users"
MINUT_TOKEN_URL = MINUT_API_URL + "/v1/oauth/token"
MINUT_WEBHOOKS_URL = MINUT_API_URL + "/draft1/webhooks"

TIMEOUT = timedelta(seconds=10)

EVENTS = {
    'warm': ('temperature_high', 'temperature_dropped_normal'),
    'cold': ('temperature_low', 'temperature_risen_normal'),
    'moisture': ('humidity_high', 'humidity_dropped_normal'),
    'dry': ('humidity_low', 'humidity_risen_normal'),
    'connectivity': ('device_offline', 'device_online'),
}


class PointSession(OAuth2Session):
    """Point Session class used by the devices."""

    def __init__(self, client_id, client_secret=None, redirect_uri=None,
                 auto_refresh_kwargs=None, token=None, token_saver=None):
        from threading import RLock
        super().__init__(client_id, auto_refresh_url=MINUT_TOKEN_URL,
                         redirect_uri=redirect_uri,
                         auto_refresh_kwargs=auto_refresh_kwargs,
                         token=token, token_updater=token_saver)

        self._client_id = client_id
        self._client_secret = client_secret
        self._token = token
        self._user = None
        self._webhook = {}
        self._state = {}
        self._lock = RLock()

    @property
    def get_authorization_url(self):
        """Return the authorization url"""
        return super().authorization_url(MINUT_AUTH_URL)

    def get_access_token(self, code):
        """Get new access token"""
        try:
            self._token = super().fetch_token(MINUT_TOKEN_URL,
                                              client_id=self._client_id,
                                              client_secret=self._client_secret,  # noqa E501
                                              code=code,
                                              )
        # except Exception as e:
        except MissingTokenError as error:
            _LOGGER.debug("Token issues: %s", error)
        return self._token

    def _request(self, url, request_type='GET', **params):
        """Send a request to the Minut Point API."""
        try:
            _LOGGER.debug('Request %s %s', url, params)
            response = self.request(request_type, url,
                                    timeout=TIMEOUT.seconds,
                                    **params)
            response.raise_for_status()
            _LOGGER.debug('Response %s %s %.200s',
                          response.status_code,
                          response.headers['content-type'],
                          response.json())
            response = response.json()
            if 'error' in response:
                raise OSError(response['error'])
            return response
        except OSError as error:
            _LOGGER.warning('Failed request: %s', error)

    def _request_devices(self):
        """Request list of devices."""
        res = self._request(MINUT_DEVICES_URL)
        return res.get('devices') if res else None

    def read_sensor(self, device_id, sensor_uri):
        """Returns sensor value based on sensor_uri."""
        url = MINUT_DEVICES_URL + "/{device_id}/{sensor_uri}".format(
            device_id=device_id, sensor_uri=sensor_uri)
        res = self._request(url, request_type='GET',
                            data={'limit': 1})
        return res.get('values')[-1].get('value')

    @property
    def is_authorized(self):
        """Returns authorized status."""
        return super().authorized

    def user(self):
        """Updates and returns the user data."""
        return self._request(MINUT_USERS_URL)

    def register_webhook(self, webhook_url, events):
        """Registering webhook."""
        response = self._request(MINUT_WEBHOOKS_URL,
                                 request_type='POST',
                                 json={'url': webhook_url,
                                       'events': events,
                                       }
                                 )
        return response

    def remove_webhook(self):
        """Remove webhook."""
        if self._webhook.get('hook_id'):
            self._request(
                MINUT_WEBHOOKS_URL + self._webhook['hook_id'],
                request_type='DELETE',
            )

    def update_webhook(self, webhook_url, webhook_id, events=None):
        """Register webhook (if it doesn't exit)."""
        self._webhook['hook_id'] = webhook_id
        hooks = self._request(MINUT_WEBHOOKS_URL, request_type='GET')['hooks']
        url_hooks = [i['url'] for i in hooks]
        if webhook_url not in url_hooks:
            events = [i for slist in EVENTS.values() for i in slist]
            self._webhook = self.register_webhook(webhook_url,
                                                  events)
            _LOGGER.debug("Registered hook: %s", self._webhook)
            return self._webhook

    @property
    def webhook(self):
        """Returns the webhook id and secret."""
        return self._webhook['hook_id']

    def update(self):
        """Updates all devices from server."""
        with self._lock:
            devices = self._request_devices()

            if devices:
                self._state = {device['device_id']: device
                               for device in devices}
                _LOGGER.debug("Found devices: %s", list(self._state.keys()))
                # _LOGGER.debug("Device status: %s", devices)
            return self.devices

    @property
    def devices(self):
        """Request representations of all devices."""
        return (self.device(device_id) for device_id in self.device_ids)

    def device(self, device_id):
        """Return a device object."""
        if len(device_id) == 1:
            raise Exception('ERR FER')
        return Device(self, device_id)

    @property
    def device_ids(self):
        """List of known device ids."""
        with self._lock:
            return self._state.keys()

    def device_raw(self, device_id):
        """Return the raw representaion of a device."""
        with self._lock:
            return self._state.get(device_id)


class Device:
    """Point device."""

    def __init__(self, session, device_id):
        self._session = session
        self._device_id = device_id

    def __str__(self):
        """String representaion of device."""
        return ('Device #{id} {name}').format(
            id=self.device_id,
            name=self.name or ""
            )

    def sensor(self, sensor_type):
        """Reads and returns sensor value."""
        _LOGGER.debug("Reading %s sensor.", sensor_type)
        return self._session.read_sensor(self.device_id, sensor_type)

    @property
    def device(self):
        """Return the raw representation of the device."""
        return self._session.device_raw(self.device_id)

    @property
    def ongoing_events(self):
        """Return ongoing events of device."""
        return self.device['ongoing_events']

    @property
    def device_id(self):
        """Id of device."""
        return self._device_id

    @property
    def last_update(self):
        """Last update from device."""
        return self.device['last_heard_from_at']

    @property
    def name(self):
        """Name of device."""
        return self.device.get('description')

    @property
    def battery_level(self):
        """Battery level of device."""
        return self.device['battery']['percent']

    @property
    def device_info(self):
        """Info about device."""
        return {
            'connections': {('mac', self.device['device_mac'])},
            'identifieres': self.device['device_id'],
            'manufacturer': 'Minut',
            'model': 'Point v{}'.format(self.device['hardware_version']),
            'name': self.device['description'],
            'sw_version': self.device['firmware']['installed'],
        }

    @property
    def device_status(self):
        """Current status of device."""
        return {
            'active': self.device['active'],
            'offline': self.device['offline'],
            'last_update': self.last_update,
            'battery_level': self.battery_level,
        }

    @property
    def webhook(self):
        """Returns the webhook id and secret."""
        return self._session.webhook

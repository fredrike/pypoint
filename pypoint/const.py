"""Constants for Minut Point."""

from datetime import timedelta

MINUT_API_URL = "https://api.minut.com/v8/"
MINUT_AUTH_URL = MINUT_API_URL + "oauth/authorize"
MINUT_DEVICES_URL = MINUT_API_URL + "devices"
MINUT_USER_URL = MINUT_API_URL + "users/me"
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

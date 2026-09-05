"""Constants for the ChargeSentry integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "chargesentry_rest"

# Configuration / options keys
CONF_TOKEN: Final = "token"
CONF_SERIAL: Final = "serial"
CONF_BASE_URL: Final = "base_url"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_BASE_URL: Final = "https://api.chargesentry.uk"
DEFAULT_WEB_URL: Final = "https://chargesentry.uk"
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
MIN_SCAN_INTERVAL: Final = 15
MAX_SCAN_INTERVAL: Final = 3600

REQUEST_TIMEOUT: Final = 20  # seconds

# API paths (relative to the base URL).
PATH_LIVE_DETAILS: Final = "/v1/live/details/{serial}"
PATH_LIVE_ENERGY: Final = "/v1/live/energy/{serial}"
PATH_CHARGER_BY_SERIAL: Final = "/v1/charger/{serial}/connected"
PATH_CHARGER_DETAILS: Final = "/v1/charger/{charger_id}/details"
PATH_START_CHARGE: Final = "/v1/account/startcharge/{charger_id}/{connector}"
PATH_STOP_CHARGE: Final = "/v1/account/stopcharge/{charger_id}/{connector}"
PATH_DELAY_START: Final = "/v1/account/delaystart/{charger_id}/{connector}"
PATH_DELAY_STATUS: Final = "/v1/account/delaystatus/{charger_id}/{connector}"
PATH_DELAY_CANCEL: Final = "/v1/account/delaycancel/{charger_id}/{connector}"

PLATFORMS: Final = ["binary_sensor", "sensor", "switch"]

# OCPP connector statuses, lower-cased the way ha/details.php returns them.
STATUS_AVAILABLE: Final = "available"
STATUS_PREPARING: Final = "preparing"
STATUS_CHARGING: Final = "charging"
STATUS_SUSPENDED_EV: Final = "suspendedev"
STATUS_SUSPENDED_EVSE: Final = "suspendedevse"
STATUS_FINISHING: Final = "finishing"
STATUS_RESERVED: Final = "reserved"
STATUS_UNAVAILABLE: Final = "unavailable"
STATUS_FAULTED: Final = "faulted"
STATUS_OCCUPIED: Final = "occupied"
STATUS_UNKNOWN: Final = "unknown"

STATUS_OPTIONS: Final = [
    STATUS_AVAILABLE,
    STATUS_PREPARING,
    STATUS_CHARGING,
    STATUS_SUSPENDED_EV,
    STATUS_SUSPENDED_EVSE,
    STATUS_FINISHING,
    STATUS_RESERVED,
    STATUS_UNAVAILABLE,
    STATUS_FAULTED,
    STATUS_OCCUPIED,
    STATUS_UNKNOWN,
]

# Statuses that mean current is actually flowing into the vehicle. Used to
# decide whether a meter reading is live; whether a *session* is open is
# answered by ``session_id``, not by these.
ACTIVE_CHARGING_STATUSES: Final = {STATUS_CHARGING}

# Delayed-charge states that count as "something is armed or running".
DELAY_ACTIVE_STATES: Final = {"armed", "starting", "running", "stopping"}

# Service names
SERVICE_START_CHARGE: Final = "start_charge"
SERVICE_STOP_CHARGE: Final = "stop_charge"
SERVICE_DELAY_START: Final = "delay_start"
SERVICE_CANCEL_DELAY: Final = "cancel_delay"

ATTR_CONNECTOR: Final = "connector"
ATTR_LIMIT_KWH: Final = "limit_kwh"
ATTR_DELAY_SECONDS: Final = "delay_seconds"
ATTR_RUN_FOR_SECONDS: Final = "run_for_seconds"

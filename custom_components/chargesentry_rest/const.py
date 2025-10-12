DOMAIN = "chargesentry_rest"

# Hard-code polling to 120s (used for display only; coordinator enforces it too)
DEFAULT_SCAN_INTERVAL = 120  # seconds

# Config/Options keys
CONF_SERIAL = "serial"
CONF_TOKEN = "token"
CONF_SCAN_INTERVAL = "scan_interval"      # kept for compatibility; ignored by coordinator
CONF_AUTH_MODE = "auth_mode"               # "bearer" | "token" | "x-api-key" | "query"
CONF_AUTH_QUERY_NAME = "auth_query_name"   # only used if auth_mode == "query"

# Hard-coded API endpoints
ENERGY_URL = "https://api.chargesentry.uk/v1/live/energy/{serial}"
LIVE_URL   = "https://api.chargesentry.uk/v1/live/details/{serial}"

PLATFORMS = ["sensor"]

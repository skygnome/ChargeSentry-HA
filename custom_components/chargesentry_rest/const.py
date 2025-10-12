DOMAIN = "chargesentry_rest"
DEFAULT_SCAN_INTERVAL = 5  # seconds
CONF_SERIAL = "serial"
CONF_TOKEN = "token"  # optional bearer

# Hard-coded API endpoints
ENERGY_URL = "https://api.chargesentry.uk/v1/live/energy/{serial}"
LIVE_URL   = "https://api.chargesentry.uk/v1/live/details/{serial}"

PLATFORMS = ["sensor"]

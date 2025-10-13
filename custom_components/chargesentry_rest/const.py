DOMAIN = "chargesentry_rest"

# Hard-code polling to 120s
DEFAULT_SCAN_INTERVAL = 120  # seconds

CONF_SERIAL = "serial"
CONF_TOKEN = "token"

ENERGY_URL = "https://api.chargesentry.uk/v1/live/energy/{serial}"
LIVE_URL   = "https://api.chargesentry.uk/v1/live/details/{serial}"

PLATFORMS = ["sensor"]

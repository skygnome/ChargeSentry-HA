<p align="center">
  <img src="brand/logo.png" alt="ChargeSentry" width="240">
</p>

<h1 align="center">ChargeSentry for Home Assistant</h1>

<p align="center">
  <a href="https://github.com/skygnome/ChargeSentry-HA/actions/workflows/validate.yml"><img src="https://github.com/skygnome/ChargeSentry-HA/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-custom-41BDF5.svg" alt="HACS custom"></a>
</p>

Monitor and control a [ChargeSentry](https://chargesentry.uk) EV charge point
from Home Assistant. The integration polls the ChargeSentry cloud API, so it
works wherever your charger is — no local network access to the charge point
required.

## What you get

One device per charger, with:

**Sensors**

| Entity | Notes |
|---|---|
| Status | `available`, `preparing`, `charging`, `faulted`, … |
| Power | Live draw in W. Reported as `0` whenever the connector is not charging (see [below](#a-note-on-power-readings)) |
| Current | Live current in A, zeroed the same way |
| Voltage | Supply voltage. Disabled by default — enable it if you want it |
| Total energy | Lifetime kWh from the meter register. `total_increasing`, so it drops straight into the **Energy dashboard** |
| Energy today | Today's delivered kWh |
| Session started | Timestamp of the session in progress |
| Delayed charge countdown | Seconds until an armed delayed charge begins |
| Session ID, Connector, Meter reading | Diagnostic, disabled by default |

**Binary sensors** — Plugged in, Charging, Delayed charge armed, Fault, Charger online.

**Switch** — *Charging*: turn it on to remote-start a charge, off to stop it.

**Services** — `start_charge`, `stop_charge`, `delay_start`, `cancel_delay`.

## Requirements

- Home Assistant **2024.11** or newer.
- A ChargeSentry API token: in the ChargeSentry app, **Account → API keys →
  create key**. The raw token is shown once, at creation — copy it then.
- An account that **owns or administers** the charger. The live endpoints are
  gated on charger/site admin access; an ordinary member of a public site can
  see the charger in the app but will get a `403` here, and setup will say so.

## Installation

### HACS (recommended)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/skygnome/ChargeSentry-HA`, category **Integration**.
3. Install **ChargeSentry**, then restart Home Assistant.

### Manual

Copy `custom_components/chargesentry_rest` into your `config/custom_components`
directory and restart Home Assistant.

## Configuration

**Settings → Devices & services → Add integration → ChargeSentry.**

| Field | |
|---|---|
| API token | The bearer token from Account → API keys |
| Charger serial | e.g. `CS-0001` |
| API base URL | Leave as `https://api.chargesentry.uk` unless you run your own host |

Setup validates the token and confirms your account administers that charger
before creating the entry, so a typo fails on the form rather than turning up
as a broken device later.

Add the integration once per charger — each entry is keyed on its serial.

**Options** (⋮ → Configure) let you change the polling interval; it defaults
to 60 seconds. If the token is ever revoked or expires, Home Assistant raises
a repair asking for a new one rather than silently going stale.

## Automation examples

Charge on cheap overnight rates:

```yaml
automation:
  - alias: Charge the car on the cheap rate
    triggers:
      - trigger: time
        at: "00:30:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.home_charger_plugged_in
        state: "on"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.home_charger_charging
```

Arm a delayed charge for one hour's time, capped at 20 kWh, as soon as the car
is plugged in:

```yaml
automation:
  - alias: Delay the charge when plugged in
    triggers:
      - trigger: state
        entity_id: binary_sensor.home_charger_plugged_in
        to: "on"
    actions:
      - action: chargesentry_rest.delay_start
        target:
          entity_id: switch.home_charger_charging
        data:
          delay_seconds: 3600
          limit_kwh: 20
```

`delay_start` needs the connector to be in the `preparing` state (plugged in,
not yet charging) — the API returns `409` otherwise, which surfaces in Home
Assistant as a failed action.

## Notes and limitations

### A note on power readings

The API's live endpoint returns the newest meter value recorded in the last 30
days, with no check that the reading is *current* — so an idle charger keeps
echoing the last power it ever drew. The integration anchors power and current
to the connector status and reports `0` when the charger is not charging, which
keeps history graphs and Energy dashboard statistics honest.

### Polling, not push

`iot_class` is `cloud_polling`. State changes show up on the next poll, so
with the default interval the switch can take up to a minute to reflect a
charge you started elsewhere. Commands request an immediate refresh, but the
charge point itself takes a few seconds to acknowledge one, so the switch may
briefly show its old state after you flip it.

### One connector

The live endpoint reports a single connector — the one with the active session,
or the charger's first. Multi-connector chargers will show whichever that is.
Services take an explicit `connector:` if you need to act on another one.

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install homeassistant pytest pytest-homeassistant-custom-component ruff
pytest          # test suite
ruff check .    # lint
ruff format .   # format
```

CI runs [hassfest](https://developers.home-assistant.io/blog/2020/04/16/hassfest),
the HACS validator, ruff and the test suite on every push and pull request.

Brand assets and how to get the logo showing inside Home Assistant itself:
[`brand/README.md`](brand/README.md).

# Brand assets

| File | Size | Used for |
|---|---|---|
| `icon.svg` / `icon.png` / `icon@2x.png` | 512 / 1024 square | Integration icon (badge only) |
| `logo.svg` / `logo.png` / `logo@2x.png` | 512 / 1024 tall | Full lockup (badge + wordmark) |

## These are a vector redraw, not the original artwork

The marks here are a clean SVG redraw of the ChargeSentry badge — same
composition (arch badge, charge post with bolt roundel, EV, teal wordmark) and
same palette — built because the original raster artwork was not in either
repository. **Drop the real files in over the top when you have them**: keep
the names and sizes above and nothing else needs to change.

The rasterised wordmark was set in DejaVu Sans Bold, which is not the display
face the original logo uses. Regenerating from `logo.svg` on a machine with the
real face installed (the SVG asks for Montserrat first) will match it more
closely.

Palette:

| Role | Hex |
|---|---|
| Outline navy | `#0E2233` |
| Wordmark teal | `#17877A` |
| Mint (field, dark stop) | `#6FD3AC` |
| Mint (field, light stop) | `#E9FBF3` |

## Getting the logo to show inside Home Assistant

Home Assistant does **not** read brand images out of a custom integration's
folder — it loads them from the
[`home-assistant/brands`](https://github.com/home-assistant/brands) repository
by domain. Until a submission is merged there, ChargeSentry shows as a generic
puzzle-piece in the HA UI, and the images here only appear in the README and
in HACS.

To fix that, open a PR against `home-assistant/brands` adding:

```
custom_integrations/chargesentry_rest/icon.png     # 256x256 (or 512x512)
custom_integrations/chargesentry_rest/icon@2x.png  # 2x the above
custom_integrations/chargesentry_rest/logo.png     # max 512px tall
custom_integrations/chargesentry_rest/logo@2x.png  # 2x the above
```

Note the `custom_integrations/` prefix — that is the directory for
integrations distributed outside HA core, which is what this is. The domain
directory must be `chargesentry_rest`, matching `manifest.json`. Images must
be trimmed of surrounding whitespace and have a transparent background; the
files here are already transparent, but re-crop them if the brands CI asks.

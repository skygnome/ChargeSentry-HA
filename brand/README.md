# Brand assets

| File | Size | Used for |
|---|---|---|
| `logo.png` | 512 × 427 | Full lockup — badge and wordmark |
| `logo@2x.png` | 1024 × 853 | Retina lockup |
| `icon.png` | 256 × 256 | Integration icon — badge only |
| `icon@2x.png` | 512 × 512 | Retina icon |

All four are RGBA with a transparent background and trimmed of surrounding
whitespace, which is what the Home Assistant brands repository requires.

`logo.png` is the source artwork. The other three are derived from it: the
icons are the badge with the wordmark cropped off, padded to a square; the
`@2x` files are the same images at double resolution. To regenerate them after
replacing the artwork, drop the new lockup in as `brand/logo.png` and re-run
the crop — the badge occupies everything above the wordmark, so the only value
worth re-checking is where that split falls.

Palette:

| Role | Hex |
|---|---|
| Outline navy | `#0E2233` |
| Wordmark teal | `#17877A` |
| Mint (field) | `#6FD3AC` – `#E9FBF3` |

## Getting the logo to show inside Home Assistant

Home Assistant does **not** read brand images out of a custom integration's
folder — it loads them from the
[`home-assistant/brands`](https://github.com/home-assistant/brands) repository
by domain. Until a submission is merged there, ChargeSentry shows as a generic
puzzle-piece in the HA UI, and the images here only appear in the README and
in HACS.

To fix that, open a PR against `home-assistant/brands` adding the four files
above at:

```
custom_integrations/chargesentry_rest/logo.png
custom_integrations/chargesentry_rest/logo@2x.png
custom_integrations/chargesentry_rest/icon.png
custom_integrations/chargesentry_rest/icon@2x.png
```

Note the `custom_integrations/` prefix — that is the directory for
integrations distributed outside HA core, which is what this is. The domain
directory must be `chargesentry_rest`, matching `manifest.json`.

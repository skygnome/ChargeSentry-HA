# Brand assets

`logo.png` here is the **master artwork** — full resolution, transparent, not
shipped to Home Assistant. Everything Home Assistant actually serves is
generated from it into
[`custom_components/chargesentry_rest/brand/`](../custom_components/chargesentry_rest/brand):

```bash
python3 scripts/generate_brand_images.py
```

| Generated file | Size | Used for |
|---|---|---|
| `icon.png` | 256 × 256 | Integration icon — badge only, wordmark cropped off |
| `icon@2x.png` | 512 × 512 | Retina icon |
| `logo.png` | 307 × 256 | Full lockup — badge and wordmark |
| `logo@2x.png` | 615 × 512 | Retina lockup |

The sizes are not arbitrary: Home Assistant applies the
[brands repository specification](https://github.com/home-assistant/brands#image-specification)
to local images too. Icons must be exactly square at 256/512 px, and a logo's
*shortest* side must be 128–256 px (256–512 px for `@2x`) — which is why the
master, at 677 × 564, cannot be shipped as-is.

If you replace the master, re-run the script. The only value in it worth
re-checking is `BADGE_BOTTOM`, the row where the wordmark starts, since that is
what separates the icon from the lockup.

Palette:

| Role | Hex |
|---|---|
| Outline navy | `#0E2233` |
| Wordmark teal | `#17877A` |
| Mint (field) | `#6FD3AC` – `#E9FBF3` |

## Why the images live inside the integration directory

Home Assistant **2026.3** added support for custom integrations shipping their
own brand images: it reads them from a `brand/` directory *inside the
integration*, and they take precedence over the
[brands repository](https://github.com/home-assistant/brands) CDN.

That is the only location that works. Images in this repository-root folder are
never read by Home Assistant — they only show up in the README and in HACS.
Before 2026.3 the sole option was a PR against `home-assistant/brands` adding
`custom_integrations/chargesentry_rest/`; that is no longer necessary, and on
2026.3+ the local files win even if such a submission also exists.

On Home Assistant older than 2026.3 the `brand/` directory is simply ignored
and the integration shows the default placeholder icon. Nothing breaks.

# DroidLens Brand Assets

**Product:** DroidLens  
**Tagline:** *See. Inspect. Automate.*

## Palette

| Name | Hex | Usage |
|------|-----|-------|
| Emerald Green | `#34A853` | Android mark, accent, success |
| Deep Blue | `#1E88E5` | Inspection lens, links |
| Dark Slate | `#263238` | Backgrounds, icon base |
| White | `#ECEFF1` | Text on dark, crosshair |
| Light Gray | `#90A4AE` | Secondary text, tagline |

## Files

| Asset | Description |
|-------|-------------|
| `logo.svg` | Horizontal wordmark with tagline |
| `icon.svg` | Square app mark (scalable) |
| `icon.png` | 512×512 master raster |
| `icon.ico` | Windows multi-size icon |
| `icons/{size}x{size}.png` | Linux electron-builder sizes (16–512) |
| `icons/icon-*.png` | Legacy alias filenames |

## Regenerate PNG/ICO

```bash
npm run generate:icons
```

## Design Concept

Flat, minimalist mark combining:

- Stylized Android head (emerald)
- Magnifying glass with crosshair reticle (blue)
- Connected UI hierarchy nodes (gray)

Recognizable at 16×16; works on light and dark backgrounds.

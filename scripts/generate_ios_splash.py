#!/usr/bin/env python3
"""Genere les splash screens iOS pour la PWA OptiFlow.

Cible toutes les resolutions iPhone/iPad utilises pour
`<link rel="apple-touch-startup-image">`. Les images sont composees
d'un fond degrade bleu OptiFlow + le logo (icon-512) centre.

Usage : python3 scripts/generate_ios_splash.py
Sortie : apps/web/public/icons/splash/*.png (10 fichiers)
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "apps" / "web" / "public"
ICON_SRC = PUBLIC / "icons" / "icon-512.png"
SPLASH_DIR = PUBLIC / "icons" / "splash"

# Couleur de fond (manifest theme_color #2563eb = blue-600)
BG_COLOR = (37, 99, 235)  # RGB

# Resolutions iOS officielles (pixels) — orientation portrait + landscape.
# Source : https://developer.apple.com/design/human-interface-guidelines/foundations/layout
SPLASH_SIZES = [
    # iPhone 14 Pro Max / 15 Pro Max (430x932 logical, @3x)
    ("iphone-14-pro-max-portrait", 1290, 2796),
    ("iphone-14-pro-max-landscape", 2796, 1290),
    # iPhone 14 Plus / 15 Plus (428x926 logical, @3x)
    ("iphone-14-plus-portrait", 1284, 2778),
    ("iphone-14-plus-landscape", 2778, 1284),
    # iPhone 14 Pro / 15 Pro (393x852 logical, @3x)
    ("iphone-14-pro-portrait", 1179, 2556),
    ("iphone-14-pro-landscape", 2556, 1179),
    # iPhone 14 / 15 (390x844 logical, @3x)
    ("iphone-14-portrait", 1170, 2532),
    ("iphone-14-landscape", 2532, 1170),
    # iPhone X/XS/11 Pro (375x812 logical, @3x)
    ("iphone-x-portrait", 1125, 2436),
    ("iphone-x-landscape", 2436, 1125),
    # iPhone 8 Plus (414x736 logical, @3x)
    ("iphone-8-plus-portrait", 1242, 2208),
    # iPhone 8 (375x667 logical, @2x)
    ("iphone-8-portrait", 750, 1334),
    # iPad Pro 12.9" (1024x1366 logical, @2x)
    ("ipad-pro-12-9-portrait", 2048, 2732),
    ("ipad-pro-12-9-landscape", 2732, 2048),
    # iPad Pro 11" / iPad Air (834x1194 logical, @2x)
    ("ipad-pro-11-portrait", 1668, 2388),
    ("ipad-pro-11-landscape", 2388, 1668),
    # iPad Mini / iPad classique (768x1024 logical, @2x)
    ("ipad-portrait", 1536, 2048),
    ("ipad-landscape", 2048, 1536),
]


def generate_splash(name: str, width: int, height: int, icon: Image.Image) -> Path:
    """Compose un splash screen : fond uni + icone centree (taille adaptative)."""
    splash = Image.new("RGB", (width, height), BG_COLOR)

    # Taille de l'icone : ~25% de la dimension la plus petite pour rester lisible
    target = int(min(width, height) * 0.25)
    icon_resized = icon.resize((target, target), Image.LANCZOS)

    # Centrer
    x = (width - target) // 2
    y = (height - target) // 2

    # Si l'icone a un canal alpha, utilise-le comme masque
    if icon_resized.mode in ("RGBA", "LA"):
        splash.paste(icon_resized, (x, y), icon_resized)
    else:
        splash.paste(icon_resized, (x, y))

    out_path = SPLASH_DIR / f"{name}.png"
    splash.save(out_path, "PNG", optimize=True)
    return out_path


def main() -> int:
    if not ICON_SRC.exists():
        print(f"ERREUR : icone source introuvable : {ICON_SRC}", file=sys.stderr)
        return 1

    SPLASH_DIR.mkdir(parents=True, exist_ok=True)

    icon = Image.open(ICON_SRC).convert("RGBA")
    print(f"Generation de {len(SPLASH_SIZES)} splash screens iOS...")

    for name, width, height in SPLASH_SIZES:
        out = generate_splash(name, width, height, icon)
        size_kb = out.stat().st_size // 1024
        print(f"  - {name}.png ({width}x{height}, {size_kb} KB)")

    print(f"\nOK. Generes dans {SPLASH_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

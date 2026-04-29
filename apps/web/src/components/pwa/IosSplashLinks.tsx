/**
 * Liens `<link rel="apple-touch-startup-image">` pour les splash screens iOS.
 *
 * iOS Safari ne supporte pas le champ `splash_screens` de manifest.json :
 * il faut declarer chaque resolution avec un media query precis pointant
 * vers le PNG correspondant.
 *
 * Les fichiers sont generes par `scripts/generate_ios_splash.py` dans
 * `public/icons/splash/`. Re-executer ce script si une nouvelle resolution
 * d'iPhone/iPad sort.
 *
 * Source media queries : https://developer.apple.com/design/human-interface-guidelines/foundations/layout
 */

interface SplashEntry {
  href: string;
  // Logical width x height (CSS px) — pas la resolution physique
  width: number;
  height: number;
  // Device-pixel-ratio (@2x ou @3x)
  ratio: number;
}

const SPLASH_ENTRIES: SplashEntry[] = [
  // iPhone 14 Pro Max / 15 Pro Max — 430x932 @3x
  { href: "/icons/splash/iphone-14-pro-max-portrait.png", width: 430, height: 932, ratio: 3 },
  { href: "/icons/splash/iphone-14-pro-max-landscape.png", width: 932, height: 430, ratio: 3 },
  // iPhone 14 Plus / 15 Plus — 428x926 @3x
  { href: "/icons/splash/iphone-14-plus-portrait.png", width: 428, height: 926, ratio: 3 },
  { href: "/icons/splash/iphone-14-plus-landscape.png", width: 926, height: 428, ratio: 3 },
  // iPhone 14 Pro / 15 Pro — 393x852 @3x
  { href: "/icons/splash/iphone-14-pro-portrait.png", width: 393, height: 852, ratio: 3 },
  { href: "/icons/splash/iphone-14-pro-landscape.png", width: 852, height: 393, ratio: 3 },
  // iPhone 14 / 15 — 390x844 @3x
  { href: "/icons/splash/iphone-14-portrait.png", width: 390, height: 844, ratio: 3 },
  { href: "/icons/splash/iphone-14-landscape.png", width: 844, height: 390, ratio: 3 },
  // iPhone X/XS/11 Pro — 375x812 @3x
  { href: "/icons/splash/iphone-x-portrait.png", width: 375, height: 812, ratio: 3 },
  { href: "/icons/splash/iphone-x-landscape.png", width: 812, height: 375, ratio: 3 },
  // iPhone 8 Plus — 414x736 @3x
  { href: "/icons/splash/iphone-8-plus-portrait.png", width: 414, height: 736, ratio: 3 },
  // iPhone 8 — 375x667 @2x
  { href: "/icons/splash/iphone-8-portrait.png", width: 375, height: 667, ratio: 2 },
  // iPad Pro 12.9" — 1024x1366 @2x
  { href: "/icons/splash/ipad-pro-12-9-portrait.png", width: 1024, height: 1366, ratio: 2 },
  { href: "/icons/splash/ipad-pro-12-9-landscape.png", width: 1366, height: 1024, ratio: 2 },
  // iPad Pro 11" / iPad Air — 834x1194 @2x
  { href: "/icons/splash/ipad-pro-11-portrait.png", width: 834, height: 1194, ratio: 2 },
  { href: "/icons/splash/ipad-pro-11-landscape.png", width: 1194, height: 834, ratio: 2 },
  // iPad Mini / iPad classique — 768x1024 @2x
  { href: "/icons/splash/ipad-portrait.png", width: 768, height: 1024, ratio: 2 },
  { href: "/icons/splash/ipad-landscape.png", width: 1024, height: 768, ratio: 2 },
];

function buildMedia(entry: SplashEntry): string {
  const orientation = entry.width >= entry.height ? "landscape" : "portrait";
  return (
    `(device-width: ${entry.width}px) and (device-height: ${entry.height}px) ` +
    `and (-webkit-device-pixel-ratio: ${entry.ratio}) and (orientation: ${orientation})`
  );
}

export function IosSplashLinks() {
  return (
    <>
      {SPLASH_ENTRIES.map((entry) => (
        <link
          key={entry.href}
          rel="apple-touch-startup-image"
          href={entry.href}
          media={buildMedia(entry)}
        />
      ))}
    </>
  );
}

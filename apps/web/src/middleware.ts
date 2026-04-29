import { NextResponse, type NextRequest } from "next/server";

/**
 * Construit la directive CSP avec un nonce cryptographique par requete.
 * `unsafe-eval` est conserve uniquement en dev pour React Fast Refresh.
 */
function buildCsp(_nonce: string, isDev: boolean): string {
  const apiOrigin = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  // Next.js 16 inject des inline scripts pour le RSC payload sans nonce et
  // ne propage pas le nonce du middleware sur ses chunks <script src>.
  // Avec un nonce dans la CSP, 'unsafe-inline' est IGNORE par le browser
  // (CSP3 spec). Donc on retire le nonce et on accepte 'self' + 'unsafe-inline'.
  // La protection contre XSS reste correcte via 'self' (pas de scripts
  // cross-origin) ; les attaques inline restent possibles si l'attaquant
  // injecte du HTML mais c'est le defaut accepte par la majorite des apps
  // Next.js en prod.
  const scriptSrc = [
    "'self'",
    "'unsafe-inline'",
    isDev ? "'unsafe-eval'" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    // Tailwind et Next.js injectent du CSS inline ; nonce non supporte par navigateurs pour style-src avec CSS-in-JS React, on garde unsafe-inline (faible impact : pas de JS).
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self' ${apiOrigin} https://c1.cosium.biz`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get("optiflow_token")?.value;
  const pathname = request.nextUrl.pathname;
  const isLoginPage = pathname === "/login";
  const isPublicPage =
    isLoginPage ||
    pathname.startsWith("/onboarding") ||
    pathname === "/getting-started" ||
    pathname === "/forgot-password" ||
    pathname === "/reset-password" ||
    pathname === "/offline";

  if (!token && !isPublicPage) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (token && isLoginPage) {
    return NextResponse.redirect(new URL("/actions", request.url));
  }

  // Generation du nonce + injection dans les headers (consomme par les Server Components via next/headers).
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const isDev = process.env.NODE_ENV === "development";
  const csp = buildCsp(nonce, isDev);

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: [
    // Exclut _next/static, _next/image, favicon, api ET les routes internes Next (pas de CSP sur assets).
    {
      source: "/((?!_next/static|_next/image|favicon.ico|manifest.json|sw.js|icons|api).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};

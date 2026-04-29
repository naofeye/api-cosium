import type { NextConfig } from "next";

// Bundle analyzer opt-in : `ANALYZE=true npm run build` apres `npm i -D @next/bundle-analyzer`.
// Desactive par defaut pour ne pas imposer la dependance.
const withBundleAnalyzer = process.env.ANALYZE === "true"
  ? require("@next/bundle-analyzer")({ enabled: true })
  : (cfg: NextConfig) => cfg;

// Backend FastAPI URL pour les rewrites server-side. Lu depuis env BACKEND_INTERNAL_URL
// (defaut hostname Docker compose). Ce rewrite permet aux requetes browser
// `/api/*` d'etre proxifees vers le backend sans toucher au reverse proxy externe :
//   browser → https://cosium.ia.coging.com/api/v1/auth/login
//          → Caddy (reverse_proxy web:3000)
//          → Next.js server (rewrite)
//          → http://api-cosium-api-1:8000/api/v1/auth/login
// Cookies httpOnly conserves naturellement (meme domaine cote browser).
const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL || "http://api-cosium-api-1:8000";

// Validation : si un attaquant compromet le container web (RCE supply chain
// npm) et modifie BACKEND_INTERNAL_URL, on refuse au boot. Sans ca, tous les
// cookies/JWT user partiraient vers un host externe.
const _BACKEND_URL_PATTERN = /^https?:\/\/(api-cosium-api(-\d+)?|localhost|127\.0\.0\.1)(:\d+)?$/;
if (!_BACKEND_URL_PATTERN.test(BACKEND_INTERNAL_URL)) {
  throw new Error(
    `BACKEND_INTERNAL_URL invalide: "${BACKEND_INTERNAL_URL}". ` +
      "Attendu format: http(s)://api-cosium-api[-N]:port ou http(s)://localhost:port",
  );
}

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  compress: true,
  async rewrites() {
    // /metrics retire des rewrites publics : exposition Prometheus = exfiltration
    // de donnees business (nombre tenants, encours, sync stats). A scrapper en
    // interne via Docker network uniquement, pas via Caddy public.
    return [
      { source: "/api/:path*", destination: `${BACKEND_INTERNAL_URL}/api/:path*` },
      { source: "/health", destination: `${BACKEND_INTERNAL_URL}/health` },
    ];
  },
  // Note Next.js 16 : `eslint.ignoreDuringBuilds` supprime du type NextConfig.
  // ESLint est toujours execute par `next build` par defaut (bloque sur erreurs).
  // CI a un job "Frontend Lint" separe qui fait un audit plus strict.
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "minio", port: "9000", pathname: "/**" },
      { protocol: "http", hostname: "localhost", port: "9000", pathname: "/**" },
      { protocol: "https", hostname: "*.cosium.biz", pathname: "/**" },
    ],
  },
  async headers() {
    // Le Content-Security-Policy est pilote par `src/middleware.ts` avec un nonce par requete.
    // On garde ici uniquement les headers statiques qui ne dependent pas d'un nonce.
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default withBundleAnalyzer(nextConfig);

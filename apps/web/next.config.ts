import path from "path";
import type { NextConfig } from "next";

// Bundle analyzer opt-in : `ANALYZE=true npm run build` apres `npm i -D @next/bundle-analyzer`.
// Desactive par defaut pour ne pas imposer la dependance.
const withBundleAnalyzer = process.env.ANALYZE === "true"
  ? require("@next/bundle-analyzer")({ enabled: true })
  : (cfg: NextConfig) => cfg;

const nextConfig: NextConfig = {
  output: "standalone",
  // Monorepo: trace files from repo root so standalone server.js is at
  // .next/standalone/apps/web/server.js with correct paths
  outputFileTracingRoot: path.join(__dirname, "../../"),
  poweredByHeader: false,
  reactStrictMode: true,
  compress: true,
  // ESLint run durant `next build` - bloque sur erreurs uniquement (warnings ok).
  // CI a un job "Frontend Lint" separe qui fait un audit plus strict.
  eslint: {
    ignoreDuringBuilds: false,
  },
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

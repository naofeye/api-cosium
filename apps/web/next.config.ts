import type { NextConfig } from "next";

// Bundle analyzer opt-in : `ANALYZE=true npm run build` apres `npm i -D @next/bundle-analyzer`.
// Desactive par defaut pour ne pas imposer la dependance.
const withBundleAnalyzer = process.env.ANALYZE === "true"
  ? require("@next/bundle-analyzer")({ enabled: true })
  : (cfg: NextConfig) => cfg;

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  compress: true,
  // CI a un job "Frontend Lint" dedie ; on ne bloque pas le build sur les warnings ESLint.
  eslint: {
    ignoreDuringBuilds: true,
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

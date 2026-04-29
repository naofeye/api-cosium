import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

export default [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-require-imports": "warn",
      "react-hooks/exhaustive-deps": "warn",
      // React Compiler-era rules (eslint-plugin-react-hooks v6) introduced
      // by eslint-config-next v16 — too aggressive for the existing codebase.
      // Downgraded to warn; tighten incrementally (TODO P2 frontend qualité).
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/purity": "warn",
      "react-hooks/refs": "warn",
      "react-hooks/immutability": "warn",
      "react-hooks/incompatible-library": "warn",
      "@next/next/no-img-element": "warn",
      "react/no-unescaped-entities": "warn",
      "jsx-a11y/role-has-required-aria-props": "warn",
      "@next/next/no-html-link-for-pages": "warn",
    },
  },
  {
    ignores: [
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
      "node_modules/**",
      "tests/e2e/**",
      "playwright-report/**",
      "test-results/**",
      "src/instrumentation*.ts",
    ],
  },
];

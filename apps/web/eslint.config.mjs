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
      "react-hooks/exhaustive-deps": "warn",
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

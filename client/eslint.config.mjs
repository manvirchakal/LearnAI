import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const config = [
  ...nextVitals,
  ...nextTs,
  {
    // Vendored component kits (shadcn/ui, AI Elements) and generated assets
    ignores: [".next/**", "node_modules/**", "public/**", "components/ui/**", "components/ai-elements/**", "next-env.d.ts"],
  },
];

export default config;

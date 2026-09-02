import resolve from "@rollup/plugin-node-resolve";

// Bundles the ES modules into a single card asset. Minification is intentionally omitted
// to keep the dev-dependency surface minimal (no terser/serialize-javascript chain); the
// card is small and served locally, so an unminified bundle is acceptable.
export default {
  input: "src/index.js",
  output: {
    file: "dist/alexa-shopping-categoriser-card.js",
    format: "es",
    sourcemap: false,
  },
  plugins: [resolve()],
};

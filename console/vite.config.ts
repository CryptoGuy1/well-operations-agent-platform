/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// A relative base: the site works from any path on GitHub Pages, and routes live in the hash.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { sourcemap: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
  },
});

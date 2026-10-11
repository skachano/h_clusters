/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In compose the API is the `api` service; on a bare host it is localhost:8000.
const apiTarget = process.env.API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  // The GitHub Pages build is served under /<repo>/ (VITE_BASE); everything else at the root.
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: ["web"], // the compose service name, used by the e2e container
    proxy: { "/api": { target: apiTarget, changeOrigin: true } },
  },
  preview: { allowedHosts: ["web-static"] }, // the static build's compose service (e2e)
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});

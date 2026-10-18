import { defineConfig } from "vite";

export default defineConfig({
  root: "dashboard",
  base: "./",
  server: { allowedHosts: [".ts.net"] }, // reachable over the tailnet via `tailscale serve`
  build: { outDir: "../dist", emptyOutDir: true, target: "es2022" },
});

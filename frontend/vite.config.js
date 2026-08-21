import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// VITE_SINGLEFILE=1 inlines everything into one self-contained index.html for a
// static, serverless preview (used with VITE_HASH=1). Otherwise a normal build
// served by FastAPI/Vite; the dev server proxies API calls to the backend.
const single = process.env.VITE_SINGLEFILE === "1";

export default defineConfig({
  base: single ? "./" : "/",
  plugins: [react(), ...(single ? [viteSingleFile()] : [])],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/webhooks": "http://localhost:8000",
    },
  },
});

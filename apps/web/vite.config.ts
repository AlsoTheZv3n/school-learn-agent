import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev proxy so the browser can call the API same-origin (no CORS needed).
// 127.0.0.1 (not localhost) so Node doesn't resolve to IPv6 ::1 — the API binds IPv4.
const apiTarget = "http://127.0.0.1:8010";

// The SPA route /teacher/* shares a prefix with the API /teacher/*. For an HTML
// navigation (browser address bar / refresh) serve the app; for data fetches proxy
// to the API. (In production the API would sit behind /api or a separate host.)
function spaBypass(req: { headers: Record<string, string | string[] | undefined> }) {
  const accept = req.headers.accept;
  if (typeof accept === "string" && accept.includes("text/html")) {
    return "/index.html";
  }
  return undefined;
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5181,
    strictPort: true,
    proxy: {
      "/teacher": { target: apiTarget, bypass: spaBypass },
      "/student": apiTarget,
      "/content": apiTarget,
      "/curriculum": apiTarget,
      "/dev": apiTarget,
      "/health": apiTarget,
    },
  },
});

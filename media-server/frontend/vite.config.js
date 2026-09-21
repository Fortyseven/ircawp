import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// Dev server proxies API calls to the media-server so the SPA can use
// relative URLs in both dev (5173) and prod (same-port static mount).
export default defineConfig({
    plugins: [svelte()],
    server: {
        port: 5173,
        proxy: {
            "/images": "http://localhost:8100",
            "/health": "http://localhost:8100",
            "/backends": "http://localhost:8100",
        },
    },
    build: {
        outDir: "dist",
    },
    test: {
        environment: "node",
    },
});

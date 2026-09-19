import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],

  server: {
    proxy: {
      //api call proxy
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
        secure: false,
        configure: (proxy, _options) => {
          proxy.on("error", (err, req, res) => {
            if (err.code === "ECONNREFUSED") {
              if (res.writeHead && !res.headersSent) {
                res.writeHead(503, { "Content-Type": "application/json" });
                res.end(JSON.stringify({ error: "Backend server offline", mock: true }));
              }
            }
          });
        },
      },

      //websocket connection proxy
      "/api/ws": {
        target: "ws://localhost:8080",
        ws: true,
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on("error", (_err, _req, _socket) => {
            // Suppress websocket ECONNREFUSED logs when backend server is offline
          });
        },
      },
    },
  },
});
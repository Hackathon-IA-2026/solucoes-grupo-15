/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// O frontend fala so com a API /v1/* do backend (nunca com o ai nem com
// o indice vetorial). Em dev/Compose, o proxy abaixo repassa /v1 para o
// backend pelo nome do servico Docker (configuravel via
// VITE_BACKEND_PROXY_TARGET), para que o codigo do app sempre use
// caminhos relativos e nunca precise saber onde o backend esta.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/v1": {
        target: process.env.VITE_BACKEND_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/setupTests.ts"],
  },
});

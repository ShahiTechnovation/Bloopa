import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// algosdk and @perawallet/connect depend on Node.js Buffer.
// Vite doesn't polyfill Node globals, so we inject them.
export default defineConfig({
  plugins: [react()],
  define: {
    global: "globalThis",
  },
  resolve: {
    alias: {
      buffer: "buffer/",
    },
  },
});

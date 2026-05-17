import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// NODE_ENV=production is set in this environment — run builds as:
//   NODE_ENV=development node_modules/.bin/vite build

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/chat": "http://localhost:5001",
      "/agent": "http://localhost:5001",
      "/generate": "http://localhost:5001",
      "/get-files": "http://localhost:5001",
      "/modify": "http://localhost:5001",
      "/push": "http://localhost:5001",
      "/plan": "http://localhost:5001",
      "/plan-output": "http://localhost:5001",
      "/apply": "http://localhost:5001",
      "/upload": "http://localhost:5001",
      "/direct-push": "http://localhost:5001",
      "/logout": "http://localhost:5001",
    },
  },
});

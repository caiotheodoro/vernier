import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Hugging Face serves a static Space from the repo root, so assets must be referenced
// relatively (`./assets/...`), not from `/`.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { outDir: "dist", assetsDir: "assets", sourcemap: false },
});

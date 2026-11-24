import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API-basisadresse konfigureres via miljøvariabel VITE_API_BASE ved build/dev
// (FORM-05: adresser skal være konfigurerbare).
export default defineConfig({
  plugins: [react()],
  server: { port: 5174 },
});

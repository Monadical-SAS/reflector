import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  client: "axios",
  name: "OpenApi",
  input: "http://127.0.0.1:1250/openapi.json",
  output: {
    path: "./app/api",
    format: "prettier",
  },
  services: {
    asClass: true,
  },
});

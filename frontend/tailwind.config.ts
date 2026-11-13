import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        clinic: {
          accent: "#0d6e7a",
          danger: "#b42318",
        },
      },
    },
  },
  plugins: [],
};
export default config;

import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0F766E",
          light: "#5EEAD4",
          dark: "#115E59"
        }
      }
    }
  },
  plugins: []
};

export default config;
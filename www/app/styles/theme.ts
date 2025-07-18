import {
  createSystem,
  defaultConfig,
  defineConfig,
  defineRecipe,
} from "@chakra-ui/react";
import { Poppins } from "next/font/google";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["200", "400", "600"],
  display: "swap",
});

// Define the accordion recipe for v3
const accordionRecipe = defineRecipe({
  className: "accordion",
  base: {
    container: {
      border: "0",
      borderRadius: "8px",
      backgroundColor: "white",
      mb: "2",
      mr: "2",
    },
    panel: {
      pl: "8",
      pb: "0",
    },
    button: {
      justifyContent: "flex-start",
      pl: "2",
    },
  },
  variants: {
    variant: {
      custom: {
        container: {
          border: "0",
          borderRadius: "8px",
          backgroundColor: "white",
          mb: "2",
          mr: "2",
        },
        panel: {
          pl: "8",
          pb: "0",
        },
        button: {
          justifyContent: "flex-start",
          pl: "2",
        },
      },
    },
  },
});

// Define the link recipe for v3
const linkRecipe = defineRecipe({
  className: "link",
  base: {
    _hover: {
      color: "blue.500",
      textDecoration: "none",
    },
  },
});

export const colors = {
  blue: {
    primary: { value: "#3158E2" },
    500: { value: "#3158E2" },
    light: { value: "#B1CBFF" },
    200: { value: "#B1CBFF" },
    dark: { value: "#0E1B48" },
    900: { value: "#0E1B48" },
  },
  red: {
    primary: { value: "#DF7070" },
    500: { value: "#DF7070" },
    light: { value: "#FBD5D5" },
    200: { value: "#FBD5D5" },
  },
  gray: {
    bg: { value: "#F4F4F4" },
    100: { value: "#F4F4F4" },
    light: { value: "#D5D5D5" },
    200: { value: "#D5D5D5" },
    primary: { value: "#838383" },
    500: { value: "#838383" },
  },
  light: { value: "#FFFFFF" },
  dark: { value: "#0C0D0E" },
};

const config = defineConfig({
  theme: {
    tokens: {
      colors,
      fonts: {
        body: { value: poppins.style.fontFamily },
        heading: { value: poppins.style.fontFamily },
      },
    },
    recipes: {
      accordion: accordionRecipe,
      link: linkRecipe,
    },
  },
});

export const system = createSystem(defaultConfig, config);

export default system;

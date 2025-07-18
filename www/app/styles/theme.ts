import {
  createSystem,
  defaultConfig,
  defineConfig,
  defineRecipe,
  defaultSystem,
} from "@chakra-ui/react";

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
    textDecoration: "none",
    _hover: {
      color: "blue.500",
      textDecoration: "none",
    },
    _focus: {
      outline: "none",
      boxShadow: "none",
    },
    _focusVisible: {
      outline: "none",
      boxShadow: "none",
    },
  },
});

// Define button recipe with custom font weight
const buttonRecipe = defineRecipe({
  base: {
    fontWeight: "600",
    bg: "gray.100",
    color: "gray.800",
    _hover: {
      bg: "gray.200",
    },
  },
  variants: {
    variant: {
      solid: {
        bg: "gray.100",
        color: "gray.800",
        _hover: {
          bg: "gray.200",
        },
      },
    },
  },
  defaultVariants: {
    variant: "solid",
  },
  compoundVariants: [
    {
      colorPalette: "whiteAlpha",
      css: {
        bg: "whiteAlpha.500",
        color: "white",
        _hover: {
          bg: "whiteAlpha.600",
          opacity: 1,
        },
      },
    },
  ],
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
    800: { value: "#1A202C" },
  },
  whiteAlpha: {
    50: { value: "rgba(255, 255, 255, 0.04)" },
    100: { value: "rgba(255, 255, 255, 0.06)" },
    200: { value: "rgba(255, 255, 255, 0.08)" },
    300: { value: "rgba(255, 255, 255, 0.16)" },
    400: { value: "rgba(255, 255, 255, 0.24)" },
    500: { value: "rgba(255, 255, 255, 0.36)" },
    600: { value: "rgba(255, 255, 255, 0.48)" },
    700: { value: "rgba(255, 255, 255, 0.64)" },
    800: { value: "rgba(255, 255, 255, 0.80)" },
    900: { value: "rgba(255, 255, 255, 0.92)" },
  },
  light: { value: "#FFFFFF" },
  dark: { value: "#0C0D0E" },
};

const config = defineConfig({
  theme: {
    tokens: {
      colors,
    },
    semanticTokens: {
      colors: {
        whiteAlpha: {
          solid: { value: "{colors.whiteAlpha.500}" },
          contrast: { value: "{colors.white}" },
          fg: { value: "{colors.white}" },
          muted: { value: "{colors.whiteAlpha.100}" },
          subtle: { value: "{colors.whiteAlpha.50}" },
          emphasized: { value: "{colors.whiteAlpha.600}" },
          focusRing: { value: "{colors.whiteAlpha.500}" },
        },
      },
    },
    recipes: {
      accordion: accordionRecipe,
      link: linkRecipe,
      button: buttonRecipe,
    },
  },
});

export const system = createSystem(defaultConfig, config);

export default system;

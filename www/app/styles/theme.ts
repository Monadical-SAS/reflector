import {
  createSystem,
  defaultConfig,
  defineConfig,
  defineRecipe,
  defineSlotRecipe,
  defaultSystem,
} from "@chakra-ui/react";

const accordionSlotRecipe = defineSlotRecipe({
  slots: [
    "root",
    "container",
    "item",
    "itemTrigger",
    "itemContent",
    "itemIndicator",
  ],
  base: {
    item: {
      bg: "white",
      borderRadius: "xl",
      border: "0",
      mb: "2",
      width: "full",
    },
    itemTrigger: {
      p: "2",
      cursor: "pointer",
      _hover: {
        bg: "gray.200",
      },
    },
  },
});

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

const buttonRecipe = defineRecipe({
  base: {
    fontWeight: "600",
    _hover: {
      bg: "gray.200",
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
  variants: {
    variant: {
      solid: {
        bg: "gray.100",
        color: "gray.800",
        _hover: {
          bg: "gray.200",
        },
      },
      primary: {
        bg: "blue.500",
        color: "white",
        _hover: {
          bg: "blue.400",
        },
      },
      outline: {
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
      fonts: {
        heading: { value: "Poppins, sans-serif" },
        body: { value: "Poppins, sans-serif" },
      },
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
    slotRecipes: {
      accordion: accordionSlotRecipe,
    },
    recipes: {
      link: linkRecipe,
      button: buttonRecipe,
    },
  },
});

export const system = createSystem(defaultConfig, config);

export default system;

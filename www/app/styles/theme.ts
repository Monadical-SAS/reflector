import { extendTheme } from "@chakra-ui/react";
import { Poppins } from "next/font/google";
import { accordionAnatomy } from "@chakra-ui/anatomy";
import { createMultiStyleConfigHelpers, defineStyle } from "@chakra-ui/react";

const { definePartsStyle, defineMultiStyleConfig } =
  createMultiStyleConfigHelpers(accordionAnatomy.keys);

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["200", "400", "600"],
  display: "swap",
});
const custom = definePartsStyle({
  container: {
    border: "0",
    borderRadius: "8px",
    backgroundColor: "white",
    mb: 2,
    mr: 2,
  },
  panel: {
    pl: 8,
    pb: 0,
  },
  button: {
    justifyContent: "flex-start",
    pl: 2,
  },
});

const accordionTheme = defineMultiStyleConfig({
  variants: { custom },
});

const linkTheme = defineStyle({
  baseStyle: {
    _hover: {
      color: "blue.500",
      textDecoration: "none",
    },
  },
});
export const colors = {
  blue: {
    primary: "#3158E2",
    500: "#3158E2",
    light: "#B1CBFF",
    200: "#B1CBFF",
    dark: "#0E1B48",
    900: "#0E1B48",
  },
  red: {
    primary: "#DF7070",
    500: "#DF7070",
    light: "#FBD5D5",
    200: "#FBD5D5",
  },
  gray: {
    bg: "#F4F4F4",
    100: "#F4F4F4",
    light: "#D5D5D5",
    200: "#D5D5D5",
    primary: "#838383",
    500: "#838383",
  },
  light: "#FFFFFF",
  dark: "#0C0D0E",
};

const theme = extendTheme({
  colors,
  components: {
    Accordion: accordionTheme,
    Link: linkTheme,
  },
  fonts: {
    body: poppins.style.fontFamily,
    heading: poppins.style.fontFamily,
  },
});

export default theme;

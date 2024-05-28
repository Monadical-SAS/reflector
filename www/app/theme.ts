// 1. Import `extendTheme`
import { extendTheme } from "@chakra-ui/react";

// 2. Call `extendTheme` and pass your custom values
const theme = extendTheme({
  colors: {
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
  },
});

export default theme;

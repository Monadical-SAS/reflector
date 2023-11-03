const plugin = require("tailwindcss/plugin");

module.exports = plugin(function ({ addUtilities }) {
  const newUtilities = {
    ".open-modal-button": {
      display: "inline-flex",
      alignItems: "flex-start",
      justifyContent: "flex-start",
      textAlign: "left",
      textDecoration: "underline",
      textDecorationThickness: ".5px",
      textDecorationStyle: "solid",
      textDecorationColor: "inherit",
      textUnderlineOffset: "2px",
      fontWeight: 600,
      paddingLeft: "0",
      color: "#ffffff",
      fontSize: "15px",
      fontFamily: '"Poppins", sans-serif',
      lineHeight: "normal",
    },
    ".open-modal-button:hover": {
      textDecoration: "none",
    },
    ".blue-button": {
      justifyContent: "center",
      alignItems: "center",
      padding: "0.375rem 1rem", // py-1.5 px-4
      gap: "0.625rem", // gap-2.5
      borderRadius: "0.25rem", // rounded
      backgroundColor: "#3158E2",
      color: "white",
      fontSize: "1rem", // text-base
      fontWeight: 600, // font-semibold
    },
  };

  addUtilities(newUtilities);
});

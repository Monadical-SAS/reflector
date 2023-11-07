const plugin = require("tailwindcss/plugin");

module.exports = plugin(function ({ addUtilities }) {
  const newUtilities = {
    ".open-modal-button": {
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
    ".splash-screen": {
      display: "flex", // flex
      flex: "1", // flex-1
      flexDirection: "row", // flex-row
      padding: "0.75rem", // p-3
      alignItems: "flex-start", // items-start
      alignSelf: "stretch", // self-stretch
      borderRadius: "0.75rem", // rounded-lg
      backgroundColor: "rgba(255, 255, 255, var(--tw-bg-opacity))",
      boxShadow: "0px 4px 4px 0px rgba(0, 0, 0, 0.25)",
      "--tw-border-radius": "20px",
      "--tw-bg-opacity": "1",
    },
  };

  addUtilities(newUtilities);
});

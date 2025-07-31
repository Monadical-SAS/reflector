// Hardcoded colors for now - can be replaced with token system in Chakra v3
export const waveSurferStyles = {
  playerSettings: {
    waveColor: "#3182ce",
    progressColor: "#2c5282",
    cursorColor: "#e53e3e",
    hideScrollbar: true,
    autoScroll: false,
    autoCenter: false,
    barWidth: 3,
    barGap: 2,
    cursorWidth: 2,
  },
  playerStyle: {
    cursor: "pointer",
  },
  marker: `
    border-left: solid 1px orange;
    padding: 0 2px 0 5px;
    font-size: 0.7rem;
    border-radius: 0 3px 3px 0;
    top: 0;
    width: 100px;
    max-width: fit-content;
    cursor: pointer;
    background-color: white;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: width 100ms linear;
    z-index: 0;
  `,
  markerHover: { backgroundColor: "#e2e8f0" },
};

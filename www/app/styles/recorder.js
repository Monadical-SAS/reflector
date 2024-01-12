export const waveSurferStyles = {
  playerSettings: {
    waveColor: "#777",
    progressColor: "#222",
    cursorColor: "OrangeRed",
  },
  playerStyle: {
    cursor: "pointer",
    backgroundColor: "RGB(240 240 240)",
    borderRadius: "15px",
  },
  marker: `
    border-left: solid 1px orange;
    padding: 0 2px 0 5px;
    font-size: 0.7rem;
    border-radius: 0 3px 3px 0;

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
  markerHover: { backgroundColor: "orange" },
};

import { useEffect, useState } from "react";
import Peer from "simple-peer";

const WebRTC_SERVER_URL = "http://127.0.0.1:1250/offer";

const useWebRTC = (stream, setIsRecording) => {
  const [data, setData] = useState({
    peer: null,
  });

  useEffect(() => {
    if (!stream) {
      return;
    }

    let peer = new Peer({ initiator: true, stream: stream });

    peer.on("signal", (data) => {
      if ("sdp" in data) {
        fetch(WebRTC_SERVER_URL, {
          body: JSON.stringify({
            sdp: data.sdp,
            type: data.type,
          }),
          headers: {
            "Content-Type": "application/json",
          },
          method: "POST",
        })
          .then((response) => response.json())
          .then((answer) => peer.signal(answer))
          .catch((e) => {
            console.log("Error signaling:", e);
          });
      }
    });

    peer.on("connect", () => {
      console.log("WebRTC connected");
      setData((prevData) => ({ ...prevData, peer: peer }));
    });

    peer.on("data", (data) => {
      const serverData = JSON.parse(data.toString());
      console.log(serverData);

      switch (serverData.cmd) {
        case "SHOW_TRANSCRIPTION":
          setData((prevData) => ({
            ...prevData,
            text: serverData.text,
          }));
          break;
        case "UPDATE_TOPICS":
          setData((prevData) => ({
            ...prevData,
            topics: serverData.topics,
          }));
          break;
        case "DISPLAY_FINAL_SUMMARY":
          setData((prevData) => ({
            ...prevData,
            finalSummary: {
              duration: serverData.duration,
              summary: serverData.summary,
            },
            text: ''
          }));
          setIsRecording(false);
          break;
        default:
          console.error(`Unknown command ${serverData.cmd}`);
      }
    });

    return () => {
      peer.destroy();
    };
  }, [stream, setIsRecording]);

  return data;
};

export default useWebRTC;

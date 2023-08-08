import { useEffect, useState } from "react";
import Peer from "simple-peer";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const useWebRTC = (stream, transcript) => {
  const [data, setData] = useState({
    peer: null,
  });

  useEffect(() => {
    if (!stream || !transcript) {
      return;
    }
    const url = `${API_URL}/v1/transcripts/${transcript.id}/record/webrtc`;
    console.log("Sending RTC Offer", url, transcript);

    let peer = new Peer({ initiator: true, stream: stream });

    peer.on("signal", (data) => {
      if ("sdp" in data) {
        const rtcOffer = {
          sdp: data.sdp,
          type: data.type,
        };

        axios
          .post(url, rtcOffer, {
            headers: {
              "Content-Type": "application/json",
            },
          })
          .then((response) => {
            const answer = response.data;
            console.log("Answer:", answer);
            peer.signal(answer);
          })
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
            text: "",
          }));
          break;
        default:
          console.error(`Unknown command ${serverData.cmd}`);
      }
    });

    return () => {
      peer.destroy();
    };
  }, [stream, transcript]);

  return data;
};

export default useWebRTC;

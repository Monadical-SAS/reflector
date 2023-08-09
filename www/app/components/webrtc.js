import { useEffect, useState } from "react";
import Peer from "simple-peer";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const useWebRTC = (stream, transcriptId) => {
  const [data, setData] = useState({
    peer: null,
  });

  useEffect(() => {
    if (!stream || !transcriptId) {
      return;
    }
    const url = `${API_URL}/v1/transcripts/${transcriptId}/record/webrtc`;

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
            peer.signal(answer);
          })
          .catch((e) => {
            console.error("WebRTC signaling error:", e);
          });
      }
    });

    peer.on("connect", () => {
      console.log("WebRTC connected");
      setData((prevData) => ({ ...prevData, peer: peer }));
    });

    return () => {
      peer.destroy();
    };
  }, [stream, transcriptId]);

  return data;
};

export default useWebRTC;

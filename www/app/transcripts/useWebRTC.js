import { useEffect, useState } from "react";
import Peer from "simple-peer";
import { DefaultApi } from "../api/apis/DefaultApi";
import { Configuration } from "../api/runtime";

const useWebRTC = (stream, transcriptId) => {
  const [data, setData] = useState({
    peer: null,
  });

  useEffect(() => {
    if (!stream || !transcriptId) {
      return;
    }

    const apiConfiguration = new Configuration({
      basePath: process.env.NEXT_PUBLIC_API_URL,
    });
    const api = new DefaultApi(apiConfiguration);

    let peer = new Peer({ initiator: true, stream: stream });

    peer.on("signal", (data) => {
      if ("sdp" in data) {
        const requestParameters = {
          transcriptId: transcriptId,
          rtcOffer: {
            sdp: data.sdp,
            type: data.type,
          },
        };

        api
          .v1TranscriptRecordWebrtc(requestParameters)
          .then((answer) => {
            peer.signal(answer);
          })
          .catch((err) => {
            console.error("WebRTC signaling error:", err);
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

import { useEffect, useState } from "react";
import Peer from "simple-peer";
import {
  DefaultApi,
  V1TranscriptRecordWebrtcRequest,
} from "../api/apis/DefaultApi";
import { Configuration } from "../api/runtime";

const useWebRTC = (
  stream: MediaStream | null,
  transcriptId: string | null,
  api: DefaultApi,
): Peer => {
  const [peer, setPeer] = useState<Peer | null>(null);

  useEffect(() => {
    if (!stream || !transcriptId) {
      return;
    }

    let p: Peer = new Peer({ initiator: true, stream: stream });

    p.on("signal", (data: any) => {
      if ("sdp" in data) {
        const requestParameters: V1TranscriptRecordWebrtcRequest = {
          transcriptId: transcriptId,
          rtcOffer: {
            sdp: data.sdp,
            type: data.type,
          },
        };

        api
          .v1TranscriptRecordWebrtc(requestParameters)
          .then((answer) => {
            p.signal(answer);
          })
          .catch((err) => {
            console.error("WebRTC signaling error:", err);
          });
      }
    });

    p.on("connect", () => {
      console.log("WebRTC connected");
      setPeer(p);
    });

    return () => {
      p.destroy();
    };
  }, [stream, transcriptId]);

  return peer;
};

export default useWebRTC;

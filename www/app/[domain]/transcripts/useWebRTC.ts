import { useEffect, useState } from "react";
import Peer from "simple-peer";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { RtcOffer } from "../../api";

const useWebRTC = (
  stream: MediaStream | null,
  transcriptId: string | null,
): Peer => {
  const [peer, setPeer] = useState<Peer | null>(null);
  const { setError } = useError();
  const api = useApi();

  useEffect(() => {
    if (!stream || !transcriptId) {
      return;
    }

    console.debug("Using WebRTC", stream, transcriptId);

    let p: Peer;

    try {
      p = new Peer({ initiator: true, stream: stream });
    } catch (error) {
      setError(error, "Error creating WebRTC");
      return;
    }

    p.on("error", (err) => {
      setError(new Error(`WebRTC error: ${err}`));
    });

    p.on("signal", (data: any) => {
      if (!api) return;
      if ("sdp" in data) {
        const rtcOffer: RtcOffer = {
          sdp: data.sdp,
          type: data.type,
        };

        api
          .v1TranscriptRecordWebrtc(transcriptId, rtcOffer)
          .then((answer) => {
            try {
              p.signal(answer);
            } catch (error) {
              setError(error);
            }
          })
          .catch((error) => {
            setError(error, "Error loading WebRTCOffer");
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

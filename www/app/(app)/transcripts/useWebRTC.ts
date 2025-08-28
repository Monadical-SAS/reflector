import { useEffect, useState } from "react";
import Peer from "simple-peer";
import { useError } from "../../(errors)/errorContext";
import { useTranscriptWebRTC } from "../../lib/api-hooks";
import { RtcOffer } from "../../lib/api-types";

const useWebRTC = (
  stream: MediaStream | null,
  transcriptId: string | null,
): Peer => {
  const [peer, setPeer] = useState<Peer | null>(null);
  const { setError } = useError();
  const webRTCMutation = useTranscriptWebRTC();

  useEffect(() => {
    if (!stream || !transcriptId) {
      return;
    }

    console.debug("Using WebRTC", stream, transcriptId);

    let p: Peer;

    try {
      p = new Peer({ initiator: true, stream: stream });
    } catch (error) {
      setError(error as Error, "Error creating WebRTC");
      return;
    }

    p.on("error", (err) => {
      setError(new Error(`WebRTC error: ${err}`));
    });

    p.on("signal", async (data: any) => {
      if ("sdp" in data) {
        const rtcOffer: RtcOffer = {
          sdp: data.sdp,
          type: data.type,
        };

        try {
          const answer = await webRTCMutation.mutateAsync({
            params: {
              path: {
                transcript_id: transcriptId,
              },
            },
            body: rtcOffer,
          });

          try {
            p.signal(answer);
          } catch (error) {
            setError(error as Error);
          }
        } catch (error) {
          setError(error as Error, "Error loading WebRTCOffer");
        }
      }
    });

    p.on("connect", () => {
      console.log("WebRTC connected");
      setPeer(p);
    });

    return () => {
      p.destroy();
    };
  }, [stream, transcriptId, webRTCMutation]);

  return peer;
};

export default useWebRTC;

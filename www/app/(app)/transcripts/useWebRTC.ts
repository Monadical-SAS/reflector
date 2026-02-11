import { useEffect, useState } from "react";
import Peer from "simple-peer";
import { useError } from "../../(errors)/errorContext";
import { useTranscriptWebRTC } from "../../lib/apiHooks";
import type { components } from "../../reflector-api";
type RtcOffer = components["schemas"]["RtcOffer"];

const useWebRTC = (
  stream: MediaStream | null,
  transcriptId: string | null,
): Peer => {
  const [peer, setPeer] = useState<Peer | null>(null);
  const { setError } = useError();
  const { mutateAsync: mutateWebRtcTranscriptAsync } = useTranscriptWebRTC();

  useEffect(() => {
    if (!stream || !transcriptId) {
      return;
    }

    console.debug("Using WebRTC", stream, transcriptId);

    let p: Peer;

    try {
      p = new Peer({
        initiator: true,
        stream: stream,
        // Disable trickle ICE: single SDP exchange (offer + answer) with all candidates.
        // Required for HTTP-based signaling; trickle needs WebSocket for candidate exchange.
        trickle: false,
        config: {
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        },
      });
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
          const answer = await mutateWebRtcTranscriptAsync({
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
  }, [stream, transcriptId, mutateWebRtcTranscriptAsync]);

  return peer;
};

export default useWebRTC;

import { useEffect, useState } from "react";
import Peer from "simple-peer";
import {
  DefaultApi,
  V1TranscriptRecordWebrtcRequest,
} from "../../api/apis/DefaultApi";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";

const useWebRTC = (
  stream: MediaStream | null,
  transcriptId: string | null,
  protectedPath,
): Peer => {
  const [peer, setPeer] = useState<Peer | null>(null);
  const { setError } = useError();
  const api = getApi(protectedPath);

  useEffect(() => {
    if (!stream || !transcriptId) {
      return;
    }

    console.debug("Using WebRTC", stream, transcriptId);

    let p: Peer;

    try {
      p = new Peer({ initiator: true, stream: stream });
    } catch (error) {
      setError(error);
      return;
    }

    p.on("error", (err) => {
      setError(new Error(`WebRTC error: ${err}`));
    });

    p.on("signal", (data: any) => {
      if (!api) return;
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
            try {
              p.signal(answer);
            } catch (error) {
              setError(error);
            }
          })
          .catch((error) => {
            setError(error);
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

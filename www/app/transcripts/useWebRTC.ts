import { useEffect, useState } from "react";
import Peer from "simple-peer";
import {
  DefaultApi,
  V1TranscriptRecordWebrtcRequest,
} from "../api/apis/DefaultApi";
import { useError } from "../(errors)/errorContext";
import handleError from "../(errors)/handleError";

const useWebRTC = (
  stream: MediaStream | null,
  transcriptId: string | null,
  api: DefaultApi,
): Peer => {
  const [peer, setPeer] = useState<Peer | null>(null);
  const { setError } = useError();

  useEffect(() => {
    if (!stream || !transcriptId) {
      return;
    }

    let p: Peer;

    try {
      p = new Peer({ initiator: true, stream: stream });
    } catch (error) {
      handleError(
        setError,
        `Failed to create WebRTC Peer: ${error.message}`,
        error,
      );
      return;
    }

    p.on("error", (err) => {
      handleError(setError, `WebRTC error: ${err.message}`, err);
    });

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
            try {
              p.signal(answer);
            } catch (error) {
              handleError(
                setError,
                `Failed to signal answer: ${error.message}`,
                error,
              );
            }
          })
          .catch((err) => {
            const errorString =
              "WebRTC signaling error: " +
              (err.response || err.message || "Unknown error");
            handleError(setError, errorString, err);
            console.error(errorString);
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

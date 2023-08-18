"use client";
import React, { useEffect, useState } from "react";
import Recorder from "../recorder";
import { Dashboard } from "../dashboard";
import useWebRTC from "../useWebRTC";
import useTranscript from "../useTranscript";
import { useWebSockets } from "../useWebSockets";
import "../../styles/button.css";

const App = () => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [disconnected, setDisconnected] = useState<boolean>(false);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_ENV === "development") {
      document.onkeyup = (e) => {
        if (e.key === "d") {
          setDisconnected((prev) => !prev);
        }
      };
    }
  }, []);

  const transcript = useTranscript();
  const webRTC = useWebRTC(stream, transcript.response?.id);
  const webSockets = useWebSockets(transcript.response?.id);

  return (
    <>
      <Recorder
        setStream={setStream}
        onStop={() => {
          webRTC?.peer?.send(JSON.stringify({ cmd: "STOP" }));
          setStream(null);
        }}
      />

      <hr />

      <Dashboard
        transcriptionText={webSockets.transcriptText}
        finalSummary={webSockets.finalSummary}
        topics={webSockets.topics}
        disconnected={disconnected}
      />
    </>
  );
};

export default App;

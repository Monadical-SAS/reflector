"use client";
import React, { useEffect, useState } from "react";
import Recorder from "./components/record.js";
import { Dashboard } from "./components/dashboard.js";
import useWebRTC from "./components/webrtc.js";
import useTranscript from "./components/transcript.js";
import { useWebSockets } from "./components/websocket.js";
import "../public/button.css";

const App = () => {
  const [stream, setStream] = useState(null);
  const [disconnected, setDisconnected] = useState(false);
  const useActiveTopic = useState(null);

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
    <div className="flex flex-col items-center h-[100svh] bg-gradient-to-r from-[#8ec5fc30] to-[#e0c3fc42]">
      <div className="h-[13svh] flex flex-col justify-center items-center">
        <h1 className="text-5xl font-bold text-blue-500">Reflector</h1>
        <p className="text-gray-500">Capture The Signal, Not The Noise</p>
      </div>

      <Recorder
        setStream={setStream}
        onStop={() => {
          webRTC?.peer?.send(JSON.stringify({ cmd: "STOP" }));
          setStream(null);
        }}
        topics={webSockets.topics}
        useActiveTopic={useActiveTopic}
      />
      <Dashboard
        transcriptionText={webSockets.transcriptText}
        finalSummary={webSockets.finalSummary}
        topics={webSockets.topics}
        stream={stream}
        disconnected={disconnected}
        useActiveTopic={useActiveTopic}
      />
    </div>
  );
};

export default App;

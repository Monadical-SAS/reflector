"use client";
import React, { useState } from "react";
import Recorder from "./components/record.js";
import { Dashboard } from "./components/dashboard.js";
import useWebRTC from "./components/webrtc.js";
import "../public/button.css";

const App = () => {
  const [stream, setStream] = useState(null);

  // This is where you'd send the stream and receive the data from the server.
  // transcription, summary, etc
  const serverData = useWebRTC(stream);

  const sendStopCmd = () =>
    serverData?.peer?.send(JSON.stringify({ cmd: "STOP" }));

  return (
    <div className="flex flex-col items-center h-[100svh] bg-gradient-to-r from-[#8ec5fc30] to-[#e0c3fc42]">
      <div className="h-[13svh] flex flex-col justify-center items-center">
        <h1 className="text-5xl font-bold text-blue-500">Reflector</h1>
        <p className="text-gray-500">Capture The Signal, Not The Noise</p>
      </div>

      <Recorder setStream={setStream} onStop={sendStopCmd} />
      <Dashboard
        transcriptionText={serverData.text ?? "(No transcription yet)"}
        finalSummary={serverData.finalSummary}
        topics={serverData.topics ?? []}
        stream={stream}
      />
    </div>
  );
};

export default App;

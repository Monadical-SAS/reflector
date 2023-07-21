"use client";
import React, { useState } from "react";
import Recorder from "./components/record.js";
import { Dashboard } from "./components/dashboard.js";
import useWebRTC from "./components/webrtc.js";
import "../public/button.css";

const App = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [stream, setStream] = useState(null);

  const handleRecord = (recording) => {
    setIsRecording(recording);

    if (recording) {
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then(setStream)
        .catch((err) => console.error(err));
    } else if (!recording && serverData.peer) {
      serverData.peer.send(JSON.stringify({ cmd: "STOP" }));
    }
  };

  const serverData = useWebRTC(stream, setIsRecording);

  return (
    <div className="flex flex-col items-center h-[100svh]">
      <div className="text-center py-6 mt-10">
        <h1 className="text-5xl font-bold text-blue-500">Reflector</h1>
        <p className="text-gray-500">Capture The Signal, Not The Noise</p>
      </div>

      <Recorder setStream={setStream} serverData={serverData} />
      <Dashboard
        isRecording={isRecording}
        onRecord={(recording) => handleRecord(recording)}
        transcriptionText={serverData.text ?? "..."}
        finalSummary={serverData.finalSummary}
        topics={serverData.topics ?? []}
        stream={stream}
      />
    </div>
  );
};

export default App;

"use client";
import React, { useState } from "react";
import Record from "./components/record.js";
import { Dashboard } from "./components/dashboard.js";
import useWebRTC from "./components/webrtc.js";
import "../public/button.css";

const App = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [splashScreen, setSplashScreen] = useState(true);
  const [stream, setStream] = useState(null);

  const handleRecord = (recording) => {
    setIsRecording(recording);
    setSplashScreen(false);

    if (recording) {
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then(setStream)
        .catch((err) => console.error(err));
    } else if (!recording && serverData.peer) {
      serverData.peer.send(JSON.stringify({ cmd: 'STOP' }));
    }
  };


  const serverData = useWebRTC(stream, setIsRecording);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      {splashScreen && (
        <Record
          isRecording={isRecording}
          onRecord={(recording) => handleRecord(recording)}
        />
      )}
      {!splashScreen && (
        <Dashboard
          isRecording={isRecording}
          onRecord={(recording) => handleRecord(recording)}
          transcriptionText={serverData.text ?? "(No transcription text)"}
          finalSummary={serverData.finalSummary}
          topics={serverData.topics ?? []}
          stream={stream}
        />
      )}
    </div>
  );
};

export default App;

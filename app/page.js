"use client";
import React, { useState, useEffect } from "react";
import Record from "./components/record.js";
import { Dashboard } from "./components/dashboard.js";
import useWebRTC from "./components/webrtc.js";
import "../public/button.css";

const App = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [splashScreen, setSplashScreen] = useState(true);

  const handleRecord = (recording) => {
    console.log("handleRecord", recording);

    setIsRecording(recording);
    setSplashScreen(false);

    if (recording) {
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then(setStream)
        .catch((err) => console.error(err));
    } else if (!recording) {
      if (stream) {
        const tracks = stream.getTracks();
        tracks.forEach((track) => track.stop());
        setStream(null);
      }

      setIsRecording(false);
    }
  };

  const [stream, setStream] = useState(null);
  const serverData = useWebRTC(stream);
  const text = serverData?.text ?? "";

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
          transcriptionText={`[${serverData?.timestamp?.substring(2) ?? "??"}] ${text}`}
        />
      )}
    </div>
  );
};

export default App;

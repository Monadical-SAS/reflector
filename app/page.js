"use client";
import React, { useState, useEffect } from "react";
import Recorder from "./components/record.js";
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
  console.log(serverData);

  return (
    <div className="flex flex-col items-center h-[100svh]">
      <div className="text-center py-6 mt-10">
        <h1 className="text-5xl font-bold text-blue-500">Reflector</h1>
        <p className="text-gray-500">Capture The Signal, Not The Noise</p>
      </div>

      <Recorder
        isRecording={isRecording}
        onRecord={(recording) => handleRecord(recording)}
      />

      {!splashScreen && (
        <Dashboard
          isRecording={isRecording}
          onRecord={(recording) => handleRecord(recording)}
        />
      )}

      <footer className="w-full bg-gray-800 text-center py-4 mt-auto text-white">
        Reflector © 2023 Monadical
      </footer>
    </div>
  );
};

export default App;

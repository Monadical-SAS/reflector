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
  const text = serverData?.text ?? "";

  return (
    <div className="flex flex-col items-center h-[100svh]">
      <div className="text-center py-6 mt-10">
        <h1 className="text-5xl font-bold text-blue-500">Reflector</h1>
        <p className="text-gray-500">Capture The Signal, Not The Noise</p>
      </div>

      <Recorder setStream={setStream}/>
      <Dashboard
        serverData={serverData}
        transcriptionText={`[${serverData?.timestamp?.substring(2) ?? "??"}] ${text}`}
      />

      <footer className="w-full bg-gray-800 text-center py-4 mt-auto text-white">
        Reflector © 2023 Monadical
      </footer>
    </div>
  );
};

export default App;

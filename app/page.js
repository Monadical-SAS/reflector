"use client"
import React, { useState, useEffect } from 'react';
import Record from './components/record.js';
import { Dashboard } from './components/dashboard.js';
import useWebRTC from './components/webrtc.js';

const App = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [splashScreen, setSplashScreen] = useState(true);
  
  
  
  const handleRecord = (recording) => {
    setIsRecording(recording);
    setSplashScreen(false);
  };
  
  const [stream, setStream] = useState(null);
  const serverData = useWebRTC(stream);
  console.log(serverData);

  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(setStream)
      .catch(err => console.error(err));
  }, []);
  
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        {splashScreen && <Record isRecording={isRecording} onRecord={(recording) => handleRecord(recording)} /> }
        {!splashScreen && <Dashboard />}
      </div>
    );

}


export default App;
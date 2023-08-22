"use client";
import React, { useEffect, useState } from "react";
import Recorder from "../recorder";
import { Dashboard } from "../dashboard";
import useWebRTC from "../useWebRTC";
import useTranscript from "../useTranscript";
import { useWebSockets } from "../useWebSockets";
import useAudioDevice from "../useAudioDevice";
import "../../styles/button.css";
import getApi from "../../lib/getApi";

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

  const api = getApi();
  const transcript = useTranscript();
  const webRTC = useWebRTC(stream, transcript.response?.id, api);
  const webSockets = useWebSockets(transcript.response?.id);
  const {
    loading,
    permissionOk,
    audioDevices,
    requestPermission,
    getAudioStream,
  } = useAudioDevice();

  return (
    <div className="w-full flex flex-col items-center h-[100svh]">
      {permissionOk ? (
        <>
          <Recorder
            setStream={setStream}
            onStop={() => {
              webRTC?.peer?.send(JSON.stringify({ cmd: "STOP" }));
              setStream(null);
            }}
            getAudioStream={getAudioStream}
            audioDevices={audioDevices}
          />

          <Dashboard
            transcriptionText={webSockets.transcriptText}
            finalSummary={webSockets.finalSummary}
            topics={webSockets.topics}
            disconnected={disconnected}
          />
        </>
      ) : (
        <>
          <div className="flex flex-col items-center justify-center w-fit bg-white px-6 py-8 mt-8 rounded-xl">
            <h1 className="text-2xl font-bold text-blue-500">
              Audio Permissions
            </h1>
            {loading ? (
              <p className="text-gray-500 text-center mt-5">
                Checking permission...
              </p>
            ) : (
              <>
                <p className="text-gray-500 text-center mt-5">
                  Reflector needs access to your microphone to work.
                  <br />
                  Please grant permission to continue.
                </p>
                <button
                  className="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded m-auto"
                  onClick={requestPermission}
                >
                  Grant Permission
                </button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default App;

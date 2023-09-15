"use client";
import React, { useEffect, useState } from "react";
import Recorder from "../recorder";
import { Dashboard } from "../dashboard";
import useWebRTC from "../useWebRTC";
import useTranscript from "../useTranscript";
import { useWebSockets } from "../useWebSockets";
import useAudioDevice from "../useAudioDevice";
import "../../styles/button.css";
import { Topic } from "../webSocketTypes";
import getApi from "../../lib/getApi";

const TranscriptCreate = () => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [disconnected, setDisconnected] = useState<boolean>(false);
  const useActiveTopic = useState<Topic | null>(null);

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
  const transcript = useTranscript(stream, api);
  const webRTC = useWebRTC(stream, transcript?.response?.id, api);
  const webSockets = useWebSockets(transcript?.response?.id);
  const {
    loading,
    permissionOk,
    permissionDenied,
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
            topics={webSockets.topics}
            getAudioStream={getAudioStream}
            audioDevices={audioDevices}
            useActiveTopic={useActiveTopic}
            isPastMeeting={false}
          />

          <Dashboard
            transcriptionText={webSockets.transcriptText}
            finalSummary={webSockets.finalSummary}
            topics={webSockets.topics}
            disconnected={disconnected}
            useActiveTopic={useActiveTopic}
          />
        </>
      ) : (
        <>
          <div className="flex flex-col items-center justify-center w-fit px-6 py-8 mt-8 rounded-xl">
            <h1 className="text-2xl font-bold">Audio Permissions</h1>
            {loading ? (
              <p className="text-gray-500 text-center mt-5">
                Checking permission...
              </p>
            ) : (
              <>
                <p className="text-gray-500 text-center mt-5">
                  Reflector needs access to your microphone to work.
                  <br />
                  {permissionDenied
                    ? "Please reset microphone permissions to continue."
                    : "Please grant permission to continue."}
                </p>
                <button
                  className="mt-4 bg-black/40 hover:bg-black/60 text-white font-bold py-2 px-4 rounded m-auto"
                  onClick={requestPermission}
                  disabled={permissionDenied}
                >
                  {permissionDenied ? "Access denied" : "Grant Permission"}
                </button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default TranscriptCreate;

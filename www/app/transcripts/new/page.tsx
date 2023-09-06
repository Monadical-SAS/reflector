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
import { isDevelopment } from "../../lib/utils";
import Image from "next/image";
import { formatTime } from "../../lib/time";

const App = () => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [disconnected, setDisconnected] = useState<boolean>(false);
  const useActiveTopic = useState<Topic | null>(null);

  useEffect(() => {
    document.onkeyup = (e) => {
      if (isDevelopment() && e.key === "d") {
        setDisconnected((prev) => !prev);
      }
    };
  }, []);

  const api = getApi();
  const transcript = useTranscript(api);
  const webRTC = useWebRTC(stream, transcript.response?.id, api);
  const webSockets = useWebSockets(transcript.response?.id);
  const {
    loading,
    permissionOk,
    permissionDenied,
    audioDevices,
    requestPermission,
    getAudioStream,
  } = useAudioDevice();
  const topicsToDisplay = 5;
  const realTopics = webSockets.topics.slice(-topicsToDisplay);
  const displayTopics = [
    ...realTopics,
    ...Array(topicsToDisplay - realTopics.length).fill(null),
  ];

  return (
    <>
      <header className="flex justify-between items-center py-4 bg-transparent">
        <div className="flex items-center">
          <Image
            src="/reach.png"
            width={16}
            height={16}
            className="h-6 w-auto ml-2"
            alt="Reflector"
          />

          <h1 className="text-lg">Reflector</h1>
        </div>

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
        />

        <span className="p-2 rounded-full">&nbsp;</span>
      </header>

      {/* Topic Section */}
      <section className="bg-red-200 p-4">
        {displayTopics.map((topic, index) => (
          <div key={topic?.id || index} className="bg-red-400 p-2 my-1 text-xl">
            {topic
              ? `[${formatTime(topic.timestamp)}] ${topic.title}`
              : "\u00A0"}
          </div>
        ))}
      </section>

      {/* Translation Section */}
      <section className="bg-light-blue p-4 h-1/2 flex items-center justify-center">
        <div className="text-center">
          <p className="text-4xl font-bold">{webSockets.transcriptText}</p>
        </div>
      </section>
    </>
  );

  /*
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
                  {permissionDenied
                    ? "Please reset microphone permissions to continue."
                    : "Please grant permission to continue."}
                </p>
                <button
                  className="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded m-auto"
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
  ); */
};

export default App;

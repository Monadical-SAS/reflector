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
import { formatTime, formatTimeDifference } from "../../lib/time";

const TranscriptCreate = () => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [disconnected, setDisconnected] = useState<boolean>(false);
  const useActiveTopic = useState<Topic | null>(null);
  const [recordingTime, setRecordingTime] = useState<number>(0);

  useEffect(() => {
    document.onkeyup = (e) => {
      if (isDevelopment() && e.key === "d") {
        setDisconnected((prev) => !prev);
      }
    };
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
  const topicsToDisplay = 5;
  const realTopics = webSockets.topics.slice(-topicsToDisplay);

  const displayTopics = [
    ...realTopics,
    ...Array(topicsToDisplay - realTopics.length + 1).fill(null),
  ] as (Topic | null)[];

  const timeLabel = (timestamp: number) => {
    return recordingTime
      ? formatTimeDifference(recordingTime - timestamp)
      : formatTime(timestamp);
  };

  return (
    <div className="bg-gradient-to-br from-blue-900 via-allin-blue via-50% to-allin-orange text-white min-h-screen p-4 flex flex-col">
      <header className="flex items-center">
        <div className="flex items-start mr-2 mb-2">
          <Image
            src="/reach.png"
            width={40}
            height={40}
            className="h-12 w-auto mt-2"
            alt="Reflector Logo"
          />
          <div className="p-2">
            <h1 className="text-3xl font-bold">Reflector</h1>
            <p className="text-xl font-light">reflector.media</p>
          </div>
        </div>

        <div className="flex-grow">
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
            recordingTime={recordingTime}
            setRecordingTime={setRecordingTime}
          />
        </div>
      </header>

      <div className="py-4 flex-grow flex flex-wrap justify-between">
        {/* Topic Section */}
        <section className="w-full lg:max-w-[45vw] min-w-[45vw] flex items-center lg:mr-2">
          <div className="bg-blue-100/10 rounded-lg md:rounded-xl w-full p-2 md:p-4 self-start lg:self-center">
            <p className="text-right text-lg font-light">Latest topics</p>
            {displayTopics.map((topic, index) => (
              <div
                key={topic?.id || index}
                className={`rounded-lg md:rounded-xl px-2 md:px-4 py-2 my-2 last:mb-0 text-lg md:text-xl leading-normal font-bold ${
                  topic ? "odd:bg-white/20" : ""
                }`}
              >
                {topic ? (
                  <>
                    <span className="font-light text-base md:text-lg inline-block align-middle font-mono">
                      {timeLabel(topic.timestamp)}:&nbsp;
                    </span>
                    {topic.title}
                  </>
                ) : (
                  "\u00A0"
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Translation Section */}
        <section className="flex-grow flex items-center justify-center lg:max-w-[49vw]">
          <div className="text-center p-4">
            <p className="text-2xl md:text-4xl font-bold">
              {webSockets.transcriptText}
            </p>
          </div>
        </section>
      </div>

      <footer className="flex justify-between items-center pt-2 border-t ">
        <Image
          src="/All-In_Logotype_Blanc_2L.png"
          width={40}
          height={40}
          className="h-14 ml-[-3px] w-auto"
          alt="All In Logo"
        />
        <Image
          src="/Monadical-BW-with-name.svg"
          width={40}
          height={40}
          className="h-16 mr-[-4px] w-auto"
          alt="Monadical Logo"
        />
      </footer>
    </div>
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

export default TranscriptCreate;

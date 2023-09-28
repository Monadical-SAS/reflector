"use client";
import React, { useEffect, useState } from "react";
import Recorder from "../recorder";
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
    ...Array(topicsToDisplay - realTopics.length).fill(null),
  ] as (Topic | null)[];

  const timeLabel = (timestamp: number) => {
    return recordingTime
      ? formatTimeDifference(recordingTime - timestamp)
      : formatTime(timestamp);
  };

  const [showEnglishText, setShowEnglishText] = useState<boolean>(true);
  const [showTranslatedText, setShowTranslatedText] = useState<boolean>(true);

  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.key === "#") {
        if (showEnglishText && showTranslatedText) {
          setShowEnglishText(false);
          setShowTranslatedText(true);
          return;
        }

        if (!showEnglishText && showTranslatedText) {
          setShowEnglishText(true);
          setShowTranslatedText(false);
          return;
        }

        if (showEnglishText && !showTranslatedText) {
          setShowEnglishText(true);
          setShowTranslatedText(true);
          return;
        }
      }
    };

    document.addEventListener("keydown", handleKeyPress);

    // Cleanup function to remove the event listener
    return () => {
      document.removeEventListener("keydown", handleKeyPress);
    };
  }, [showEnglishText, showTranslatedText]);

  return (
    <div className="bg-gradient-to-br from-blue-900 via-allin-blue via-50% to-allin-orange text-white min-h-screen p-2 md:p-3 lg:p-4 flex flex-col">
      <header className="flex items-center">
        <div className="flex items-start mr-2">
          <Image
            src="/Reflector_Logo.svg"
            width={80}
            height={80}
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

      <div className="py-2 md:py-3 lg:py-4 flex-grow flex flex-wrap justify-between">
        {/* Topic Section */}
        <section className="w-full lg:max-w-[45vw] min-w-[45vw] flex items-center lg:mr-2">
          <div className="bg-blue-100/10 rounded-lg md:rounded-xl w-full p-2 md:p-4 self-start lg:self-center">
            <p className="text-right text-lg font-light">Latest topics</p>
            {displayTopics.map((topic, index) => (
              <div
                key={topic?.id || index}
                className={`rounded-lg md:rounded-xl px-2 md:px-4 py-2 my-2 last:mb-0 text-lg md:text-xl leading-tight font-bold ${
                  topic ? "odd:bg-white/20" : ""
                }`}
              >
                {topic ? (
                  <p className=" line-clamp-2 md:line-clamp-2 lg:line-clamp-3">
                    <span className="font-light text-base md:text-lg inline-block align-middle font-mono">
                      {timeLabel(topic.timestamp)}:&nbsp;
                    </span>
                    {topic.title}
                  </p>
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
            {showEnglishText && (
              <p
                className={
                  "text-xl md:text-2xl lg:text-4xl line-clamp-2 md:line-clamp-3 lg:line-clamp-4 font-bold " +
                  (showTranslatedText
                    ? "line-clamp-1 md:line-clamp-1 mb-2 md:mb-3 lg:mb-5"
                    : "")
                }
              >
                {webSockets.transcriptText}
              </p>
            )}
            {showTranslatedText && (
              <p
                className={
                  showEnglishText
                    ? "text-lg md:text-xl lg:text-2xl line-clamp-1 lg:line-clamp-4"
                    : "line-clamp-2 md:line-clamp-3 lg:line-clamp-4 text-xl md:text-2xl lg:text-4xl font-bold"
                }
              >
                {webSockets.translationText}
              </p>
            )}
          </div>
        </section>
      </div>

      <footer className="flex justify-between items-center pt-2 border-t ">
        <Image
          src="/All-In_Logotype_Blanc_2L.png"
          width={40}
          height={40}
          className="h-12 lg:h-16 ml-[-3px] w-auto"
          alt="All In Logo"
        />
        <div className="flex items-end">
          <Image
            src="/Flag_of_Quebec.svg"
            width={40}
            height={40}
            className="h-8 lg:auto w-auto mr-1 mb-3 opacity-80 ml-2 lg:relative lg:bottom-1.5"
            alt="Flag of Quebec"
          />
          <Image
            src="/canada-flag.svg"
            width={30}
            height={30}
            className="h-8 lg:auto w-auto mr-1 mb-3 opacity-80 ml-2 lg:relative lg:bottom-1.5"
            alt="Canada flag"
          />
          <Image
            src="/Monadical-BW-with-name.svg"
            width={30}
            height={30}
            className="h-12 lg:h-16 mr-[-4px] w-auto"
            alt="Monadical Logo"
          />
        </div>
      </footer>
    </div>
  );
};

export default TranscriptCreate;

"use client";
import React, { useEffect, useState } from "react";
import Recorder from "../recorder";
import { TopicList } from "../topicList";
import useWebRTC from "../useWebRTC";
import useTranscript from "../useTranscript";
import { useWebSockets } from "../useWebSockets";
import useAudioDevice from "../useAudioDevice";
import "../../styles/button.css";
import { Topic } from "../webSocketTypes";
import getApi from "../../lib/getApi";
import LiveTrancription from "../liveTranscription";
import DisconnectedIndicator from "../disconnectedIndicator";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGear } from "@fortawesome/free-solid-svg-icons";

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
  const [hasRecorded, setHasRecorded] = useState(false);

  return (
    <>
      {permissionOk ? (
        <>
          <Recorder
            setStream={setStream}
            onStop={() => {
              webRTC?.peer?.send(JSON.stringify({ cmd: "STOP" }));
              setStream(null);
              setHasRecorded(true);
            }}
            topics={webSockets.topics}
            getAudioStream={getAudioStream}
            useActiveTopic={useActiveTopic}
            isPastMeeting={false}
            audioDevices={audioDevices}
          />

          <div className="grid grid-cols-1 lg:grid-cols-2 grid-rows-mobile-inner lg:grid-rows-1 gap-2 lg:gap-4 h-full">
            <TopicList
              topics={webSockets.topics}
              useActiveTopic={useActiveTopic}
            />
            <section className="w-full h-full bg-blue-400/20 rounded-lg md:rounded-xl px-2 md:px-4 flex flex-col justify-center align-center">
              {!hasRecorded ? (
                <div className="py-2 h-auto">
                  <LiveTrancription text={webSockets.transcriptText} />
                </div>
              ) : (
                <div className="flex flex-col justify-center align center text-center">
                  <div className="p-4">
                    <FontAwesomeIcon
                      icon={faGear}
                      className="animate-spin-slow h-20 w-20"
                    />
                  </div>
                  <p>Your final summary is being processed.</p>
                </div>
              )}
            </section>
          </div>

          {disconnected && <DisconnectedIndicator />}
        </>
      ) : (
        <>
          <div></div>
          <section className="flex flex-col w-full h-full items-center justify-evenly p-4 md:px-6 md:py-8">
            <div className="flex flex-col max-w-2xl items-center justify-center">
              <h1 className="text-2xl font-bold mb-2">Reflector</h1>
              <p className="self-start">
                Meet Monadical's own Reflector, your audio ally for hassle-free
                insights.
              </p>
              <p className="mb-4 md:text-justify">
                With real-time transcriptions, translations, and summaries,
                Reflector captures and categorizes the details of your meetings
                and events, all while keeping your data locked down tight on
                your own infrastructure. Forget the scribbled notes, endless
                recordings, or third-party apps. Discover Reflector, a powerful
                new way to elevate knowledge management and accessibility for
                all.
              </p>
            </div>
            <div>
              <div className="flex flex-col max-w-2xl items-center justify-center">
                <h2 className="text-2xl font-bold  mb-2">Audio Permissions</h2>
                {loading ? (
                  <p className="text-gray-500 text-center">
                    Checking permission...
                  </p>
                ) : (
                  <>
                    <p className="text-gray-500 text-center">
                      Reflector needs access to your microphone to work.
                      <br />
                      {permissionDenied
                        ? "Please reset microphone permissions to continue."
                        : "Please grant permission to continue."}
                    </p>
                    <button
                      className="mt-4 bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white font-bold py-2 px-4 rounded m-auto"
                      onClick={requestPermission}
                      disabled={permissionDenied}
                    >
                      {permissionDenied ? "Access denied" : "Grant Permission"}
                    </button>
                  </>
                )}
              </div>
            </div>
          </section>
        </>
      )}
    </>
  );
};

export default TranscriptCreate;

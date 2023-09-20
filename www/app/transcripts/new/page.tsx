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
import AudioInputsDropdown from "../audioInputsDropdown";
import LiveTrancription from "../liveTranscription";
import DisconnectedIndicator from "../disconnectedIndicator";

const TranscriptCreate = () => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [disconnected, setDisconnected] = useState<boolean>(false);
  const useActiveTopic = useState<Topic | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [recordStarted, setRecordStarted] = useState(false);

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

  const getCurrentStream = async () => {
    setRecordStarted(true);
    return deviceId ? await getAudioStream(deviceId) : null;
  };

  useEffect(() => {
    if (audioDevices.length > 0) {
      setDeviceId[audioDevices[0].value];
    }
  }, [audioDevices]);

  return (
    <>
      {permissionOk ? (
        <>
          <Recorder
            setStream={setStream}
            onStop={() => {
              webRTC?.peer?.send(JSON.stringify({ cmd: "STOP" }));
              setStream(null);
            }}
            topics={webSockets.topics}
            getAudioStream={getCurrentStream}
            useActiveTopic={useActiveTopic}
            isPastMeeting={false}
          />
          <div className="grid grid-cols-1 lg:grid-cols-2 grid-rows-2 lg:grid-rows-1 gap-2 lg:gap-4 h-full">
            <TopicList
              topics={webSockets.topics}
              useActiveTopic={useActiveTopic}
            />
            <div className="h-full flex flex-col">
              <section className="mb-2">
                <AudioInputsDropdown
                  setDeviceId={setDeviceId}
                  audioDevices={audioDevices}
                  disabled={recordStarted}
                />
              </section>
              <section className="w-full h-full bg-blue-400/20 rounded-lg md:rounded-xl px-2 md:px-4 flex flex-col justify-center align-center">
                <div className="py-2 h-auto">
                  <LiveTrancription text={webSockets.transcriptText} />
                </div>
              </section>
            </div>

            {disconnected && <DisconnectedIndicator />}
          </div>
        </>
      ) : (
        <>
          <div className="flex flex-col w-full items-center justify-center px-6 py-8 mt-8 rounded-xl">
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
                  className="mt-4 bg-blue-400 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded m-auto"
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
    </>
  );
};

export default TranscriptCreate;

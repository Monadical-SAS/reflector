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
import About from "../../(aboutAndPrivacy)/about";
import Privacy from "../../(aboutAndPrivacy)/privacy";

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
  const [transcriptStarted, setTranscriptStarted] = useState(false);

  useEffect(() => {
    if (!transcriptStarted && webSockets.transcriptText.length !== 0)
      setTranscriptStarted(true);
  }, [webSockets.transcriptText]);

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
              autoscroll={true}
            />

            <section
              className={`w-full h-full bg-blue-400/20 rounded-lg md:rounded-xl p-2 md:px-4`}
            >
              {!hasRecorded ? (
                <>
                  {transcriptStarted && (
                    <h2 className="md:text-lg font-bold">Transcription</h2>
                  )}
                  <div className="flex flex-col justify-center align center text-center h-full">
                    <div className="py-2 h-auto">
                      {!transcriptStarted ? (
                        <div className="text-center text-gray-500">
                          The conversation transcript will appear here shortly
                          after you start recording.
                        </div>
                      ) : (
                        <LiveTrancription text={webSockets.transcriptText} />
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex flex-col justify-center align center text-center h-full text-gray-500">
                  <div className="p-2 md:p-4">
                    <FontAwesomeIcon
                      icon={faGear}
                      className="animate-spin-slow h-14 w-14 md:h-20 md:w-20"
                    />
                  </div>
                  <p>
                    We are generating the final summary for you. This may take a
                    couple of minutes. Please do not navigate away from the page
                    during this time.
                  </p>
                </div>
              )}
            </section>
          </div>

          {disconnected && <DisconnectedIndicator />}
        </>
      ) : (
        <>
          <div></div>
          <div className="max-h-full overflow-auto">
            <section className="flex flex-col w-full h-full items-center justify-evenly p-4 md:px-6 md:py-8">
              <div>
                <div className="flex flex-col max-w-xl items-center justify-center">
                  <h1 className="text-2xl font-bold mb-2">
                    Welcome to reflector.media
                  </h1>
                  <p>
                    Reflector is a transcription and summarization pipeline that
                    transforms audio into knowledge. The output is meeting
                    minutes and topic summaries enabling topic-specific analyses
                    stored in your systems of record. This is accomplished on
                    your infrastructure – without 3rd parties – keeping your
                    data private, secure, and organized.
                  </p>
                  <About buttonText="Learn more" />
                  <h2 className="text-2xl font-bold mt-4 mb-2">
                    Audio Permissions
                  </h2>
                  {loading ? (
                    <p className="text-center">Checking permission...</p>
                  ) : (
                    <>
                      <p className="text-center">
                        In order to use Reflector, we kindly request permission
                        to access your microphone during meetings and events.
                        <br />
                        <Privacy buttonText="Privacy policy" />
                        <br />
                        {permissionDenied
                          ? "Permission to use your microphone was denied, please change the permission setting in your browser and refresh this page."
                          : "Please grant permission to continue."}
                      </p>
                      <button
                        className="mt-4 bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white font-bold py-2 px-4 rounded m-auto"
                        onClick={requestPermission}
                        disabled={permissionDenied}
                      >
                        {permissionDenied
                          ? "Access denied"
                          : "Grant Permission"}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </section>
          </div>
        </>
      )}
    </>
  );
};

export default TranscriptCreate;

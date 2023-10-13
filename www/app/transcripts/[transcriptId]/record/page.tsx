"use client";
import React, { useEffect, useState } from "react";
import Recorder from "../../recorder";
import { TopicList } from "../../topicList";
import useWebRTC from "../../useWebRTC";
import useTranscript from "../../useTranscript";
import { useWebSockets } from "../../useWebSockets";
import useAudioDevice from "../../useAudioDevice";
import "../../../styles/button.css";
import { Topic } from "../../webSocketTypes";
import getApi from "../../../lib/getApi";
import LiveTrancription from "../../liveTranscription";
import DisconnectedIndicator from "../../disconnectedIndicator";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGear } from "@fortawesome/free-solid-svg-icons";
import { lockWakeState, releaseWakeState } from "../../../lib/wakeLock";

type TranscriptDetails = {
  params: {
    transcriptId: string;
  };
};

const TranscriptRecord = (details: TranscriptDetails) => {
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

  const transcript = useTranscript(details.params.transcriptId);
  const api = getApi();
  const webRTC = useWebRTC(stream, details.params.transcriptId, api);
  const webSockets = useWebSockets(details.params.transcriptId);

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

  useEffect(() => {
    if (transcript?.response?.longSummary) {
      const newUrl = `/transcripts/${transcript.response.id}`;
      // Shallow redirection does not work on NextJS 13
      // https://github.com/vercel/next.js/discussions/48110
      // https://github.com/vercel/next.js/discussions/49540
      // router.push(newUrl, undefined, { shallow: true });
      history.replaceState({}, "", newUrl);
    }
  });

  useEffect(() => {
    lockWakeState();
    return () => {
      releaseWakeState();
    };
  }, []);

  return (
    <>
      <Recorder
        setStream={setStream}
        onStop={() => {
          setStream(null);
          setHasRecorded(true);
          webRTC?.send(JSON.stringify({ cmd: "STOP" }));
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
                      The conversation transcript will appear here shortly after
                      you start recording.
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
  );
};

export default TranscriptRecord;

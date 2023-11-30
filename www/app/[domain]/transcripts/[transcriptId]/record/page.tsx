"use client";
import React, { useEffect, useState } from "react";
import Recorder from "../../recorder";
import { TopicList } from "../../topicList";
import useWebRTC from "../../useWebRTC";
import useTranscript from "../../useTranscript";
import { useWebSockets } from "../../useWebSockets";
import useAudioDevice from "../../useAudioDevice";
import "../../../../styles/button.css";
import { Topic } from "../../webSocketTypes";
import LiveTrancription from "../../liveTranscription";
import DisconnectedIndicator from "../../disconnectedIndicator";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGear } from "@fortawesome/free-solid-svg-icons";
import { lockWakeState, releaseWakeState } from "../../../../lib/wakeLock";
import { useRouter } from "next/navigation";
import Player from "../../player";
import useMp3 from "../../useMp3";
import WaveformLoading from "../../waveformLoading";

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
  const webRTC = useWebRTC(stream, details.params.transcriptId);
  const webSockets = useWebSockets(details.params.transcriptId);

  const { audioDevices, getAudioStream } = useAudioDevice();

  const [recordedTime, setRecordedTime] = useState(0);
  const [startTime, setStartTime] = useState(0);
  const [transcriptStarted, setTranscriptStarted] = useState(false);
  let mp3 = useMp3(details.params.transcriptId, true);

  const router = useRouter();

  useEffect(() => {
    if (!transcriptStarted && webSockets.transcriptText.length !== 0)
      setTranscriptStarted(true);
  }, [webSockets.transcriptText]);

  useEffect(() => {
    const statusToRedirect = ["ended", "error"];

    //TODO if has no topic and is error, get back to new
    if (
      statusToRedirect.includes(transcript.response?.status) ||
      statusToRedirect.includes(webSockets.status.value)
    ) {
      const newUrl = "/transcripts/" + details.params.transcriptId;
      // Shallow redirection does not work on NextJS 13
      // https://github.com/vercel/next.js/discussions/48110
      // https://github.com/vercel/next.js/discussions/49540
      router.replace(newUrl);
      // history.replaceState({}, "", newUrl);
    } // history.replaceState({}, "", newUrl);
  }, [webSockets.status.value, transcript.response?.status]);

  useEffect(() => {
    if (webSockets.duration) {
      mp3.getNow();
    }
  }, [webSockets.duration]);

  useEffect(() => {
    lockWakeState();
    return () => {
      releaseWakeState();
    };
  }, []);

  return (
    <>
      {webSockets.waveform && webSockets.duration && mp3?.media ? (
        <Player
          topics={webSockets.topics || []}
          useActiveTopic={useActiveTopic}
          waveform={webSockets.waveform}
          media={mp3.media}
          mediaDuration={webSockets.duration}
        />
      ) : recordedTime ? (
        <WaveformLoading />
      ) : (
        <Recorder
          setStream={setStream}
          onStop={() => {
            setStream(null);
            setRecordedTime(Date.now() - startTime);
            webRTC?.send(JSON.stringify({ cmd: "STOP" }));
          }}
          onRecord={() => {
            setStartTime(Date.now());
          }}
          getAudioStream={getAudioStream}
          audioDevices={audioDevices}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 grid-rows-mobile-inner lg:grid-rows-1 gap-2 lg:gap-4 h-full">
        <TopicList
          topics={webSockets.topics}
          useActiveTopic={useActiveTopic}
          autoscroll={true}
        />

        <section
          className={`w-full h-full bg-blue-400/20 rounded-lg md:rounded-xl p-2 md:px-4`}
        >
          {!recordedTime ? (
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
                    <LiveTrancription
                      text={webSockets.transcriptText}
                      translateText={webSockets.translateText}
                    />
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
              {/* NTH If login required remove last sentence */}
            </div>
          )}
        </section>
      </div>

      {disconnected && <DisconnectedIndicator />}
    </>
  );
};

export default TranscriptRecord;

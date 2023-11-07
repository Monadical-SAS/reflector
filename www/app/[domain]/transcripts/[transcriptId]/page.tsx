"use client";
import Modal from "../modal";
import useTranscript from "../useTranscript";
import useTopics from "../useTopics";
import useWaveform from "../useWaveform";
import useMp3 from "../useMp3";
import { TopicList } from "../topicList";
import Recorder from "../recorder";
import { Topic } from "../webSocketTypes";
import React, { useState } from "react";
import "../../../styles/button.css";
import FinalSummary from "../finalSummary";
import ShareLink from "../shareLink";
import QRCode from "react-qr-code";
import TranscriptTitle from "../transcriptTitle";

type TranscriptDetails = {
  params: {
    transcriptId: string;
  };
};

const protectedPath = true;

export default function TranscriptDetails(details: TranscriptDetails) {
  const transcriptId = details.params.transcriptId;

  const transcript = useTranscript(protectedPath, transcriptId);
  const topics = useTopics(protectedPath, transcriptId);
  const waveform = useWaveform(protectedPath, transcriptId);
  const useActiveTopic = useState<Topic | null>(null);
  const mp3 = useMp3(protectedPath, transcriptId);

  if (transcript?.error /** || topics?.error || waveform?.error **/) {
    return (
      <Modal
        title="Transcription Not Found"
        text="A trascription with this ID does not exist."
      />
    );
  }

  const fullTranscript =
    topics.topics
      ?.map((topic) => topic.transcript)
      .join("\n\n")
      .replace(/ +/g, " ")
      .trim() || "";

  return (
    <>
      {!transcriptId || transcript?.loading || topics?.loading ? (
        <Modal title="Loading" text={"Loading transcript..."} />
      ) : (
        <>
          <div className="flex flex-col">
            {transcript?.response?.title && (
              <TranscriptTitle
                protectedPath={protectedPath}
                title={transcript.response.title}
                transcriptId={transcript.response.id}
              />
            )}
            {waveform?.loading === false && (
              <Recorder
                topics={topics?.topics || []}
                useActiveTopic={useActiveTopic}
                waveform={waveform?.waveform}
                isPastMeeting={true}
                transcriptId={transcript?.response?.id}
                mp3Blob={mp3.blob}
              />
            )}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 grid-rows-2 lg:grid-rows-1 gap-2 lg:gap-4 h-full">
            <TopicList
              topics={topics?.topics || []}
              useActiveTopic={useActiveTopic}
              autoscroll={false}
            />
            <div className="w-full h-full grid grid-rows-layout-one grid-cols-1 gap-2 lg:gap-4">
              <section className=" bg-blue-400/20 rounded-lg md:rounded-xl p-2 md:px-4 h-full">
                {transcript?.response?.longSummary && (
                  <FinalSummary
                    protectedPath={protectedPath}
                    fullTranscript={fullTranscript}
                    summary={transcript?.response?.longSummary}
                    transcriptId={transcript?.response?.id}
                  />
                )}
              </section>

              <section className="flex items-center">
                <div className="mr-4 hidden md:block h-auto">
                  <QRCode
                    value={`${location.origin}/transcripts/${details.params.transcriptId}`}
                    level="L"
                    size={98}
                  />
                </div>
                <div className="flex-grow max-w-full">
                  <ShareLink
                    protectedPath={protectedPath}
                    transcriptId={transcript?.response?.id}
                    userId={transcript?.response?.userId}
                    shareMode={transcript?.response?.shareMode}
                  />
                </div>
              </section>
            </div>
          </div>
        </>
      )}
    </>
  );
}

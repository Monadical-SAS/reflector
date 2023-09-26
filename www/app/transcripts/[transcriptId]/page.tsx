"use client";
import Modal from "../modal";
import getApi from "../../lib/getApi";
import useTranscript from "../useTranscript";
import useTopics from "../useTopics";
import useWaveform from "../useWaveform";
import { TopicList } from "../topicList";
import Recorder from "../recorder";
import { Topic } from "../webSocketTypes";
import React, { useEffect, useState } from "react";
import "../../styles/button.css";
import FinalSummary from "../finalSummary";
import ShareLink from "../shareLink";

type TranscriptDetails = {
  params: {
    transcriptId: string;
  };
};

export default function TranscriptDetails(details: TranscriptDetails) {
  const api = getApi();
  const transcript = useTranscript(null, api, details.params.transcriptId);
  const topics = useTopics(api, details.params.transcriptId);
  const waveform = useWaveform(api, details.params.transcriptId);
  const useActiveTopic = useState<Topic | null>(null);

  if (transcript?.error || topics?.error || waveform?.error) {
    return (
      <Modal
        title="Transcription Not Found"
        text="A trascription with this ID does not exist."
      />
    );
  }

  return (
    <>
      {transcript?.loading === true ||
      waveform?.loading == true ||
      topics?.loading == true ? (
        <Modal title="Loading" text={"Loading transcript..."} />
      ) : (
        <>
          <Recorder
            topics={topics?.topics || []}
            useActiveTopic={useActiveTopic}
            waveform={waveform?.waveform}
            isPastMeeting={true}
            transcriptId={transcript?.response?.id}
          />
          <div className="grid grid-cols-1 lg:grid-cols-2 grid-rows-2 lg:grid-rows-1 gap-2 lg:gap-4 h-full">
            <TopicList
              topics={topics?.topics || []}
              useActiveTopic={useActiveTopic}
              autoscroll={false}
            />
            <div className="w-full h-full grid grid-rows-layout-one gap-2 lg:gap-4">
              <section className=" bg-blue-400/20 rounded-lg md:rounded-xl p-2 md:px-4 h-full">
                {transcript?.response?.longSummary && (
                  <FinalSummary text={transcript?.response?.longSummary} />
                )}
              </section>
              <ShareLink />
            </div>
          </div>
        </>
      )}
    </>
  );
}

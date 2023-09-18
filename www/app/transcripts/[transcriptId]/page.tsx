"use client";
import Modal from "../modal";
import getApi from "../../lib/getApi";
import useTranscript from "../useTranscript";
import useTopics from "../useTopics";
import useWaveform from "../useWaveform";
import { Dashboard } from "../dashboard";
import Recorder from "../recorder";
import { Topic } from "../webSocketTypes";
import React, { useEffect, useState } from "react";
import "../../styles/button.css";

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
      <div className="w-full flex flex-col items-center">
        {transcript?.loading === true ||
        waveform?.loading == true ||
        topics?.loading == true ? (
          <Modal
            title="Loading"
            text={"Loading transcript..." + transcript.loading}
          />
        ) : (
          <>
            <Recorder
              topics={topics?.topics || []}
              useActiveTopic={useActiveTopic}
              waveform={waveform?.waveform}
              isPastMeeting={true}
              transcriptId={transcript?.response?.id}
            />

            <Dashboard
              transcriptionText={""}
              finalSummary={{ summary: transcript?.response?.longSummary }}
              topics={topics?.topics || []}
              disconnected={false}
              useActiveTopic={useActiveTopic}
            />
          </>
        )}
      </div>
    </>
  );
}

"use client";
import { useState } from "react";
import useTranscript from "../../useTranscript";
import TopicHeader from "./topicHeader";
import TopicWords from "./topicWords";

type TranscriptCorrect = {
  params: {
    transcriptId: string;
  };
};

export default function TranscriptCorrect(details: TranscriptCorrect) {
  const transcriptId = details.params.transcriptId;
  const transcript = useTranscript(transcriptId);
  const [currentTopic, setCurrentTopic] = useState("");
  const [selectedTime, setSelectedTime] = useState<{
    start: number;
    end: number;
  }>();

  console.log(selectedTime);
  return (
    <div className="h-full grid grid-cols-2 gap-4">
      <div className="flex flex-col h-full">
        <TopicHeader
          currentTopic={currentTopic}
          setCurrentTopic={setCurrentTopic}
          transcriptId={transcriptId}
        />
        <TopicWords
          setSelectedTime={setSelectedTime}
          currentTopic={currentTopic}
          transcriptId={transcriptId}
        />
      </div>
    </div>
  );
}

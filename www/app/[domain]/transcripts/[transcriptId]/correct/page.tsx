"use client";
import { useEffect, useState } from "react";
import useTranscript from "../../useTranscript";
import TopicHeader from "./topicHeader";
import TopicWords from "./topicWords";
import TopicPlayer from "./topicPlayer";

type TranscriptCorrect = {
  params: {
    transcriptId: string;
  };
};

type TimeSlice = {
  start: number;
  end: number;
};

export default function TranscriptCorrect(details: TranscriptCorrect) {
  const transcriptId = details.params.transcriptId;
  const transcript = useTranscript(transcriptId);
  const [currentTopic, setCurrentTopic] = useState("");
  const [selectedTime, setSelectedTime] = useState<TimeSlice>();
  const [topicTime, setTopicTime] = useState<TimeSlice>();

  // TODO BE
  // Get one topic with words
  // -> fix useTopicWithWords.ts
  // Add start and end time of each topic in the topic list
  // -> use full current topic instead of topicId here
  // -> remove time calculation and setting from TopicHeader
  // -> pass in topicTime to player directly

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
          setTopicTime={setTopicTime}
        />
      </div>
      <div>
        <TopicPlayer
          transcriptId={transcriptId}
          selectedTime={selectedTime}
          topicTime={topicTime}
        />
      </div>
    </div>
  );
}

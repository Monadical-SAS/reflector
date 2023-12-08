"use client";
import { useEffect, useState } from "react";
import useTranscript from "../../useTranscript";
import TopicHeader from "./topicHeader";
import TopicWords from "./topicWords";
import TopicPlayer from "./topicPlayer";
import getApi from "../../../../lib/getApi";
import useParticipants from "../../useParticipants";

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
  const api = getApi();
  const participants = useParticipants(transcriptId);
  const stateSelectedSpeaker = useState<number>();

  // TODO BE
  // Get one topic with words
  // -> fix useTopicWithWords.ts
  // Add start and end time of each topic in the topic list
  // -> use full current topic instead of topicId here
  // -> remove time calculation and setting from TopicHeader
  // -> pass in topicTime to player directly
  // Should we have participants by default, one for each speaker ?

  const createParticipant = () => {
    api?.v1TranscriptAddParticipant({
      createParticipant: { name: "Samantha" },
      transcriptId,
    });
  };

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
          stateSelectedSpeaker={stateSelectedSpeaker}
          participants={participants}
        />
      </div>
      <div>
        <TopicPlayer
          transcriptId={transcriptId}
          selectedTime={selectedTime}
          topicTime={topicTime}
        />
        <button onClick={createParticipant}>Create</button>
      </div>
    </div>
  );
}

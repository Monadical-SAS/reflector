"use client";
import { useState } from "react";
import TopicHeader from "./topicHeader";
import TopicWords from "./topicWords";
import TopicPlayer from "./topicPlayer";
import useParticipants from "../../useParticipants";
import useTopicWithWords from "../../useTopicWithWords";
import ParticipantList from "./participantList";
import { GetTranscriptTopic } from "../../../../api";
import { SelectedText, selectedTextIsTimeSlice } from "./types";

export type TranscriptCorrect = {
  params: {
    transcriptId: string;
  };
};

export default function TranscriptCorrect({
  params: { transcriptId },
}: TranscriptCorrect) {
  const stateCurrentTopic = useState<GetTranscriptTopic>();
  const [currentTopic, _sct] = stateCurrentTopic;
  const stateSelectedText = useState<SelectedText>();
  const [selectedText, _sst] = stateSelectedText;
  const topicWithWords = useTopicWithWords(currentTopic?.id, transcriptId);
  const participants = useParticipants(transcriptId);

  return (
    <div className="h-full grid grid-cols-2 gap-4">
      <div className="flex flex-col h-full">
        <TopicHeader
          stateCurrentTopic={stateCurrentTopic}
          transcriptId={transcriptId}
          topicWithWordsLoading={topicWithWords.loading}
        />
        <TopicWords
          stateSelectedText={stateSelectedText}
          participants={participants}
          topicWithWords={topicWithWords}
        />
      </div>
      <div className="flex flex-col justify-stretch">
        {currentTopic ? (
          <TopicPlayer
            transcriptId={transcriptId}
            selectedTime={
              selectedTextIsTimeSlice(selectedText) ? selectedText : undefined
            }
            topicTime={{
              start: currentTopic?.timestamp,
              end: currentTopic?.timestamp + currentTopic?.duration,
            }}
          />
        ) : (
          <div></div>
        )}
        {participants.response && (
          <ParticipantList
            {...{
              transcriptId,
              participants,
              topicWithWords,
              stateSelectedText,
            }}
          />
        )}
      </div>
    </div>
  );
}

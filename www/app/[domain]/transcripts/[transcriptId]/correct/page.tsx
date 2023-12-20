"use client";
import { useEffect, useState } from "react";
import TopicHeader from "./topicHeader";
import TopicWords from "./topicWords";
import TopicPlayer from "./topicPlayer";
import useParticipants from "../../useParticipants";
import useTopicWithWords from "../../useTopicWithWords";
import ParticipantList from "./participantList";
import { GetTranscriptTopic } from "../../../../api";
import { SelectedText, selectedTextIsTimeSlice } from "./types";
import getApi from "../../../../lib/getApi";
import useTranscript from "../../useTranscript";
import { useError } from "../../../../(errors)/errorContext";
import { useRouter } from "next/navigation";

export type TranscriptCorrect = {
  params: {
    transcriptId: string;
  };
};

export default function TranscriptCorrect({
  params: { transcriptId },
}: TranscriptCorrect) {
  const api = getApi();
  const transcript = useTranscript(transcriptId);
  const stateCurrentTopic = useState<GetTranscriptTopic>();
  const [currentTopic, _sct] = stateCurrentTopic;
  const stateSelectedText = useState<SelectedText>();
  const [selectedText, _sst] = stateSelectedText;
  const topicWithWords = useTopicWithWords(currentTopic?.id, transcriptId);
  const participants = useParticipants(transcriptId);
  const { setError } = useError();
  const router = useRouter();

  const markAsDone = () => {
    if (transcript.response && !transcript.response.reviewed) {
      api
        ?.v1TranscriptUpdate({
          transcriptId,
          updateTranscript: { reviewed: true },
        })
        .then(() => {
          router.push(`/transcripts/${transcriptId}`);
        })
        .catch((e) => {
          setError(e, "Error marking as done");
        });
    }
  };

  return (
    <div className="h-full grid grid-cols-2 gap-4">
      <div className="flex flex-col h-full ">
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
          <div className="h-full flex flex-col justify-between">
            <ParticipantList
              {...{
                transcriptId,
                participants,
                topicWithWords,
                stateSelectedText,
              }}
            />
            {!transcript.response?.reviewed && (
              <div className="flex flex-row justify-end">
                <button
                  className="p-2 px-4 rounded bg-green-400"
                  onClick={markAsDone}
                >
                  Done
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

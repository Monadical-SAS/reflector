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
import getApi from "../../../../lib/getApi";
import useTranscript from "../../useTranscript";
import { useError } from "../../../../(errors)/errorContext";
import { useRouter } from "next/navigation";
import { Box, Grid } from "@chakra-ui/react";

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
    <Grid
      templateRows="auto minmax(0, 1fr)"
      h="100%"
      maxW={{ lg: "container.lg" }}
      mx="auto"
      minW={{ base: "100%", lg: "container.lg" }}
    >
      <Box display="flex" flexDir="column" minW="100%" mb={{ base: 4, lg: 10 }}>
        <TopicHeader
          minW="100%"
          stateCurrentTopic={stateCurrentTopic}
          transcriptId={transcriptId}
          topicWithWordsLoading={topicWithWords.loading}
        />

        <TopicPlayer
          transcriptId={transcriptId}
          selectedTime={
            selectedTextIsTimeSlice(selectedText) ? selectedText : undefined
          }
          topicTime={
            currentTopic
              ? {
                  start: currentTopic?.timestamp,
                  end: currentTopic?.timestamp + currentTopic?.duration,
                }
              : undefined
          }
        />
      </Box>
      <Grid
        templateColumns={{
          base: "minmax(0, 1fr)",
          md: "4fr 3fr",
          lg: "2fr 1fr",
        }}
        templateRows={{
          base: "repeat(2, minmax(0, 1fr)) auto",
          md: "minmax(0, 1fr)",
        }}
        gap={{ base: "2", md: "4", lg: "4" }}
        h="100%"
        maxH="100%"
        w="100%"
      >
        <TopicWords
          stateSelectedText={stateSelectedText}
          participants={participants}
          topicWithWords={topicWithWords}
          mb={{ md: "-3rem" }}
        />
        <ParticipantList
          {...{
            transcriptId,
            participants,
            topicWithWords,
            stateSelectedText,
          }}
        />
      </Grid>
      {transcript.response && !transcript.response?.reviewed && (
        <div className="flex flex-row justify-end">
          <button
            className="p-2 px-4 rounded bg-green-400"
            onClick={markAsDone}
          >
            Done
          </button>
        </div>
      )}
    </Grid>
  );
}

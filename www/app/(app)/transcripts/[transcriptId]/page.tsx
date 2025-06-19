"use client";
import Modal from "../modal";
import useTranscript from "../useTranscript";
import useTopics from "../useTopics";
import useWaveform from "../useWaveform";
import useMp3 from "../useMp3";
import { TopicList } from "../topicList";
import { Topic } from "../webSocketTypes";
import React, { useEffect, useState } from "react";
import "../../../styles/button.css";
import FinalSummary from "./finalSummary";
import TranscriptTitle from "../transcriptTitle";
import Player from "../player";
import { useRouter } from "next/navigation";
import { Flex, Grid, GridItem, Skeleton, Text } from "@chakra-ui/react";

type TranscriptDetails = {
  params: {
    transcriptId: string;
  };
};

export default function TranscriptDetails(details: TranscriptDetails) {
  const transcriptId = details.params.transcriptId;
  const router = useRouter();
  const statusToRedirect = ["idle", "recording", "processing"];

  const transcript = useTranscript(transcriptId);
  const transcriptStatus = transcript.response?.status;
  const waiting = statusToRedirect.includes(transcriptStatus || "");

  const topics = useTopics(transcriptId);
  const waveform = useWaveform(transcriptId, waiting);
  const useActiveTopic = useState<Topic | null>(null);
  const mp3 = useMp3(transcriptId, waiting);

  useEffect(() => {
    if (waiting) {
      const newUrl = "/transcripts/" + details.params.transcriptId + "/record";
      // Shallow redirection does not work on NextJS 13
      // https://github.com/vercel/next.js/discussions/48110
      // https://github.com/vercel/next.js/discussions/49540
      router.replace(newUrl);
      // history.replaceState({}, "", newUrl);
    }
  }, [waiting]);

  if (transcript.error || topics?.error) {
    return (
      <Modal
        title="Transcription Not Found"
        text="A trascription with this ID does not exist."
      />
    );
  }

  if (transcript?.loading || topics?.loading) {
    return <Modal title="Loading" text={"Loading transcript..."} />;
  }

  if (mp3.error) {
    return (
      <Modal
        title="Transcription error"
        text={`There was an error loading the recording. Error: ${mp3.error}`}
      />
    );
  }



  return (
    <>
      <Grid
        templateColumns="1fr"
        templateRows="auto minmax(0, 1fr)"
        gap={4}
        mt={4}
        mb={4}
      >
        {waveform.waveform && mp3.media && !mp3.audioDeleted && topics.topics ? (
          <Player
            topics={topics?.topics}
            useActiveTopic={useActiveTopic}
            waveform={waveform.waveform}
            media={mp3.media}
            mediaDuration={transcript.response.duration}
          />
        ) : waveform.error ? (
          <div>"error loading this recording"</div>
        ) : mp3.audioDeleted ? (
          <div>Audio was deleted</div>
        ) : (
          <Skeleton h={14} />
        )}
        <Grid
          templateColumns={{ base: "minmax(0, 1fr)", md: "repeat(2, 1fr)" }}
          templateRows={{
            base: "auto minmax(0, 1fr) minmax(0, 1fr)",
            md: "auto minmax(0, 1fr)",
          }}
          gap={2}
          padding={4}
          paddingBottom={0}
          background="gray.bg"
          border={"2px solid"}
          borderColor={"gray.bg"}
          borderRadius={8}
        >
          <GridItem
            display="flex"
            flexDir="row"
            alignItems={"center"}
            colSpan={{ base: 1, md: 2 }}
          >
            <TranscriptTitle
              title={transcript.response.title || "Unnamed Transcript"}
              transcriptId={transcriptId}
              onUpdate={(newTitle) => {
                transcript.reload();
              }}
            />
          </GridItem>
          <TopicList
            topics={topics.topics || []}
            useActiveTopic={useActiveTopic}
            autoscroll={false}
            transcriptId={transcriptId}
            status={transcript.response?.status}
            currentTranscriptText=""
          />
          {transcript.response && topics.topics ? (
            <>
              <FinalSummary
                transcriptResponse={transcript.response}
                topicsResponse={topics.topics}
                onUpdate={(newSummary) => {
                  transcript.reload();
                }}
              />
            </>
          ) : (
            <Flex justify={"center"} alignItems={"center"} h={"100%"}>
              <div className="flex flex-col h-full justify-center content-center">
                {transcript.response.status == "processing" ? (
                  <Text>Loading Transcript</Text>
                ) : (
                  <Text>
                    There was an error generating the final summary, please come
                    back later
                  </Text>
                )}
              </div>
            </Flex>
          )}
        </Grid>
      </Grid>
    </>
  );
}

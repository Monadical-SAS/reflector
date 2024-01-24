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

  const transcript = useTranscript(transcriptId);
  const topics = useTopics(transcriptId);
  const waveform = useWaveform(transcriptId);
  const useActiveTopic = useState<Topic | null>(null);
  const mp3 = useMp3(transcriptId);

  useEffect(() => {
    const statusToRedirect = ["idle", "recording", "processing"];
    if (statusToRedirect.includes(transcript.response?.status || "")) {
      const newUrl = "/transcripts/" + details.params.transcriptId + "/record";
      // Shallow redirection does not work on NextJS 13
      // https://github.com/vercel/next.js/discussions/48110
      // https://github.com/vercel/next.js/discussions/49540
      router.replace(newUrl);
      // history.replaceState({}, "", newUrl);
    }
  }, [transcript.response?.status]);

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

  return (
    <>
      <Grid
        templateColumns="1fr"
        templateRows="minmax(0, 1fr) auto"
        gap={4}
        mb={4}
      >
        <Grid
          templateColumns="repeat(2, 1fr)"
          templateRows="auto minmax(0, 1fr)"
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
            colSpan={2}
          >
            <TranscriptTitle
              title={transcript.response.title || "Unamed Transcript"}
              transcriptId={transcriptId}
            />
          </GridItem>
          <TopicList
            topics={topics.topics || []}
            useActiveTopic={useActiveTopic}
            autoscroll={false}
            transcriptId={transcriptId}
          />
          {transcript.response && topics.topics ? (
            <>
              <FinalSummary
                transcriptResponse={transcript.response}
                topicsResponse={topics.topics}
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
        {waveform.waveform && mp3.media && topics.topics ? (
          <Player
            topics={topics?.topics}
            useActiveTopic={useActiveTopic}
            waveform={waveform.waveform}
            media={mp3.media}
            mediaDuration={transcript.response.duration}
          />
        ) : waveform.error ? (
          <div>"error loading this recording"</div>
        ) : (
          <Skeleton h={14} />
        )}
      </Grid>
    </>
  );
}

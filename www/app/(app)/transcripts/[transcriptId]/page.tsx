"use client";
import Modal from "../modal";
import useTopics from "../useTopics";
import useWaveform from "../useWaveform";
import useMp3 from "../useMp3";
import { TopicList } from "./_components/TopicList";
import { Topic } from "../webSocketTypes";
import React, { useEffect, useState, use } from "react";
import FinalSummary from "./finalSummary";
import TranscriptTitle from "../transcriptTitle";
import Player from "../player";
import { useWebSockets } from "../useWebSockets";
import { useRouter } from "next/navigation";
import {
  Box,
  Flex,
  Grid,
  GridItem,
  Skeleton,
  Text,
  Spinner,
} from "@chakra-ui/react";
import { useTranscriptGet } from "../../../lib/apiHooks";
import { TranscriptStatus } from "../../../lib/transcript";

type TranscriptDetails = {
  params: Promise<{
    transcriptId: string;
  }>;
};

export default function TranscriptDetails(details: TranscriptDetails) {
  const params = use(details.params);
  const transcriptId = params.transcriptId;
  const router = useRouter();
  const statusToRedirect = [
    "idle",
    "recording",
    "processing",
    "uploaded",
  ] satisfies TranscriptStatus[] as TranscriptStatus[];

  const transcript = useTranscriptGet(transcriptId);
  const waiting =
    transcript.data && statusToRedirect.includes(transcript.data.status);

  const mp3 = useMp3(transcriptId, waiting);
  const topics = useTopics(transcriptId);
  const waveform = useWaveform(
    transcriptId,
    waiting || mp3.audioDeleted === true,
  );
  useWebSockets(transcriptId);
  const useActiveTopic = useState<Topic | null>(null);
  const [finalSummaryElement, setFinalSummaryElement] =
    useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!waiting || !transcript.data) return;

    const status = transcript.data.status;
    let newUrl: string | null = null;

    if (status === "processing" || status === "uploaded") {
      newUrl = `/transcripts/${params.transcriptId}/processing`;
    } else if (status === "recording") {
      newUrl = `/transcripts/${params.transcriptId}/record`;
    } else if (status === "idle") {
      newUrl =
        transcript.data.source_kind === "file"
          ? `/transcripts/${params.transcriptId}/upload`
          : `/transcripts/${params.transcriptId}/record`;
    }

    if (newUrl) {
      // Shallow redirection does not work on NextJS 13
      // https://github.com/vercel/next.js/discussions/48110
      // https://github.com/vercel/next.js/discussions/49540
      router.replace(newUrl);
    }
  }, [waiting, transcript.data?.status, transcript.data?.source_kind]);

  if (waiting) {
    return (
      <Box>
        <Box
          w="full"
          background="gray.bg"
          border={"2px solid"}
          borderColor={"gray.bg"}
          borderRadius={8}
          p={6}
          minH="100%"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Flex direction="column" align="center" gap={3}>
            <Spinner size="xl" color="blue.500" />
            <Text color="gray.600" textAlign="center">
              Loading transcript...
            </Text>
          </Flex>
        </Box>
      </Box>
    );
  }

  if (transcript.error || topics?.error) {
    return (
      <Modal
        title="Transcription Not Found"
        text="A trascription with this ID does not exist."
      />
    );
  }

  if (transcript?.isLoading || topics?.loading) {
    return <Modal title="Loading" text={"Loading transcript..."} />;
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
        {!mp3.audioDeleted && (
          <>
            {waveform.waveform && mp3.media && topics.topics ? (
              <Player
                topics={topics?.topics}
                useActiveTopic={useActiveTopic}
                waveform={waveform.waveform}
                media={mp3.media}
                mediaDuration={transcript.data?.duration || null}
              />
            ) : !mp3.loading && (waveform.error || mp3.error) ? (
              <Box p={4} bg="red.100" borderRadius="md">
                <Text>
                  Error loading{" "}
                  {[waveform.error && "waveform", mp3.error && "mp3"]
                    .filter(Boolean)
                    .join(" and ")}
                </Text>
              </Box>
            ) : (
              <Skeleton h={14} />
            )}
          </>
        )}
        <Grid
          templateColumns={{ base: "minmax(0, 1fr)", md: "repeat(2, 1fr)" }}
          templateRows={{
            base: "auto minmax(0, 1fr) minmax(0, 1fr)",
            md: "auto minmax(0, 1fr)",
          }}
          gap={4}
          gridRowGap={2}
          padding={4}
          paddingBottom={0}
          background="gray.bg"
          border={"2px solid"}
          borderColor={"gray.bg"}
          borderRadius={8}
        >
          <GridItem colSpan={{ base: 1, md: 2 }}>
            <Flex direction="column" gap={0}>
              <Flex alignItems="center" gap={2}>
                <TranscriptTitle
                  title={transcript.data?.title || "Unnamed Transcript"}
                  transcriptId={transcriptId}
                  onUpdate={() => {
                    transcript.refetch().then(() => {});
                  }}
                  transcript={transcript.data || null}
                  topics={topics.topics}
                  finalSummaryElement={finalSummaryElement}
                />
              </Flex>
              {mp3.audioDeleted && (
                <Text fontSize="xs" color="gray.600" fontStyle="italic">
                  No audio is available because one or more participants didn't
                  consent to keep the audio
                </Text>
              )}
            </Flex>
          </GridItem>
          <TopicList
            topics={topics.topics || []}
            useActiveTopic={useActiveTopic}
            autoscroll={false}
            transcriptId={transcriptId}
            status={transcript.data?.status || null}
            currentTranscriptText=""
          />
          {transcript.data && topics.topics ? (
            <>
              <FinalSummary
                transcript={transcript.data}
                topics={topics.topics}
                onUpdate={() => {
                  transcript.refetch().then(() => {});
                }}
                finalSummaryRef={setFinalSummaryElement}
              />
            </>
          ) : (
            <Flex justify={"center"} alignItems={"center"} h={"100%"}>
              <div className="flex flex-col h-full justify-center content-center">
                {transcript?.data?.status == "processing" ? (
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

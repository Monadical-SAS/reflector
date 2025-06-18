"use client";
import { useEffect, useState } from "react";
import Recorder from "../../recorder";
import { TopicList } from "../../topicList";
import useTranscript from "../../useTranscript";
import { useWebSockets } from "../../useWebSockets";
import "../../../../styles/button.css";
import { Topic } from "../../webSocketTypes";
import { lockWakeState, releaseWakeState } from "../../../../lib/wakeLock";
import { useRouter } from "next/navigation";
import Player from "../../player";
import useMp3 from "../../useMp3";
import WaveformLoading from "../../waveformLoading";
import { Box, Text, Grid, Heading, VStack, Flex } from "@chakra-ui/react";
import LiveTrancription from "../../liveTranscription";

type TranscriptDetails = {
  params: {
    transcriptId: string;
  };
};

const TranscriptRecord = (details: TranscriptDetails) => {
  const transcript = useTranscript(details.params.transcriptId);
  const [transcriptStarted, setTranscriptStarted] = useState(false);
  const useActiveTopic = useState<Topic | null>(null);

  const webSockets = useWebSockets(details.params.transcriptId);

  const mp3 = useMp3(details.params.transcriptId, true);

  const router = useRouter();

  const [status, setStatus] = useState(
    webSockets.status.value || transcript.response?.status || "idle",
  );

  useEffect(() => {
    if (!transcriptStarted && webSockets.transcriptTextLive.length !== 0)
      setTranscriptStarted(true);
  }, [webSockets.transcriptTextLive]);

  useEffect(() => {
    //TODO HANDLE ERROR STATUS BETTER
    const newStatus =
      webSockets.status.value || transcript.response?.status || "idle";
    setStatus(newStatus);
    if (newStatus && (newStatus == "ended" || newStatus == "error")) {
      console.log(newStatus, "redirecting");

      const newUrl = "/transcripts/" + details.params.transcriptId;
      router.replace(newUrl);
    }
  }, [webSockets.status.value, transcript.response?.status]);

  useEffect(() => {
    if (webSockets.waveform && webSockets.waveform) mp3.getNow();
  }, [webSockets.waveform, webSockets.duration]);

  useEffect(() => {
    lockWakeState();
    return () => {
      releaseWakeState();
    };
  }, []);

  return (
    <Grid
      templateColumns="1fr"
      templateRows="auto minmax(0, 1fr) "
      gap={4}
      mt={4}
      mb={4}
    >
      {status == "processing" ? (
        <WaveformLoading />
      ) : (
        // todo: only start recording animation when you get "recorded" status
        <Recorder transcriptId={details.params.transcriptId} status={status} />
      )}
      <VStack
        align={"left"}
        w="full"
        h="full"
        mb={4}
        background="gray.bg"
        border={"2px solid"}
        borderColor={"gray.bg"}
        borderRadius={8}
        p="4"
      >
        <Heading size={"lg"}>
          {status === "processing" ? "Processing meeting" : "Record meeting"}
        </Heading>

        <Flex direction={{ base: "column-reverse", md: "row" }} h={"full"}>
          <Box w={{ md: "50%" }} h={{ base: "80%", md: "full" }}>
            <TopicList
              topics={webSockets.topics}
              useActiveTopic={useActiveTopic}
              autoscroll={true}
              transcriptId={details.params.transcriptId}
              status={status}
              currentTranscriptText={webSockets.accumulatedText}
            />
          </Box>
          <Box w={{ md: "50%" }} h={{ base: "20%", md: "full" }}>
            {!transcriptStarted ? (
              <Box textAlign={"center"} textColor="gray">
                <Text>
                  Live transcript will appear here shortly after you'll start
                  recording.
                </Text>
              </Box>
            ) : (
              status === "recording" && (
                <LiveTrancription
                  text={webSockets.transcriptTextLive}
                  translateText={webSockets.translateText}
                />
              )
            )}
          </Box>
        </Flex>
      </VStack>
    </Grid>
  );
};

export default TranscriptRecord;

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
import { Box, Text, Grid } from "@chakra-ui/react";
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

  let mp3 = useMp3(details.params.transcriptId, true);

  const router = useRouter();

  const [status, setStatus] = useState(
    webSockets.status.value || transcript.response?.status || "idle"
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
      {status == "processing" && // todo send an event when the mp3 is ready
      webSockets.waveform &&
      webSockets.duration &&
      mp3?.media ? (
        <Player
          topics={webSockets.topics || []}
          useActiveTopic={useActiveTopic}
          waveform={webSockets.waveform}
          media={mp3.media}
          mediaDuration={webSockets.duration}
        />
      ) : status == "processing" ? (
        <WaveformLoading />
      ) : (
        // todo: only start recording animation when you get "recorded" status
        <Recorder transcriptId={details.params.transcriptId} status={status} />
      )}
      <Grid
        templateColumns={{ base: "minmax(0, 1fr)", md: "repeat(2, 1fr)" }}
        templateRows={{
          base: "minmax(0, 1fr) minmax(0, 1fr)",
          md: "minmax(0, 1fr)",
        }}
        gap={2}
        padding={4}
        paddingBottom={0}
        background="gray.bg"
        border={"2px solid"}
        borderColor={"gray.bg"}
        borderRadius={8}
      >
        <TopicList
          topics={webSockets.topics}
          useActiveTopic={useActiveTopic}
          autoscroll={true}
          transcriptId={details.params.transcriptId}
          status={status}
          currentTranscriptText={webSockets.accumulatedText}
        />
        <Box>
          {!transcriptStarted ? (
            <Box textAlign={"center"} textColor="gray">
              <Text>
                The conversation transcript will appear here shortly after you
                start recording.
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
      </Grid>
    </Grid>
  );
};

export default TranscriptRecord;

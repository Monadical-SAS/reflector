"use client";
import { useEffect, useState } from "react";
import useTranscript from "../../useTranscript";
import { useWebSockets } from "../../useWebSockets";
import { lockWakeState, releaseWakeState } from "../../../../lib/wakeLock";
import { useRouter } from "next/navigation";
import useMp3 from "../../useMp3";
import { Center, VStack, Text, Heading, Button } from "@chakra-ui/react";
import FileUploadButton from "../../fileUploadButton";

type TranscriptUpload = {
  params: {
    transcriptId: string;
  };
};

const TranscriptUpload = (details: TranscriptUpload) => {
  const transcript = useTranscript(details.params.transcriptId);
  const [transcriptStarted, setTranscriptStarted] = useState(false);

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
    <>
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
        <Heading size={"lg"}>Upload meeting</Heading>
        <Center h={"full"} w="full">
          <VStack gap={10}>
            {status && status == "idle" && (
              <>
                <Text>
                  Please select the file, supported formats: .mp3, m4a, .wav,
                  .mp4, .mov or .webm
                </Text>
                <FileUploadButton transcriptId={details.params.transcriptId} />
              </>
            )}
            {status && status == "uploaded" && (
              <Text>File is uploaded, processing...</Text>
            )}
            {(status == "recording" || status == "processing") && (
              <>
                <Heading size={"lg"}>Processing your recording...</Heading>
                <Text>
                  You can safely return to the library while your file is being
                  processed.
                </Text>
                <Button
                  colorPalette="blue"
                  onClick={() => {
                    router.push("/browse");
                  }}
                >
                  Browse
                </Button>
              </>
            )}
          </VStack>
        </Center>
      </VStack>
    </>
  );
};

export default TranscriptUpload;

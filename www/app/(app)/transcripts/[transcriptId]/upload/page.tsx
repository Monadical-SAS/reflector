"use client";
import { useEffect, useState, use } from "react";
import { useWebSockets } from "../../useWebSockets";
import { lockWakeState, releaseWakeState } from "../../../../lib/wakeLock";
import { useRouter } from "next/navigation";
import useMp3 from "../../useMp3";
import { Center, VStack, Text, Heading } from "@chakra-ui/react";
import FileUploadButton from "../../fileUploadButton";
import { useTranscriptGet } from "../../../../lib/apiHooks";

type TranscriptUpload = {
  params: Promise<{
    transcriptId: string;
  }>;
};

const TranscriptUpload = (details: TranscriptUpload) => {
  const params = use(details.params);
  const transcript = useTranscriptGet(params.transcriptId);
  const [transcriptStarted, setTranscriptStarted] = useState(false);

  const webSockets = useWebSockets(params.transcriptId);

  const mp3 = useMp3(params.transcriptId, true);

  const router = useRouter();

  const [status_, setStatus] = useState(
    webSockets.status?.value || transcript.data?.status || "idle",
  );

  // status is obviously done if we have transcript
  const status =
    !transcript.isLoading && transcript.data?.status === "ended"
      ? transcript.data?.status
      : status_;

  useEffect(() => {
    if (!transcriptStarted && webSockets.transcriptTextLive.length !== 0)
      setTranscriptStarted(true);
  }, [webSockets.transcriptTextLive]);

  useEffect(() => {
    //TODO HANDLE ERROR STATUS BETTER
    // TODO deprecate webSockets.status.value / depend on transcript.response?.status from query lib
    const newStatus =
      transcript.data?.status === "ended"
        ? "ended"
        : webSockets.status?.value || transcript.data?.status || "idle";
    setStatus(newStatus);
    if (newStatus && (newStatus == "ended" || newStatus == "error")) {
      console.log(newStatus, "redirecting");

      const newUrl = "/transcripts/" + params.transcriptId;
      router.replace(newUrl);
    } else if (
      newStatus &&
      (newStatus == "uploaded" || newStatus == "processing")
    ) {
      // After upload finishes (or if already processing), redirect to the unified processing page
      router.replace(`/transcripts/${params.transcriptId}/processing`);
    }
  }, [webSockets.status?.value, transcript.data?.status]);

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
        minH="100vh"
        pt={4}
        mx="auto"
        w={{ base: "full", md: "container.xl" }}
      >
        <Heading size={"lg"}>Upload meeting</Heading>
        <Center h={"full"} w="full">
          <VStack gap={10} bg="gray.100" p={10} borderRadius="md" maxW="500px">
            <Text>
              Please select the file, supported formats: .mp3, m4a, .wav, .mp4,
              .mov or .webm
            </Text>
            <FileUploadButton
              transcriptId={params.transcriptId}
              onUploadComplete={() =>
                router.replace(`/transcripts/${params.transcriptId}/processing`)
              }
            />
          </VStack>
        </Center>
      </VStack>
    </>
  );
};

export default TranscriptUpload;

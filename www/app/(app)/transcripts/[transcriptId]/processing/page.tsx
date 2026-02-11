"use client";
import { useEffect, use } from "react";
import {
  Heading,
  Text,
  VStack,
  Spinner,
  Button,
  Center,
} from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { useTranscriptGet } from "../../../../lib/apiHooks";
import { parseNonEmptyString } from "../../../../lib/utils";
import { useWebSockets } from "../../useWebSockets";

type TranscriptProcessing = {
  params: Promise<{
    transcriptId: string;
  }>;
};

export default function TranscriptProcessing(details: TranscriptProcessing) {
  const params = use(details.params);
  const transcriptId = parseNonEmptyString(params.transcriptId);
  const router = useRouter();

  const transcript = useTranscriptGet(transcriptId);
  useWebSockets(transcriptId);

  useEffect(() => {
    const status = transcript.data?.status;
    if (!status) return;

    if (status === "ended" || status === "error") {
      router.replace(`/transcripts/${transcriptId}`);
    } else if (status === "recording") {
      router.replace(`/transcripts/${transcriptId}/record`);
    } else if (status === "idle") {
      const dest =
        transcript.data?.source_kind === "file"
          ? `/transcripts/${transcriptId}/upload`
          : `/transcripts/${transcriptId}/record`;
      router.replace(dest);
    }
  }, [
    transcript.data?.status,
    transcript.data?.source_kind,
    router,
    transcriptId,
  ]);

  if (transcript.isLoading) {
    return (
      <VStack align="center" py={8}>
        <Heading size="lg">Loading transcript...</Heading>
      </VStack>
    );
  }

  if (transcript.error) {
    return (
      <VStack align="center" py={8}>
        <Heading size="lg">Transcript not found</Heading>
        <Text>We couldn't load this transcript.</Text>
      </VStack>
    );
  }

  return (
    <>
      <VStack
        align={"left"}
        minH="100vh"
        pt={4}
        mx="auto"
        w={{ base: "full", md: "container.xl" }}
      >
        <Center h={"full"} w="full">
          <VStack gap={10} bg="gray.100" p={10} borderRadius="md" maxW="500px">
            <Spinner size="xl" color="blue.500" />
            <Heading size={"md"} textAlign="center">
              Processing recording
            </Heading>
            <Text color="gray.600" textAlign="center">
              You can safely return to the library while your recording is being
              processed.
            </Text>
            <Button
              onClick={() => {
                router.push("/browse");
              }}
            >
              Browse
            </Button>
          </VStack>
        </Center>
      </VStack>
    </>
  );
}

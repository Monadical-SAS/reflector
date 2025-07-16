"use client";
import React, { useEffect, useState } from "react";
import useAudioDevice from "../useAudioDevice";
import "react-select-search/style.css";
import "../../../styles/button.css";
import "../../../styles/form.scss";
import About from "../../../(aboutAndPrivacy)/about";
import Privacy from "../../../(aboutAndPrivacy)/privacy";
import { useRouter } from "next/navigation";
import useCreateTranscript from "../createTranscript";
import SelectSearch from "react-select-search";
import { supportedLanguages } from "../../../supportedLanguages";
import useSessionStatus from "../../../lib/useSessionStatus";
import { featureEnabled } from "../../../domainContext";
import { signIn } from "next-auth/react";
import {
  Flex,
  Box,
  Spinner,
  Heading,
  Button,
  Card,
  Center,
  Link,
  CardBody,
  Stack,
  Text,
  Icon,
  Grid,
  IconButton,
  Spacer,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  Tooltip,
  Input,
} from "@chakra-ui/react";
const TranscriptCreate = () => {
  const isClient = typeof window !== "undefined";
  const router = useRouter();
  const { isLoading, isAuthenticated } = useSessionStatus();
  const requireLogin = featureEnabled("requireLogin");

  const [name, setName] = useState<string>("");
  const nameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setName(event.target.value);
  };
  const [targetLanguage, setTargetLanguage] = useState<string>("NOTRANSLATION");

  const onLanguageChange = (newval) => {
    (!newval || typeof newval === "string") && setTargetLanguage(newval);
  };

  const createTranscript = useCreateTranscript();

  const [loadingRecord, setLoadingRecord] = useState(false);
  const [loadingUpload, setLoadingUpload] = useState(false);

  const getTargetLanguage = () => {
    if (targetLanguage === "NOTRANSLATION") return;
    return targetLanguage;
  };

  const send = () => {
    if (loadingRecord || createTranscript.loading || permissionDenied) return;
    setLoadingRecord(true);
    createTranscript.create({ name, target_language: getTargetLanguage() });
  };

  const uploadFile = () => {
    if (loadingUpload || createTranscript.loading || permissionDenied) return;
    setLoadingUpload(true);
    createTranscript.create({ name, target_language: getTargetLanguage() });
  };

  useEffect(() => {
    let action = "record";
    if (loadingUpload) action = "upload";

    createTranscript.transcript &&
      router.push(`/transcripts/${createTranscript.transcript.id}/${action}`);
  }, [createTranscript.transcript]);

  useEffect(() => {
    if (createTranscript.error) setLoadingRecord(false);
  }, [createTranscript.error]);

  const { loading, permissionOk, permissionDenied, requestPermission } =
    useAudioDevice();

  return (
    <Flex
      maxW="container.xl"
      flexDir="column"
      margin="auto"
      gap={2}
      maxH="100%"
      px={{ base: 5, md: 10 }}
      py={5}
    >
      <Flex
        flexDir={{ base: "column", md: "row" }}
        justify="space-between"
        align="center"
        gap={8}
      >
        <Flex
          flexDir="column"
          h="full"
          justify="evenly"
          flexBasis="1"
          flexGrow={1}
        >
          <Heading size="lg" textAlign={{ base: "center", md: "left" }}>
            Welcome to Reflector
          </Heading>
          <Text mt={6}>
            Reflector is a transcription and summarization pipeline that
            transforms audio into knowledge.
            <span className="hidden md:block">
              The output is meeting minutes and topic summaries enabling
              topic-specific analyses stored in your systems of record. This is
              accomplished on your infrastructure – without 3rd parties –
              keeping your data private, secure, and organized.
            </span>
          </Text>
          <About buttonText="Learn more" />
          <Text mt={6}>
            In order to use Reflector, we kindly request permission to access
            your microphone during meetings and events.
          </Text>
          {featureEnabled("privacy") && <Privacy buttonText="Privacy policy" />}
        </Flex>
        <Flex flexDir="column" h="full" flexBasis="1" flexGrow={1}>
          <Center>
            {isLoading ? (
              <Spinner />
            ) : requireLogin && !isAuthenticated ? (
              <Button onClick={() => signIn("authentik")} colorScheme="blue">
                Log in
              </Button>
            ) : (
              <Flex
                rounded="xl"
                bg="blue.primary"
                color="white"
                maxW="96"
                p={8}
                flexDir="column"
                my={4}
              >
                <Heading size="md" mb={4}>
                  Try Reflector
                </Heading>
                <Box mb={4}>
                  <Text>Recording name</Text>
                  <div className="select-search-container">
                    <input
                      className="select-search-input"
                      type="text"
                      onChange={nameChange}
                      placeholder="Optional"
                    />
                  </div>
                </Box>
                <Box mb={4}>
                  <Text>Do you want to enable live translation?</Text>
                  <SelectSearch
                    search
                    options={supportedLanguages}
                    value={targetLanguage}
                    onChange={onLanguageChange}
                    placeholder="Choose your language"
                  />
                </Box>
                {isClient && !loading ? (
                  permissionOk ? (
                    <Spacer />
                  ) : permissionDenied ? (
                    <Text className="">
                      Permission to use your microphone was denied, please
                      change the permission setting in your browser and refresh
                      this page.
                    </Text>
                  ) : (
                    <Button
                      colorScheme="whiteAlpha"
                      onClick={requestPermission}
                      disabled={permissionDenied}
                    >
                      Request Microphone Permission
                    </Button>
                  )
                ) : (
                  <Text className="">Checking permissions...</Text>
                )}
                <Button
                  colorScheme="whiteAlpha"
                  onClick={send}
                  isDisabled={!permissionOk || loadingRecord || loadingUpload}
                  mt={2}
                >
                  {loadingRecord ? "Loading..." : "Record Meeting"}
                </Button>
                <Text align="center" m="2">
                  OR
                </Text>
                <Button
                  colorScheme="whiteAlpha"
                  onClick={uploadFile}
                  isDisabled={loadingRecord || loadingUpload}
                >
                  {loadingUpload ? "Loading..." : "Upload File"}
                </Button>
              </Flex>
            )}
          </Center>
        </Flex>
      </Flex>
    </Flex>
  );
};

export default TranscriptCreate;

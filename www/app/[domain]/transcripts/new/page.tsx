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
import { supportedLatinLanguages } from "../../../supportedLanguages";
import { useFiefIsAuthenticated } from "@fief/fief/nextjs/react";
import { featureEnabled } from "../../domainContext";
import { Button, Text } from "@chakra-ui/react";
const TranscriptCreate = () => {
  const router = useRouter();
  const isAuthenticated = useFiefIsAuthenticated();
  const requireLogin = featureEnabled("requireLogin");

  const [name, setName] = useState<string>("");
  const nameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setName(event.target.value);
  };
  const [targetLanguage, setTargetLanguage] = useState<string>();

  const onLanguageChange = (newval) => {
    (!newval || typeof newval === "string") && setTargetLanguage(newval);
  };

  const createTranscript = useCreateTranscript();

  const [loadingRecord, setLoadingRecord] = useState(false);
  const [loadingUpload, setLoadingUpload] = useState(false);

  const send = () => {
    if (loadingRecord || createTranscript.loading || permissionDenied) return;
    setLoadingRecord(true);
    createTranscript.create({ name, target_language: targetLanguage });
  };

  const uploadFile = () => {
    if (loadingUpload || createTranscript.loading || permissionDenied) return;
    setLoadingUpload(true);
    createTranscript.create({ name, target_language: targetLanguage });
  };

  useEffect(() => {
    const action = loadingRecord ? "record" : "upload";
    createTranscript.transcript &&
      router.push(`/transcripts/${createTranscript.transcript.id}/${action}`);
  }, [createTranscript.transcript]);

  useEffect(() => {
    if (createTranscript.error) setLoadingRecord(false);
  }, [createTranscript.error]);

  const { loading, permissionOk, permissionDenied, requestPermission } =
    useAudioDevice();

  return (
    <div className="grid grid-rows-layout-topbar gap-2 lg:gap-4 max-h-full overflow-y-scroll">
      <div className="lg:grid lg:grid-cols-2 lg:grid-rows-1 lg:gap-4 lg:h-full h-auto flex flex-col">
        <section className="flex flex-col w-full lg:h-full items-center justify-evenly p-4 md:px-6 md:py-8">
          <div className="flex flex-col max-w-xl items-center justify-center">
            <h1 className="text-2xl font-bold mb-2">Welcome to Reflector</h1>
            <p>
              Reflector is a transcription and summarization pipeline that
              transforms audio into knowledge.
              <span className="hidden md:block">
                The output is meeting minutes and topic summaries enabling
                topic-specific analyses stored in your systems of record. This
                is accomplished on your infrastructure – without 3rd parties –
                keeping your data private, secure, and organized.
              </span>
            </p>
            <About buttonText="Learn more" />
            <p className="mt-6">
              In order to use Reflector, we kindly request permission to access
              your microphone during meetings and events.
            </p>
            {featureEnabled("privacy") && (
              <Privacy buttonText="Privacy policy" />
            )}
          </div>
        </section>
        <section className="flex flex-col justify-center items-center w-full h-full">
          {requireLogin && !isAuthenticated ? (
            <button
              className="mt-4 bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white font-bold py-2 px-4 rounded"
              onClick={() => router.push("/login")}
            >
              Log in
            </button>
          ) : (
            <div className="rounded-xl md:bg-blue-200 md:w-96 p-4 lg:p-6 flex flex-col mb-4 md:mb-10">
              <h2 className="text-2xl font-bold mt-2 mb-2">Try Reflector</h2>
              <label className="mb-3">
                <p>Recording name</p>
                <div className="select-search-container">
                  <input
                    className="select-search-input"
                    type="text"
                    onChange={nameChange}
                    placeholder="Optional"
                  />
                </div>
              </label>
              <label className="mb-3">
                <p>Do you want to enable live translation?</p>
                <SelectSearch
                  search
                  options={supportedLatinLanguages}
                  value={targetLanguage}
                  onChange={onLanguageChange}
                  placeholder="Choose your language"
                />
              </label>
              {loading ? (
                <p className="">Checking permissions...</p>
              ) : permissionOk ? (
                <p className=""> Microphone permission granted </p>
              ) : permissionDenied ? (
                <p className="">
                  Permission to use your microphone was denied, please change
                  the permission setting in your browser and refresh this page.
                </p>
              ) : (
                <button
                  className="mt-4 bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white font-bold py-2 px-4 rounded"
                  onClick={requestPermission}
                  disabled={permissionDenied}
                >
                  Request Microphone Permission
                </button>
              )}
              <Button
                colorScheme="blue"
                onClick={send}
                isDisabled={!permissionOk || loadingRecord || loadingUpload}
              >
                {loadingRecord ? "Loading..." : "Record Meeting"}
              </Button>
              <Text align="center" m="2">
                OR
              </Text>
              <Button
                colorScheme="blue"
                onClick={uploadFile}
                isDisabled={!permissionOk || loadingRecord || loadingUpload}
              >
                {loadingUpload ? "Loading..." : "Upload File"}
              </Button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default TranscriptCreate;

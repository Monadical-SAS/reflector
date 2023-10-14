"use client";
import React, { useEffect, useState } from "react";
import useAudioDevice from "../useAudioDevice";
import "../../styles/button.css";
import getApi from "../../lib/getApi";
import About from "../../(aboutAndPrivacy)/about";
import Privacy from "../../(aboutAndPrivacy)/privacy";
import { useRouter } from "next/navigation";
import useCreateTranscript from "../createTranscript";
import SelectSearch from "react-select-search";
import { supportedLatinLanguages } from "../../supportedLanguages";
import "react-select-search/style.css";

const TranscriptCreate = () => {
  // const transcript = useTranscript(stream, api);
  const router = useRouter();
  const api = getApi();

  const [name, setName] = useState<string>();
  const nameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setName(event.target.value);
  };
  const [targetLanguage, setTargetLanguage] = useState<string>();

  const onLanguageChange = (newval) => {
    typeof newval === "string" && setTargetLanguage(newval);
  };

  const createTranscript = useCreateTranscript();

  const send = () => {
    if (createTranscript.loading || permissionDenied) return;
    createTranscript.create({ name, targetLanguage });
  };
  useEffect(() => {
    createTranscript.response &&
      router.push(`/transcripts/${createTranscript.response.id}/record`);
  }, [createTranscript.response]);

  const { loading, permissionOk, permissionDenied, requestPermission } =
    useAudioDevice();

  return (
    <>
      <div></div>
      <div className="grid grid-cols-1 lg:grid-cols-2 grid-rows-mobile-inner lg:grid-rows-1 gap-2 lg:gap-4 h-full">
        <section className="flex flex-col w-full h-full items-center justify-evenly p-4 md:px-6 md:py-8">
          <div className="flex flex-col max-w-xl items-center justify-center">
            <h1 className="text-2xl font-bold mb-2">
              Welcome to reflector.media
            </h1>
            <p>
              Reflector is a transcription and summarization pipeline that
              transforms audio into knowledge. The output is meeting minutes and
              topic summaries enabling topic-specific analyses stored in your
              systems of record. This is accomplished on your infrastructure –
              without 3rd parties – keeping your data private, secure, and
              organized.
            </p>
            <About buttonText="Learn more" />
          </div>
        </section>
        <section className="rounded-xl md:bg-blue-200 flex flex-col justify-start p-6">
          <h2 className="text-2xl font-bold mt-4 mb-2"> Try Reflector</h2>
          <label className="mb-3">
            <p>What is this meeting about ?</p>
            <input type="text" onChange={nameChange} />
          </label>

          <label className="mb-3">
            <p>Do you need live translation ?</p>
            <SelectSearch
              search
              options={supportedLatinLanguages}
              value={targetLanguage}
              onChange={onLanguageChange}
              placeholder="Choose your language"
            />
          </label>

          {loading ? (
            <p className="">Checking permission...</p>
          ) : permissionOk ? (
            <> Microphone permission granted </>
          ) : (
            <>
              <p className="">
                In order to use Reflector, we kindly request permission to
                access your microphone during meetings and events.
                <br />
                <Privacy buttonText="Privacy policy" />
                <br />
                {permissionDenied &&
                  "Permission to use your microphone was denied, please change the permission setting in your browser and refresh this page."}
              </p>
              <button
                className="mt-4 bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white font-bold py-2 px-4 rounded m-auto"
                onClick={requestPermission}
                disabled={permissionDenied}
              >
                {permissionDenied ? "Access denied" : "Grant Permission"}
              </button>
            </>
          )}
          <button onClick={send} disabled={!permissionOk}>
            {createTranscript.loading ? "loading" : "Send"}
          </button>
        </section>
      </div>
    </>
  );
};

export default TranscriptCreate;

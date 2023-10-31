"use client";
import React, { useEffect, useState } from "react";
import useAudioDevice from "../useAudioDevice";
import "react-select-search/style.css";
import "../../styles/button.css";
import "../../styles/form.scss";
import getApi from "../../lib/getApi";
import { useRouter } from "next/navigation";
import useCreateTranscript from "../createTranscript";
import SplashScreen from "../../(splashScreen)/splashScreen";

const TranscriptCreate = () => {
  // const transcript = useTranscript(stream, api);
  const router = useRouter();
  const api = getApi();

  const [name, setName] = useState<string>();
  const [translationLanguage, setTranslationLanguage] = useState<string>();
  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setName(event.target.value);
  };

  const createTranscript = useCreateTranscript();

  useEffect(() => {
    createTranscript.response &&
      router.push(`/transcripts/${createTranscript.response.id}/record`);
  }, [createTranscript.response]);

  useEffect(() => {
    if (createTranscript.error) setLoadingSend(false);
  }, [createTranscript.error]);

  const { loading, permissionOk, permissionDenied, requestPermission } =
    useAudioDevice();

  const [loadingSend, setLoadingSend] = useState(false);

  const send = () => {
    if (loadingSend || createTranscript.loading || permissionDenied) return;

    setLoadingSend(true);
    const targetLanguage = translationLanguage;
    createTranscript.create({ name, targetLanguage });
  };

  return (
    <SplashScreen
      create={createTranscript.create}
      loading={loading}
      handleNameChange={handleNameChange}
      permissionOk={permissionOk}
      permissionDenied={permissionDenied}
      requestPermission={requestPermission}
      createTranscriptLoading={createTranscript.loading}
      translationLanguage={translationLanguage}
      setTranslationLanguage={(newLang) => setTranslationLanguage(newLang)}
      send={send}
      loadingSend={loadingSend}
    />
  );
};

export default TranscriptCreate;

import { useEffect, useState } from "react";
import { DefaultApi, V1TranscriptsCreateRequest } from "../api/apis/DefaultApi";
import { GetTranscript } from "../api";
import { useError } from "../(errors)/errorContext";
import handleError from "../(errors)/handleError";

type UseTranscript = {
  response: GetTranscript | null;
  loading: boolean;
  createTranscript: () => void;
};

const useTranscript = (api: DefaultApi): UseTranscript => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const { setError } = useError();

  const createTranscript = () => {
    setLoading(true);
    const requestParameters: V1TranscriptsCreateRequest = {
      createTranscript: {
        name: "Weekly All-Hands", // Hardcoded for now
        targetLanguage: "fr", // Hardcoded for now
      },
    };

    console.debug(
      "POST - /v1/transcripts/ - Requesting new transcription creation",
      requestParameters,
    );

    api
      .v1TranscriptsCreate(requestParameters)
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("New transcript created:", result);
      })
      .catch((err) => {
        const errorString = err.response || err.message || "Unknown error";
        handleError(setError, errorString, err);
        setLoading(false);
        console.error("Error creating transcript:", errorString);
      });
  };

  useEffect(() => {
    createTranscript();
  }, []);

  return { response, loading, createTranscript };
};

export default useTranscript;

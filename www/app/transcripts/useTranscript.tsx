import { useEffect, useState } from "react";
import { DefaultApi, V1TranscriptsCreateRequest } from "../api/apis/DefaultApi";
import { Configuration } from "../api/runtime";
import { GetTranscript } from "../api";
import getApi from "../lib/getApi";

type UseTranscript = {
  response: GetTranscript | null;
  loading: boolean;
  error: string | null;
  createTranscript: () => void;
};

const useTranscript = (): UseTranscript => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const api = getApi();

  const createTranscript = () => {
    setLoading(true);
    const requestParameters: V1TranscriptsCreateRequest = {
      createTranscript: {
        name: "Weekly All-Hands", // Hardcoded for now
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
        setError(errorString);
        setLoading(false);
        console.error("Error creating transcript:", errorString);
      });
  };

  useEffect(() => {
    createTranscript();
  }, []);

  return { response, loading, error, createTranscript };
};

export default useTranscript;

import { useEffect, useState } from "react";
import { DefaultApi } from "../api/apis/DefaultApi";
import { Configuration } from "../api/runtime";

const useTranscript = () => {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const apiConfiguration = new Configuration({
    basePath: process.env.NEXT_PUBLIC_API_URL,
  });
  const api = new DefaultApi(apiConfiguration);

  const createTranscript = () => {
    setLoading(true);
    const requestParameters = {
      createTranscript: {
        name: "Weekly All-Hands", // Hardcoded for now
      },
    };

    console.debug(
      "POST - /v1/transcripts/ - Requesting new transcription creation",
      requestParameters,
    );

    api
      .transcriptsCreateV1TranscriptsPost(requestParameters)
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

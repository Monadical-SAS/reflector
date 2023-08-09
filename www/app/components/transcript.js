import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const useTranscript = () => {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const createTranscript = () => {
    setLoading(true);
    const url = API_URL + "/v1/transcripts/";
    const data = {
      name: "Weekly All-Hands", // Hardcoded for now
    };

    console.debug(
      "POST - /v1/transcripts/ - Requesting new transcription creation",
      data,
    );

    axios
      .post(url, data)
      .then((result) => {
        setResponse(result.data);
        setLoading(false);
        console.debug("New transcript created:", result.data);
      })
      .catch((err) => {
        const errorString = err.response || err || "Unknown error";
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

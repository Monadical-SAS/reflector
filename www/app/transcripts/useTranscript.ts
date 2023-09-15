import { useEffect, useState } from "react";
import {
  DefaultApi,
  V1TranscriptGetRequest,
  V1TranscriptsCreateRequest,
} from "../api/apis/DefaultApi";
import { GetTranscript } from "../api";
import { useError } from "../(errors)/errorContext";

type Transcript = {
  response: GetTranscript | null;
  loading: boolean;
  error: Error | null;
};

const useTranscript = (
  stream: MediaStream | null,
  api: DefaultApi,
  id: string | null = null,
): Transcript => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();

  const getOrCreateTranscript = (id: string | null) => {
    if (id) {
      getTranscript(id);
    } else if (stream) {
      createTranscript();
    }
  };

  const getTranscript = (id: string | null) => {
    if (!id) throw new Error("Transcript ID is required to get transcript");

    setLoading(true);
    const requestParameters: V1TranscriptGetRequest = {
      transcriptId: id,
    };
    api
      .v1TranscriptGet(requestParameters)
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("New transcript created:", result);
      })
      .catch((err) => {
        setError(err);
        setErrorState(err);
      });
  };

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
        setError(err);
        setErrorState(err);
      });
  };

  useEffect(() => {
    getOrCreateTranscript(id);
  }, [id, stream]);

  return { response, loading, error };
};

export default useTranscript;

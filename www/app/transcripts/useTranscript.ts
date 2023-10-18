import { useEffect, useState } from "react";
import {
  V1TranscriptGetRequest,
  V1TranscriptsCreateRequest,
} from "../api/apis/DefaultApi";
import { GetTranscript } from "../api";
import { useError } from "../(errors)/errorContext";
import getApi from "../lib/getApi";

type Transcript = {
  response: GetTranscript | null;
  loading: boolean;
  error: Error | null;
};

const useTranscript = (id: string | null): Transcript => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi();

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
        console.debug("Transcript Loaded:", result);
      })
      .catch((err) => {
        setError(err);
        setErrorState(err);
      });
  };

  useEffect(() => {
    getTranscript(id);
  }, [id]);

  return { response, loading, error };
};

export default useTranscript;

import { useEffect, useState } from "react";
import {
  DefaultApi,
  V1TranscriptsCreateRequest,
} from "../../api/apis/DefaultApi";
import { GetTranscript } from "../../api";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";

type CreateTranscript = {
  response: GetTranscript | null;
  loading: boolean;
  error: Error | null;
  create: (params: V1TranscriptsCreateRequest["createTranscript"]) => void;
};

const useCreateTranscript = (): CreateTranscript => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi();

  const create = (params: V1TranscriptsCreateRequest["createTranscript"]) => {
    if (loading || !api) return;

    setLoading(true);
    const requestParameters: V1TranscriptsCreateRequest = {
      createTranscript: {
        name: params.name || "Unnamed Transcript", // Default
        targetLanguage: params.targetLanguage || "en", // Default
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
        setError(
          err,
          "There was an issue creating a transcript, please try again.",
        );
        setErrorState(err);
        setLoading(false);
      });
  };

  return { response, loading, error, create };
};

export default useCreateTranscript;

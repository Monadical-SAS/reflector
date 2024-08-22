import { useEffect, useState } from "react";

import { useError } from "../../(errors)/errorContext";
import { CreateTranscript, GetTranscript } from "../../api";
import useApi from "../../lib/useApi";

type UseCreateTranscript = {
  transcript: GetTranscript | null;
  loading: boolean;
  error: Error | null;
  create: (transcriptCreationDetails: CreateTranscript) => void;
};

const useCreateTranscript = (): UseCreateTranscript => {
  const [transcript, setTranscript] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();

  const create = (transcriptCreationDetails: CreateTranscript) => {
    if (loading || !api) return;

    setLoading(true);

    api
      .v1TranscriptsCreate({ requestBody: transcriptCreationDetails })
      .then((transcript) => {
        setTranscript(transcript);
        setLoading(false);
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

  return { transcript, loading, error, create };
};

export default useCreateTranscript;

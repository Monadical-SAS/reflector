import { useState } from "react";
import { useError } from "../../(errors)/errorContext";
import { GetTranscript, CreateTranscript } from "../../api";
import useApi from "../../lib/useApi";

type UseTranscript = {
  transcript: GetTranscript | null;
  loading: boolean;
  error: Error | null;
  create: (transcriptCreationDetails: CreateTranscript) => void;
};

const useCreateTranscript = (): UseTranscript => {
  const [transcript, setTranscript] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();

  const create = (transcriptCreationDetails: CreateTranscript) => {
    if (loading || !api) return;

    setLoading(true);

    console.log(
      "POST - /v1/transcripts/ - Requesting new transcription creation",
      transcriptCreationDetails,
      api,
    );

    console.log("START");

    api
      .v1TranscriptsCreate(transcriptCreationDetails)
      .then((transcript) => {
        console.debug("New transcript created:", transcript);
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
      })
      .finally(() => {
        console.log("At least this should display?");
      });
  };

  return { transcript, loading, error, create };
};

export default useCreateTranscript;

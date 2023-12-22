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

    console.debug(
      "POST - /v1/transcripts/ - Requesting new transcription creation",
      transcriptCreationDetails,
      api
    );

    const aaa = async () => {
      console.log("Calling API...");

      await new Promise((res) => setTimeout(res, 500));

      console.log("500 ms elapsed - calling api");

      const test = await api.v1TranscriptsCreate(transcriptCreationDetails);
      console.log(test);
    };

    aaa();

    api.v1TranscriptsCreate(transcriptCreationDetails)
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
      });
  };

  return { transcript, loading, error, create };
};

export default useCreateTranscript;

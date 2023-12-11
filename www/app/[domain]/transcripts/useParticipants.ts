import { useEffect, useState } from "react";
import { V1TranscriptGetParticipantsRequest } from "../../api/apis/DefaultApi";
import { GetTranscript, Participant } from "../../api";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";
import { shouldShowError } from "../../lib/errorUtils";

type ErrorParticipants = {
  error: Error;
  loading: false;
  response: null;
};

type LoadingParticipants = {
  response: Participant[] | null;
  loading: true;
  error: false;
};

type SuccessParticipants = {
  response: Participant[];
  loading: boolean;
  error: null;
};

export type UseParticipants = (
  | ErrorParticipants
  | LoadingParticipants
  | SuccessParticipants
) & { refetch: () => void };

const useParticipants = (transcriptId: string): UseParticipants => {
  const [response, setResponse] = useState<Participant[] | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi();
  const [count, setCount] = useState(0);

  const refetch = () => {
    setCount(count + 1);
    setLoading(true);
    setErrorState(null);
  };

  useEffect(() => {
    if (!transcriptId || !api) return;

    setLoading(true);
    const requestParameters: V1TranscriptGetParticipantsRequest = {
      transcriptId,
    };
    api
      .v1TranscriptGetParticipants(requestParameters)
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("Participants Loaded:", result);
      })
      .catch((error) => {
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman) {
          setError(error, "There was an error loading the participants");
        } else {
          setError(error);
        }
        setErrorState(error);
      });
  }, [transcriptId, !api, count]);

  return { response, loading, error, refetch } as UseParticipants;
};

export default useParticipants;

import { useEffect, useState } from "react";
import { V1TranscriptGetParticipantsRequest } from "../../api/apis/DefaultApi";
import { GetTranscript, Participant } from "../../api";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";
import { shouldShowError } from "../../lib/errorUtils";

type ErrorParticipants = {
  error: Error;
  loading: false;
  response: any;
};

type LoadingParticipants = {
  response: any;
  loading: true;
  error: false;
};

type SuccessParticipants = {
  response: Participant[];
  loading: false;
  error: null;
};

const useParticipants = (
  transcriptId: string,
): ErrorParticipants | LoadingParticipants | SuccessParticipants => {
  const [response, setResponse] = useState<GetTranscript | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi();

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
  }, [transcriptId, !api]);

  return { response, loading, error } as
    | ErrorParticipants
    | LoadingParticipants
    | SuccessParticipants;
};

export default useParticipants;

import { useEffect, useState } from "react";
import { useError } from "../../(errors)/errorContext";
import { GetMeeting } from "../../api";
import { shouldShowError } from "../../lib/errorUtils";
import useApi from "../../lib/useApi";

type ErrorMeeting = {
  error: Error;
  loading: false;
  response: null;
  reload: () => void;
};

type LoadingMeeting = {
  response: null;
  loading: true;
  error: false;
  reload: () => void;
};

type SuccessMeeting = {
  response: GetMeeting;
  loading: false;
  error: null;
  reload: () => void;
};

const useMeeting = (
  id: string | null | undefined,
): ErrorMeeting | LoadingMeeting | SuccessMeeting => {
  const [response, setResponse] = useState<GetMeeting | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const [reload, setReload] = useState(0);
  const { setError } = useError();
  const api = useApi();
  const reloadHandler = () => setReload((prev) => prev + 1);

  useEffect(() => {
    if (!id || !api) return;

    if (!response) {
      setLoading(true);
    }

    api
      .v1MeetingGet({ meetingId: id })
      .then((result) => {
        setResponse(result);
        setLoading(false);
        console.debug("Meeting Loaded:", result);
      })
      .catch((error) => {
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman) {
          setError(error, "There was an error loading the meeting");
        } else {
          setError(error);
        }
        setErrorState(error);
      });
  }, [id, !api, reload]);

  return { response, loading, error, reload: reloadHandler } as
    | ErrorMeeting
    | LoadingMeeting
    | SuccessMeeting;
};

export default useMeeting;

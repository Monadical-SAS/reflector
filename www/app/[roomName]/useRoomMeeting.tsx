import { useEffect, useState } from "react";
import { useError } from "../(errors)/errorContext";
import { Meeting } from "../api";
import { shouldShowError } from "../lib/errorUtils";
import useApi from "../lib/useApi";
import { notFound } from "next/navigation";

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
  response: Meeting;
  loading: false;
  error: null;
  reload: () => void;
};

const useRoomMeeting = (
  roomName: string | null | undefined,
): ErrorMeeting | LoadingMeeting | SuccessMeeting => {
  const [response, setResponse] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const [reload, setReload] = useState(0);
  const { setError } = useError();
  const api = useApi();
  const reloadHandler = () => setReload((prev) => prev + 1);

  useEffect(() => {
    if (!roomName || !api) return;

    if (!response) {
      setLoading(true);
    }

    api
      .v1RoomsCreateMeeting({ roomName })
      .then((result) => {
        setResponse(result);
        setLoading(false);
      })
      .catch((error) => {
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman && error.status !== 404) {
          setError(
            error,
            "There was an error loading the meeting. Please try again by refreshing the page.",
          );
        } else {
          setError(error);
        }
        setErrorState(error);
      });
  }, [roomName, !api, reload]);

  return { response, loading, error, reload: reloadHandler } as
    | ErrorMeeting
    | LoadingMeeting
    | SuccessMeeting;
};

export default useRoomMeeting;

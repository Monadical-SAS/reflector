import { useEffect, useState } from "react";
import { useError } from "../(errors)/errorContext";
import { Meeting } from "../lib/api-types";
import { shouldShowError } from "../lib/errorUtils";
import { useRoomsCreateMeeting } from "../lib/api-hooks";
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
  const [reload, setReload] = useState(0);
  const { setError } = useError();
  const createMeetingMutation = useRoomsCreateMeeting();
  const reloadHandler = () => setReload((prev) => prev + 1);

  useEffect(() => {
    if (!roomName) return;

    const createMeeting = async () => {
      try {
        const result = await createMeetingMutation.mutateAsync({
          params: {
            path: {
              room_name: roomName,
            },
          },
        });
        setResponse(result);
      } catch (error: any) {
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman && error.status !== 404) {
          setError(
            error,
            "There was an error loading the meeting. Please try again by refreshing the page.",
          );
        } else {
          setError(error);
        }
      }
    };

    createMeeting();
  }, [roomName, reload]);

  const loading = createMeetingMutation.isPending && !response;
  const error = createMeetingMutation.error as Error | null;

  return { response, loading, error, reload: reloadHandler } as
    | ErrorMeeting
    | LoadingMeeting
    | SuccessMeeting;
};

export default useRoomMeeting;

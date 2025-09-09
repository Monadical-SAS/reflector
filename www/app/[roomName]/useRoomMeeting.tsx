import { useEffect, useState } from "react";
import { useError } from "../../../(errors)/errorContext";
import type { components } from "../../../reflector-api";
import { shouldShowError } from "../../../lib/errorUtils";

type Meeting = components["schemas"]["Meeting"];
import { useRoomsCreateMeeting } from "../../../lib/apiHooks";
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
  meetingId?: string,
): ErrorMeeting | LoadingMeeting | SuccessMeeting => {
  const [response, setResponse] = useState<Meeting | null>(null);
  const [reload, setReload] = useState(0);
  const { setError } = useError();
  const createMeetingMutation = useRoomsCreateMeeting();
  const reloadHandler = () => setReload((prev) => prev + 1);

  useEffect(() => {
    if (!roomName) return;

    // For any case where we need a meeting (with or without meetingId),
    // we create a new meeting. The meetingId parameter can be used for
    // additional logic in the future if needed (e.g., fetching existing meetings)
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
  }, [roomName, meetingId, reload]);

  const loading = createMeetingMutation.isPending && !response;
  const error = createMeetingMutation.error as Error | null;

  return { response, loading, error, reload: reloadHandler } as
    | ErrorMeeting
    | LoadingMeeting
    | SuccessMeeting;
};

export default useRoomMeeting;

import { useEffect, useState } from "react";
import { useError } from "../(errors)/errorContext";
import type { components } from "../reflector-api";
import { shouldShowError } from "../lib/errorUtils";
import { useUuidV4 as useUuid } from "react-uuid-hook";

type Meeting = components["schemas"]["Meeting"];
import { useRoomsCreateMeeting } from "../lib/apiHooks";

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

  // Generate idempotency key based on room name
  const [uuid, refreshUuid] = useUuid(roomName || "");

  useEffect(() => {
    if (!roomName) return;

    // For any case where we need a meeting (with or without meetingId),
    const createMeeting = async () => {
      try {
        const result = await createMeetingMutation.mutateAsync({
          params: {
            path: {
              room_name: roomName,
            },
          },
          body: {
            allow_duplicated: false,
            idempotency_key: uuid,
          },
        });
        setResponse(result);
        refreshUuid();
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

    createMeeting().then(() => {});
    // roomName is excluded, giving place to uuid that is generated on roomName prefix. roomName itself is used though
  }, [reload, uuid]);

  const loading = createMeetingMutation.isPending && !response;
  const error = createMeetingMutation.error as Error | null;

  return { response, loading, error, reload: reloadHandler } as
    | ErrorMeeting
    | LoadingMeeting
    | SuccessMeeting;
};

export default useRoomMeeting;

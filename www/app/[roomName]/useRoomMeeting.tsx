import { useEffect, useState, useRef, useCallback } from "react";
import { useError } from "../(errors)/errorContext";
import { Meeting, Pong } from "../api";
import { shouldShowError } from "../lib/errorUtils";
import useApi from "../lib/useApi";

type ErrorMeeting = {
  error: Error;
  loading: false;
  response: null;
  reload: () => void;
  startKeepalive: (onKeepalive?: (pong: Pong) => void) => void;
  stopKeepalive: () => void;
  endMeeting: () => Promise<void>;
};

type LoadingMeeting = {
  response: null;
  loading: true;
  error: false;
  reload: () => void;
  startKeepalive: (onKeepalive?: (pong: Pong) => void) => void;
  stopKeepalive: () => void;
  endMeeting: () => Promise<void>;
};

type SuccessMeeting = {
  response: Meeting;
  loading: false;
  error: null;
  reload: () => void;
  startKeepalive: (onKeepalive?: (pong: Pong) => void) => void;
  stopKeepalive: () => void;
  endMeeting: () => Promise<void>;
};

const useRoomMeeting = (
  roomName: string | null | undefined
): ErrorMeeting | LoadingMeeting | SuccessMeeting => {
  const [response, setResponse] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const [reload, setReload] = useState(0);
  const { setError } = useError();
  const api = useApi();
  const keepaliveInterval = useRef<number>();
  const keepaliveCallback = useRef<((pong: Pong) => void) | undefined>();
  const reloadHandler = () => setReload((prev) => prev + 1);

  const keepalive = useCallback(async () => {
    if (!response || !api || !roomName) return;

    try {
      const pong = await api.v1RoomsKeepAlive({
        roomName,
        meetingId: response.id,
      });
      keepaliveCallback.current?.(pong);
    } catch (error) {
      console.error("Keepalive failed:", error);
    }
  }, [api, response, roomName]);

  const startKeepalive = useCallback(
    (onKeepalive?: (pong: Pong) => void) => {
      keepaliveCallback.current = onKeepalive;
      if (!keepaliveInterval.current) {
        keepalive();
        keepaliveInterval.current = window.setInterval(keepalive, 10000);
      }
    },
    [keepalive],
  );

  const stopKeepalive = useCallback(() => {
    if (keepaliveInterval.current) {
      window.clearInterval(keepaliveInterval.current);
      keepaliveInterval.current = undefined;
    }
    keepaliveCallback.current = undefined;
  }, []);

  const endMeeting = useCallback(async () => {
    if (!response || !api || !roomName) return;

    try {
      await api.v1RoomsEndMeeting({
        roomName,
        meetingId: response.id,
      });
      stopKeepalive();
    } catch (error) {
      console.error("End meeting failed:", error);
      throw error;
    }
  }, [api, response, roomName, stopKeepalive]);

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
        console.debug("Meeting Loaded:", result);
      })
      .catch((error) => {
        const shouldShowHuman = shouldShowError(error);
        if (shouldShowHuman) {
          setError(
            error,
            "There was an error loading the meeting. Please try again by refreshing the page."
          );
        } else {
          setError(error);
        }
        setErrorState(error);
      });

    return () => {
      stopKeepalive();
    };
  }, [roomName, !api, reload]);

  return {
    response,
    loading,
    error,
    reload: reloadHandler,
    startKeepalive,
    stopKeepalive,
    endMeeting,
  } as ErrorMeeting | LoadingMeeting | SuccessMeeting;
};

export default useRoomMeeting;

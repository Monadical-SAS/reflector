import { useContext, useEffect, useState } from "react";
import { DomainContext } from "../../domainContext";
import getApi from "../../lib/useApi";

export type Mp3Response = {
  media: HTMLMediaElement | null;
  loading: boolean;
  error: string | null;
  getNow: () => void;
  audioDeleted: boolean | null;
};

const useMp3 = (transcriptId: string, waiting?: boolean): Mp3Response => {
  const [media, setMedia] = useState<HTMLMediaElement | null>(null);
  const [later, setLater] = useState(waiting);
  const [audioLoading, setAudioLoading] = useState<boolean>(true);
  const [audioLoadingError, setAudioLoadingError] = useState<null | string>(
    null,
  );
  const [transcriptMetadataLoading, setTranscriptMetadataLoading] =
    useState<boolean>(true);
  const [transcriptMetadataLoadingError, setTranscriptMetadataLoadingError] =
    useState<string | null>(null);
  const [audioDeleted, setAudioDeleted] = useState<boolean | null>(null);
  const api = getApi();
  const { api_url } = useContext(DomainContext);
  const accessTokenInfo = api?.httpRequest?.config?.TOKEN;

  const [serviceWorker, setServiceWorker] =
    useState<ServiceWorkerRegistration | null>(null);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js").then((worker) => {
        setServiceWorker(worker);
      });
    }
    return () => {
      serviceWorker?.unregister();
    };
  }, []);

  useEffect(() => {
    if (!navigator.serviceWorker) return;
    if (!navigator.serviceWorker.controller) return;
    if (!serviceWorker) return;
    // Send the token to the service worker
    navigator.serviceWorker.controller.postMessage({
      type: "SET_AUTH_TOKEN",
      token: accessTokenInfo,
    });
  }, [navigator.serviceWorker, !serviceWorker, accessTokenInfo]);

  useEffect(() => {
    if (!transcriptId || !api || later) return;

    let stopped = false;
    let audioElement: HTMLAudioElement | null = null;
    let handleCanPlay: (() => void) | null = null;
    let handleError: (() => void) | null = null;

    setTranscriptMetadataLoading(true);
    setAudioLoading(true);

    // First fetch transcript info to check if audio is deleted
    api
      .v1TranscriptGet({ transcriptId })
      .then((transcript) => {
        if (stopped) {
          return;
        }

        const deleted = transcript.audio_deleted || false;
        setAudioDeleted(deleted);
        setTranscriptMetadataLoadingError(null);

        if (deleted) {
          // Audio is deleted, don't attempt to load it
          setMedia(null);
          setAudioLoadingError(null);
          setAudioLoading(false);
          return;
        }

        // Audio is not deleted, proceed to load it
        audioElement = document.createElement("audio");
        audioElement.src = `${api_url}/v1/transcripts/${transcriptId}/audio/mp3`;
        audioElement.crossOrigin = "anonymous";
        audioElement.preload = "auto";

        handleCanPlay = () => {
          if (stopped) return;
          setAudioLoading(false);
          setAudioLoadingError(null);
        };

        handleError = () => {
          if (stopped) return;
          setAudioLoading(false);
          setAudioLoadingError("Failed to load audio");
        };

        audioElement.addEventListener("canplay", handleCanPlay);
        audioElement.addEventListener("error", handleError);

        if (!stopped) {
          setMedia(audioElement);
        }
      })
      .catch((error) => {
        if (stopped) return;
        console.error("Failed to fetch transcript:", error);
        setAudioDeleted(null);
        setTranscriptMetadataLoadingError(error.message);
        setAudioLoading(false);
      })
      .finally(() => {
        if (stopped) return;
        setTranscriptMetadataLoading(false);
      });

    return () => {
      stopped = true;
      if (audioElement) {
        audioElement.src = "";
        if (handleCanPlay)
          audioElement.removeEventListener("canplay", handleCanPlay);
        if (handleError) audioElement.removeEventListener("error", handleError);
      }
    };
  }, [transcriptId, api, later, api_url]);

  const getNow = () => {
    setLater(false);
  };

  const loading = audioLoading || transcriptMetadataLoading;
  const error = audioLoadingError || transcriptMetadataLoadingError;

  return { media, loading, error, getNow, audioDeleted };
};

export default useMp3;

import { useContext, useEffect, useState } from "react";
import { useError } from "../../(errors)/errorContext";
import { DomainContext } from "../domainContext";
import getApi from "../../lib/getApi";
import { useFiefAccessTokenInfo } from "@fief/fief/build/esm/nextjs/react";
import { shouldShowError } from "../../lib/errorUtils";

type Mp3Response = {
  url: string | null;
  media: HTMLMediaElement | null;
  loading: boolean;
  error: Error | null;
};

const useMp3 = (protectedPath: boolean, id: string): Mp3Response => {
  const [url, setUrl] = useState<string | null>(null);
  const [media, setMedia] = useState<HTMLMediaElement | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi(protectedPath);
  const { api_url } = useContext(DomainContext);
  const accessTokenInfo = useFiefAccessTokenInfo();
  const [serviceWorkerReady, setServiceWorkerReady] = useState(false);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js").then(() => {
        setServiceWorkerReady(true);
      });
    }
  }, []);

  useEffect(() => {
    if (!navigator.serviceWorker) return;
    if (!navigator.serviceWorker.controller) return;
    if (!serviceWorkerReady) return;
    // Send the token to the service worker
    navigator.serviceWorker.controller.postMessage({
      type: "SET_AUTH_TOKEN",
      token: accessTokenInfo?.access_token,
    });
  }, [navigator.serviceWorker, serviceWorkerReady, accessTokenInfo]);

  const getMp3 = (id: string) => {
    if (!id || !api) return;

    // createa a audio element and set the source
    setLoading(true);
    const audioElement = document.createElement("audio");
    audioElement.src = `${api_url}/v1/transcripts/${id}/audio/mp3`;
    audioElement.crossOrigin = "anonymous";
    audioElement.preload = "auto";
    setMedia(audioElement);
    setLoading(false);
  };

  useEffect(() => {
    getMp3(id);
  }, [id, api]);

  return { url, media, loading, error };
};

export default useMp3;

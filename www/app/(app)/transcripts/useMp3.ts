import { useContext, useEffect, useState } from "react";
import { DomainContext } from "../../domainContext";
import getApi from "../../lib/useApi";
import { useFiefAccessTokenInfo } from "@fief/fief/build/esm/nextjs/react";

export type Mp3Response = {
  media: HTMLMediaElement | null;
  loading: boolean;
  getNow: () => void;
};

const useMp3 = (id: string, waiting?: boolean): Mp3Response => {
  const [media, setMedia] = useState<HTMLMediaElement | null>(null);
  const [later, setLater] = useState(waiting);
  const [loading, setLoading] = useState<boolean>(false);
  const api = getApi();
  const { api_url } = useContext(DomainContext);
  const accessTokenInfo = useFiefAccessTokenInfo();
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
      token: accessTokenInfo?.access_token,
    });
  }, [navigator.serviceWorker, !serviceWorker, accessTokenInfo]);

  useEffect(() => {
    if (!id || !api || later) return;

    // createa a audio element and set the source
    setLoading(true);
    const audioElement = document.createElement("audio");
    audioElement.src = `${api_url}/v1/transcripts/${id}/audio/mp3`;
    audioElement.crossOrigin = "anonymous";
    audioElement.preload = "auto";
    setMedia(audioElement);
    setLoading(false);
  }, [id, api, later]);

  const getNow = () => {
    setLater(false);
  };

  return { media, loading, getNow };
};

export default useMp3;

import { useContext, useEffect, useState } from "react";
import { useError } from "../../(errors)/errorContext";
import { DomainContext } from "../domainContext";
import getApi from "../../lib/getApi";
import { useFiefAccessTokenInfo } from "@fief/fief/build/esm/nextjs/react";
import { shouldShowGet } from "../../lib/errorUtils";

type Mp3Response = {
  url: string | null;
  blob: Blob | null;
  loading: boolean;
  error: Error | null;
};

const useMp3 = (protectedPath: boolean, id: string): Mp3Response => {
  const [url, setUrl] = useState<string | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi(protectedPath);
  const { api_url } = useContext(DomainContext);
  const accessTokenInfo = useFiefAccessTokenInfo();

  const getMp3 = (id: string) => {
    if (!id || !api) return;

    setLoading(true);
    // XXX Current API interface does not output a blob, we need to to is manually
    // const requestParameters: V1TranscriptGetAudioMp3Request = {
    //   transcriptId: id,
    // };
    // api
    //   .v1TranscriptGetAudioMp3(requestParameters)
    //   .then((result) => {
    //     setUrl(result);
    //     setLoading(false);
    //     console.debug("Transcript Mp3 loaded:", result);
    //   })
    //   .catch((err) => {
    //     setError(err);
    //     setErrorState(err);
    //   });
    const localUrl = `${api_url}/v1/transcripts/${id}/audio/mp3`;
    if (localUrl == url) return;
    const headers = new Headers();

    if (accessTokenInfo) {
      headers.set("Authorization", "Bearer " + accessTokenInfo.access_token);
    }
    fetch(localUrl, {
      method: "GET",
      headers,
    })
      .then((response) => {
        setUrl(localUrl);
        response.blob().then((blob) => {
          setBlob(blob);
          setLoading(false);
        });
      })
      .catch((err) => {
        setErrorState(err);
        const shouldShowHuman = shouldShowGet(error);
        if (shouldShowHuman) {
          setError(err, "There was an error loading the audio");
        } else {
          setError(err);
        }
      });
  };

  useEffect(() => {
    getMp3(id);
  }, [id, api]);

  return { url, blob, loading, error };
};

export default useMp3;

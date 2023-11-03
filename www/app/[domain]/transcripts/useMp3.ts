import { useContext, useEffect, useState } from "react";
import {
  DefaultApi,
  // V1TranscriptGetAudioMp3Request,
} from "../../api/apis/DefaultApi";
import {} from "../../api";
import { useError } from "../../(errors)/errorContext";
import { DomainContext } from "../domainContext";

type Mp3Response = {
  url: string | null;
  blob: Blob | null;
  loading: boolean;
  error: Error | null;
};

const useMp3 = (api: DefaultApi, id: string): Mp3Response => {
  const [url, setUrl] = useState<string | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const { api_url } = useContext(DomainContext);

  const getMp3 = (id: string) => {
    if (!id) return;

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

    if (api.configuration.configuration.accessToken) {
      headers.set("Authorization", api.configuration.configuration.accessToken);
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
        setError(err);
        setErrorState(err);
      });
  };

  useEffect(() => {
    getMp3(id);
  }, [id]);

  return { url, blob, loading, error };
};

export default useMp3;

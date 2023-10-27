import { useEffect, useState } from "react";
import {
  DefaultApi,
  V1TranscriptGetAudioMp3Request,
} from "../../api/apis/DefaultApi";
import {} from "../../api";
import { useError } from "../../(errors)/errorContext";

type Mp3Response = {
  url: string | null;
  loading: boolean;
  error: Error | null;
};

const useMp3 = (api: DefaultApi, id: string): Mp3Response => {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();

  const getMp3 = (id: string) => {
    if (!id) throw new Error("Transcript ID is required to get transcript Mp3");

    setLoading(true);
    const requestParameters: V1TranscriptGetAudioMp3Request = {
      transcriptId: id,
    };
    api
      .v1TranscriptGetAudioMp3(requestParameters)
      .then((result) => {
        setUrl(result);
        setLoading(false);
        console.debug("Transcript Mp3 loaded:", result);
      })
      .catch((err) => {
        setError(err);
        setErrorState(err);
      });
  };

  useEffect(() => {
    getMp3(id);
  }, [id]);

  return { url, loading, error };
};

export default useMp3;

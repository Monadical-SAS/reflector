import { useEffect, useState } from "react";
import {
  DefaultApi,
  V1TranscriptGetAudioWaveformRequest,
} from "../../api/apis/DefaultApi";
import { AudioWaveform } from "../../api";
import { useError } from "../../(errors)/errorContext";
import getApi from "../../lib/getApi";
import { shouldShowError } from "../../lib/errorUtils";

type AudioWaveFormResponse = {
  waveform: AudioWaveform | null;
  loading: boolean;
  error: Error | null;
};

const useWaveform = (protectedPath, id: string): AudioWaveFormResponse => {
  const [waveform, setWaveform] = useState<AudioWaveform | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = getApi(protectedPath);

  useEffect(() => {
    if (!id || !api) return;
    console.log("hee");
    setLoading(true);
    const requestParameters: V1TranscriptGetAudioWaveformRequest = {
      transcriptId: id,
    };
    api
      .v1TranscriptGetAudioWaveform(requestParameters)
      .then((result) => {
        setWaveform(result);
        setLoading(false);
        console.debug("Transcript waveform loaded:", result);
      })
      .catch((err) => {
        setErrorState(err);
        const shouldShowHuman = shouldShowError(err);
        if (shouldShowHuman) {
          setError(err, "There was an error loading the waveform");
        } else {
          setError(err);
        }
      });
  }, [id, api]);

  return { waveform, loading, error };
};

export default useWaveform;

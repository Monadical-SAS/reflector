import { useEffect, useState } from "react";
import { AudioWaveform } from "../../api";
import { useError } from "../../(errors)/errorContext";
import useApi from "../../lib/useApi";
import { shouldShowError } from "../../lib/errorUtils";

type AudioWaveFormResponse = {
  waveform: AudioWaveform | null;
  loading: boolean;
  error: Error | null;
};

const useWaveform = (id: string, skip: boolean): AudioWaveFormResponse => {
  const [waveform, setWaveform] = useState<AudioWaveform | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();

  useEffect(() => {
    if (!id || !api || skip) {
      setLoading(false);
      setErrorState(null);
      setWaveform(null);
      return;
    }
    setLoading(true);
    setErrorState(null);
    api
      .v1TranscriptGetAudioWaveform({ transcriptId: id })
      .then((result) => {
        setWaveform(result);
        setLoading(false);
        console.debug("Transcript waveform loaded:", result);
      })
      .catch((err) => {
        setErrorState(err);
        setLoading(false);
      });
  }, [id, api, skip]);

  return { waveform, loading, error };
};

export default useWaveform;

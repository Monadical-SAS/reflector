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

const useWaveform = (id: string, waiting: boolean): AudioWaveFormResponse => {
  const [waveform, setWaveform] = useState<AudioWaveform | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();
  const api = useApi();

  useEffect(() => {
    if (!id || !api || waiting) return;
    setLoading(true);
    api
      .v1TranscriptGetAudioWaveform({ transcriptId: id })
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
  }, [id, !api, waiting]);

  return { waveform, loading, error };
};

export default useWaveform;

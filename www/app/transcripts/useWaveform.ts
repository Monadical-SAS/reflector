import { useEffect, useState } from "react";
import {
  DefaultApi,
  V1TranscriptGetAudioWaveformRequest,
} from "../api/apis/DefaultApi";
import { AudioWaveform } from "../api";
import { useError } from "../(errors)/errorContext";

type AudioWaveFormResponse = {
  waveform: AudioWaveform | null;
  loading: boolean;
  error: Error | null;
};

const useWaveform = (api: DefaultApi, id: string): AudioWaveFormResponse => {
  const [waveform, setWaveform] = useState<AudioWaveform | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setErrorState] = useState<Error | null>(null);
  const { setError } = useError();

  const getWaveform = (id: string) => {
    if (!id)
      throw new Error("Transcript ID is required to get transcript waveform");

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
        setError(err);
        setErrorState(err);
      });
  };

  useEffect(() => {
    getWaveform(id);
  }, [id]);

  return { waveform, loading, error };
};

export default useWaveform;

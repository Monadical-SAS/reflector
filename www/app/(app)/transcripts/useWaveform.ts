import { AudioWaveform } from "../../lib/api-types";
import { useTranscriptWaveform } from "../../lib/api-hooks";

type AudioWaveFormResponse = {
  waveform: AudioWaveform | null;
  loading: boolean;
  error: Error | null;
};

const useWaveform = (id: string, skip: boolean): AudioWaveFormResponse => {
  const {
    data: waveform,
    isLoading: loading,
    error,
  } = useTranscriptWaveform(skip ? null : id);

  return {
    waveform: waveform || null,
    loading,
    error: error as Error | null,
  };
};

export default useWaveform;

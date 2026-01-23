import type { components } from "../../reflector-api";
import { useTranscriptWaveform } from "../../lib/apiHooks";
import { parseMaybeNonEmptyString } from "../../lib/utils";

type AudioWaveform = components["schemas"]["AudioWaveform"];

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
  } = useTranscriptWaveform(skip ? null : parseMaybeNonEmptyString(id));

  return {
    waveform: waveform || null,
    loading,
    error: error as Error | null,
  };
};

export default useWaveform;

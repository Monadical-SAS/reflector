import type { components } from "../../reflector-api";
import { useTranscriptCreate } from "../../lib/apiHooks";

type CreateTranscript = components["schemas"]["CreateTranscript"];
type GetTranscriptWithParticipants =
  components["schemas"]["GetTranscriptWithParticipants"];

type UseCreateTranscript = {
  transcript: GetTranscriptWithParticipants | null;
  loading: boolean;
  error: Error | null;
  create: (transcriptCreationDetails: CreateTranscript) => Promise<void>;
};

const useCreateTranscript = (): UseCreateTranscript => {
  const createMutation = useTranscriptCreate();

  const create = async (transcriptCreationDetails: CreateTranscript) => {
    if (createMutation.isPending) return;

    await createMutation.mutateAsync({
      body: transcriptCreationDetails,
    });
  };

  return {
    transcript: createMutation.data || null,
    loading: createMutation.isPending,
    error: createMutation.error as Error | null,
    create,
  };
};

export default useCreateTranscript;

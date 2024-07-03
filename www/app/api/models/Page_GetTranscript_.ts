import type { GetTranscript } from "./GetTranscript";

export type Page_GetTranscript_ = {
  items: Array<GetTranscript>;
  total: number;
  page: number | null;
  size: number | null;
  pages?: number | null;
};

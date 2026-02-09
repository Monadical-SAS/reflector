export type DagTaskStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type DagTask = {
  name: string;
  status: DagTaskStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  parents: string[];
  error: string | null;
  children_total: number | null;
  children_completed: number | null;
  progress_pct: number | null;
};

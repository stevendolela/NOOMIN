export type Organization = { id: string; name: string; slug: string; role: string };
export type User = { id: string; email: string; full_name: string };
export type Session = { user: User; organizations: Organization[] };
export type Dataset = {
  id: string;
  name: string;
  original_filename: string;
  source_type: string;
  row_count: number;
  column_count: number;
  byte_size: number;
  columns: string[];
  created_at: string;
};
export type DatasetDetail = Dataset & { preview: Array<Record<string, string | null>> };

export type HistogramBin = { start: number; end: number; count: number };
export type ColumnProfile = { name: string; data_type: 'number' | 'text'; non_null_count: number; unique_count: number; minimum: number | null; maximum: number | null; average: number | null; distribution: HistogramBin[] };
export type DatasetProfile = { dataset_id: string; row_count: number; columns: ColumnProfile[] };
export type PipelineRun = { id: string; status: 'queued' | 'running' | 'succeeded' | 'failed'; output_dataset_id: string | null; error_message: string | null; created_at: string; started_at: string | null; finished_at: string | null };
export type Pipeline = { id: string; name: string; source_dataset_id: string; source_dataset_name: string; steps: Array<Record<string, unknown>>; created_at: string; last_run: PipelineRun | null };
export type SavedAnalysis = { id: string; title: string; dataset_id: string; dataset_name: string; column_profile: ColumnProfile; created_at: string };

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

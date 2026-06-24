export interface OrderExportTask {
  id: number
  site_id: number
  task_no: string
  filters: Record<string, any>
  file_format: 'csv' | 'xlsx'
  row_count?: number | null
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'expired'
  error_message?: string | null
  created_by: number
  completed_at?: string | null
  expires_at?: string | null
  created_at: string
  updated_at: string
}

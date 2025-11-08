-- Migration: Add processing status tracking to answer_analysis
-- Date: 2025-10-03
-- Purpose: Track real execution status of vectorization and DP updates

-- Add new columns for tracking processing status
ALTER TABLE selfology.answer_analysis
ADD COLUMN IF NOT EXISTS vectorization_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS vectorization_error TEXT,
ADD COLUMN IF NOT EXISTS vectorization_completed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS dp_update_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS dp_update_error TEXT,
ADD COLUMN IF NOT EXISTS dp_update_completed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS background_task_completed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS background_task_duration_ms INTEGER,
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_retry_at TIMESTAMP;

-- Add comments for documentation
COMMENT ON COLUMN selfology.answer_analysis.vectorization_status IS 'Status: pending, success, failed, skipped';
COMMENT ON COLUMN selfology.answer_analysis.vectorization_error IS 'Error message if vectorization failed';
COMMENT ON COLUMN selfology.answer_analysis.vectorization_completed_at IS 'Timestamp when vectorization completed';
COMMENT ON COLUMN selfology.answer_analysis.dp_update_status IS 'Status: pending, success, failed, skipped';
COMMENT ON COLUMN selfology.answer_analysis.dp_update_error IS 'Error message if DP update failed';
COMMENT ON COLUMN selfology.answer_analysis.dp_update_completed_at IS 'Timestamp when DP update completed';
COMMENT ON COLUMN selfology.answer_analysis.background_task_completed IS 'True if entire background task finished successfully';
COMMENT ON COLUMN selfology.answer_analysis.background_task_duration_ms IS 'Total duration of background task in milliseconds';
COMMENT ON COLUMN selfology.answer_analysis.retry_count IS 'Number of retry attempts made';
COMMENT ON COLUMN selfology.answer_analysis.last_retry_at IS 'Timestamp of last retry attempt';

-- Create index for monitoring queries (frequently query by status)
CREATE INDEX IF NOT EXISTS idx_answer_analysis_vectorization_status
ON selfology.answer_analysis(vectorization_status);

CREATE INDEX IF NOT EXISTS idx_answer_analysis_dp_update_status
ON selfology.answer_analysis(dp_update_status);

CREATE INDEX IF NOT EXISTS idx_answer_analysis_background_task_completed
ON selfology.answer_analysis(background_task_completed);

-- Update existing records to have 'success' status if they have data
UPDATE selfology.answer_analysis
SET
    vectorization_status = 'success',
    dp_update_status = 'success',
    background_task_completed = TRUE
WHERE
    processed_at IS NOT NULL
    AND vectorization_status = 'pending';

-- Create monitoring view for easy health checks
CREATE OR REPLACE VIEW selfology.processing_health_monitor AS
SELECT
    DATE_TRUNC('hour', processed_at) as hour,
    COUNT(*) as total_processed,
    COUNT(*) FILTER (WHERE vectorization_status = 'success') as vectorization_success,
    COUNT(*) FILTER (WHERE vectorization_status = 'failed') as vectorization_failed,
    COUNT(*) FILTER (WHERE dp_update_status = 'success') as dp_update_success,
    COUNT(*) FILTER (WHERE dp_update_status = 'failed') as dp_update_failed,
    COUNT(*) FILTER (WHERE background_task_completed = TRUE) as tasks_completed,
    AVG(background_task_duration_ms) as avg_duration_ms,
    MAX(background_task_duration_ms) as max_duration_ms,
    SUM(retry_count) as total_retries
FROM selfology.answer_analysis
WHERE processed_at > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', processed_at)
ORDER BY hour DESC;

COMMENT ON VIEW selfology.processing_health_monitor IS 'Hourly statistics of processing health for last 7 days';

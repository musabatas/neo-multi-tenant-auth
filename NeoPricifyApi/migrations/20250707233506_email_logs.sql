-- Create email logs table for comprehensive email tracking
CREATE TABLE IF NOT EXISTS email_logs (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Email identification
    message_id TEXT, -- Provider's message ID (e.g., AWS SES message ID)
    
    -- Sender information
    from_email TEXT NOT NULL,
    from_name TEXT,
    reply_to TEXT,
    
    -- Recipients (stored as JSONB arrays for flexibility)
    to_addresses JSONB NOT NULL DEFAULT '[]'::jsonb, -- Array of email addresses
    cc_addresses JSONB DEFAULT '[]'::jsonb,
    bcc_addresses JSONB DEFAULT '[]'::jsonb,
    
    -- Email content
    subject TEXT NOT NULL,
    body_text TEXT,
    body_html TEXT,
    
    -- Template information (for resending)
    template_id TEXT,
    template_data JSONB,
    template_version TEXT, -- Track template version for consistency
    
    -- Attachments metadata (for resending)
    attachments JSONB DEFAULT '[]'::jsonb, -- Array of {filename, size, content_type, storage_url}
    
    -- Email metadata
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
    headers JSONB, -- Custom headers
    metadata JSONB, -- Any additional metadata
    
    -- Provider information
    provider TEXT NOT NULL, -- smtp, sendgrid, ses, mailgun
    provider_config JSONB, -- Store provider settings used (excluding secrets)
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'queued', 'sending', 'sent', 'delivered', 'failed', 'bounced', 'complained')),
    
    -- Delivery information
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB, -- Detailed error information
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    last_retry_at TIMESTAMPTZ,
    
    -- Provider responses
    provider_response JSONB, -- Raw response from provider
    provider_events JSONB DEFAULT '[]'::jsonb, -- Array of webhook events
    
    -- Bounce/Complaint handling
    bounce_type TEXT, -- hard, soft, general, etc.
    bounce_subtype TEXT,
    bounce_message TEXT,
    complaint_type TEXT, -- abuse, auth-failure, fraud, etc.
    complaint_feedback_type TEXT,
    
    -- User association (optional)
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Request tracking
    request_id TEXT, -- Track which API request initiated this email
    ip_address INET, -- IP address of the requester
    user_agent TEXT, -- User agent of the requester
    
    -- Resend information
    is_resend BOOLEAN DEFAULT FALSE,
    original_email_id UUID REFERENCES email_logs(id) ON DELETE SET NULL,
    resent_count INT DEFAULT 0,
    resent_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    resent_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_email_logs_message_id ON email_logs(message_id) WHERE message_id IS NOT NULL;
CREATE INDEX idx_email_logs_from_email ON email_logs(from_email);
CREATE INDEX idx_email_logs_status ON email_logs(status);
CREATE INDEX idx_email_logs_user_id ON email_logs(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_email_logs_created_at ON email_logs(created_at DESC);
CREATE INDEX idx_email_logs_sent_at ON email_logs(sent_at DESC) WHERE sent_at IS NOT NULL;
CREATE INDEX idx_email_logs_failed_at ON email_logs(failed_at DESC) WHERE failed_at IS NOT NULL;
CREATE INDEX idx_email_logs_original_email_id ON email_logs(original_email_id) WHERE original_email_id IS NOT NULL;

-- Index for searching recipients (using GIN for JSONB)
CREATE INDEX idx_email_logs_to_addresses ON email_logs USING GIN (to_addresses);

-- Index for template searches
CREATE INDEX idx_email_logs_template_id ON email_logs(template_id) WHERE template_id IS NOT NULL;

-- Composite indexes for common queries
CREATE INDEX idx_email_logs_status_created ON email_logs(status, created_at DESC);
CREATE INDEX idx_email_logs_user_status ON email_logs(user_id, status) WHERE user_id IS NOT NULL;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_email_logs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER update_email_logs_timestamp
    BEFORE UPDATE ON email_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_email_logs_updated_at();

-- Function to search emails by recipient
CREATE OR REPLACE FUNCTION search_emails_by_recipient(recipient_email TEXT)
RETURNS SETOF email_logs AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM email_logs
    WHERE 
        to_addresses @> to_jsonb(ARRAY[recipient_email])
        OR cc_addresses @> to_jsonb(ARRAY[recipient_email])
        OR bcc_addresses @> to_jsonb(ARRAY[recipient_email])
    ORDER BY created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get email statistics
CREATE OR REPLACE FUNCTION get_email_statistics(
    start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
    end_date TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    total_emails BIGINT,
    sent_emails BIGINT,
    delivered_emails BIGINT,
    failed_emails BIGINT,
    bounced_emails BIGINT,
    complained_emails BIGINT,
    pending_emails BIGINT,
    resend_count BIGINT,
    unique_recipients BIGINT,
    avg_retry_count NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_emails,
        COUNT(*) FILTER (WHERE status = 'sent')::BIGINT as sent_emails,
        COUNT(*) FILTER (WHERE status = 'delivered')::BIGINT as delivered_emails,
        COUNT(*) FILTER (WHERE status = 'failed')::BIGINT as failed_emails,
        COUNT(*) FILTER (WHERE status = 'bounced')::BIGINT as bounced_emails,
        COUNT(*) FILTER (WHERE status = 'complained')::BIGINT as complained_emails,
        COUNT(*) FILTER (WHERE status IN ('pending', 'queued', 'sending'))::BIGINT as pending_emails,
        COUNT(*) FILTER (WHERE is_resend = TRUE)::BIGINT as resend_count,
        COUNT(DISTINCT jsonb_array_elements_text(to_addresses))::BIGINT as unique_recipients,
        AVG(retry_count)::NUMERIC(10,2) as avg_retry_count
    FROM email_logs
    WHERE created_at BETWEEN start_date AND end_date;
END;
$$ LANGUAGE plpgsql;

-- RLS Policies
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;

-- Admin users can see all email logs
CREATE POLICY "Admin users can view all email logs" ON email_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM auth_user_roles ur
            JOIN auth_roles r ON ur.role_id = r.id
            WHERE ur.user_id = auth.uid()
            AND r.name = 'admin'
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
        )
    );

-- Admin users can update email logs (for resending)
CREATE POLICY "Admin users can update email logs" ON email_logs
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM auth_user_roles ur
            JOIN auth_roles r ON ur.role_id = r.id
            WHERE ur.user_id = auth.uid()
            AND r.name = 'admin'
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
        )
    );

-- Service role can do everything (for backend operations)
CREATE POLICY "Service role has full access to email logs" ON email_logs
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- Users can see their own emails (optional - remove if not needed)
CREATE POLICY "Users can view their own email logs" ON email_logs
    FOR SELECT
    USING (auth.uid() = user_id);

-- Add comments for documentation
COMMENT ON TABLE email_logs IS 'Comprehensive email tracking table for all sent emails with resend capability';
COMMENT ON COLUMN email_logs.message_id IS 'Provider-specific message ID returned after sending';
COMMENT ON COLUMN email_logs.to_addresses IS 'Array of recipient email addresses stored as JSONB';
COMMENT ON COLUMN email_logs.template_data IS 'Template variables used for rendering, stored for resending';
COMMENT ON COLUMN email_logs.attachments IS 'Attachment metadata including storage URLs for resending';
COMMENT ON COLUMN email_logs.provider_config IS 'Provider configuration used (excluding sensitive data)';
COMMENT ON COLUMN email_logs.provider_events IS 'Webhook events from email provider (delivery, bounce, etc)';
COMMENT ON COLUMN email_logs.original_email_id IS 'Reference to original email if this is a resend';
COMMENT ON COLUMN email_logs.resent_count IS 'Number of times this email has been resent';
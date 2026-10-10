"""
Meeting Intelligence Domain Models.
Simulates enterprise data pipelines, meetings, transcripts, AI extractions, approvals, Asana tasks, and audit trails.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Client(models.Model):
    """Enterprise Account / Client profile with business context and health metrics."""
    TIER_CHOICES = [
        ('strategic', 'Strategic Account'),
        ('enterprise', 'Enterprise Tier'),
        ('growth', 'Growth Tier'),
    ]
    HEALTH_CHOICES = [
        ('healthy', 'Healthy (Low Risk)'),
        ('needs_attention', 'Needs Attention (Moderate Risk)'),
        ('at_risk', 'At Risk (High Churn Probability)'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    domain = models.CharField(max_length=150, help_text="e.g. acmehealth.io")
    industry = models.CharField(max_length=150)
    tier = models.CharField(max_length=30, choices=TIER_CHOICES, default='enterprise')
    arr = models.DecimalField(max_digits=12, decimal_places=2, help_text="Annual Recurring Revenue in USD")
    health_status = models.CharField(max_length=30, choices=HEALTH_CHOICES, default='healthy')
    health_score = models.IntegerField(default=90, help_text="Score from 0 to 100")
    account_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_clients')
    
    primary_contact_name = models.CharField(max_length=150)
    primary_contact_role = models.CharField(max_length=150)
    primary_contact_email = models.EmailField()
    
    relationship_summary = models.TextField(help_text="Key history, business drivers, and strategic context.")
    renewal_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (${self.arr:,.0f} ARR)"


class Meeting(models.Model):
    """Simulated Google Calendar event with scheduled attendees, agenda, and context."""
    MEETING_TYPE_CHOICES = [
        ('qbr', 'Quarterly Business Review (QBR)'),
        ('renewal', 'Executive Renewal & Contract Strategy'),
        ('technical_architecture', 'Technical & Security Architecture Sync'),
        ('discovery', 'Strategic Discovery & Solution Scoping'),
        ('weekly_sync', 'Weekly Project Governance Sync'),
        ('escalation', 'Executive Escalation & Root Cause Analysis'),
    ]
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='meetings')
    title = models.CharField(max_length=255)
    meeting_type = models.CharField(max_length=40, choices=MEETING_TYPE_CHOICES, default='weekly_sync')
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    location_url = models.CharField(max_length=255, default='https://meet.google.com/int-ai-conf', help_text="Mock Google Meet / Zoom link")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='scheduled')
    
    goals = models.JSONField(default=list, help_text="List of strategic objectives for this meeting")
    attendees = models.JSONField(default=list, help_text="List of attendee objects with name, email, role, and internal flag")
    simulated_calendar_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_start']

    def __str__(self):
        return f"{self.title} ({self.client.name})"

    @property
    def is_upcoming(self):
        return self.scheduled_start >= timezone.now()

    @property
    def has_briefing(self):
        return hasattr(self, 'briefing_pack') and self.briefing_pack is not None


class EmailMessage(models.Model):
    """Simulated Gmail workspace thread history for context ingestion."""
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('urgent', 'Urgent / Escalation'),
        ('concerning', 'Concerning / Risk Indicator'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='emails')
    meeting = models.ForeignKey(Meeting, on_delete=models.SET_NULL, null=True, blank=True, related_name='related_emails')
    sender_name = models.CharField(max_length=150)
    sender_email = models.EmailField()
    recipient_name = models.CharField(max_length=150)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField()
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, default='neutral')
    simulated_gmail_id = models.CharField(max_length=100, default=uuid.uuid4)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.subject} ({self.sender_name})"


class BriefingPack(models.Model):
    """AI-generated executive preparation dossier for an upcoming meeting."""
    STATUS_CHOICES = [
        ('ready', 'Ready'),
        ('generating', 'Generating Intelligence...'),
        ('failed', 'Generation Failed'),
    ]

    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name='briefing_pack')
    generated_at = models.DateTimeField(auto_now=True)
    ai_provider = models.CharField(max_length=50, default='mock')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ready')
    
    executive_summary = models.TextField(help_text="High-level briefing synthesis.")
    client_context = models.JSONField(default=dict, help_text="Industry, ARR, key historical milestones.")
    financial_snapshot = models.JSONField(default=dict, help_text="ARR, renewal date, expansion potential, risk factors.")
    relationship_health = models.JSONField(default=dict, help_text="Health score, sentiment, top concerns, champion info.")
    recent_communications = models.JSONField(default=list, help_text="Summary of recent simulated email touchpoints.")
    previous_meeting_takeaways = models.TextField(help_text="Synthesis of previous meeting outcomes.")
    pending_action_items = models.JSONField(default=list, help_text="Unresolved action items from prior calls.")
    strategic_talking_points = models.JSONField(default=list, help_text="Recommended talking points, tactical questions, and risks to deflect.")
    stakeholder_analysis = models.JSONField(default=list, help_text="Attendee dossiers, motivations, and champion vs blocker dynamics.")
    potential_risks_and_mitigations = models.JSONField(default=list, help_text="Anticipated risks and tactical mitigations.")
    
    raw_prompt = models.TextField(blank=True)
    raw_response = models.TextField(blank=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"Briefing Pack: {self.meeting.title}"


class MeetingTranscript(models.Model):
    """Raw meeting audio transcript or uploaded text/markdown/VTT."""
    FORMAT_CHOICES = [
        ('vtt', 'WebVTT (.vtt)'),
        ('md', 'Markdown (.md)'),
        ('txt', 'Plain Text (.txt)'),
        ('manual', 'Manual Entry'),
    ]
    STATUS_CHOICES = [
        ('unprocessed', 'Unprocessed'),
        ('processing', 'Processing with AI...'),
        ('processed', 'Processed'),
        ('failed', 'Processing Failed'),
    ]

    meeting = models.ForeignKey(Meeting, on_delete=models.SET_NULL, null=True, blank=True, related_name='transcripts')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='transcripts')
    title = models.CharField(max_length=255)
    source_filename = models.CharField(max_length=255, default='sample_transcript.txt')
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='txt')
    raw_content = models.TextField()
    word_count = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unprocessed')
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_format_display()})"

    def save(self, *args, **kwargs):
        if self.raw_content:
            self.word_count = len(self.raw_content.split())
        super().save(*args, **kwargs)


class MeetingSummaryRecord(models.Model):
    """High level summary and strategic decisions extracted from a processed transcript."""
    transcript = models.OneToOneField(MeetingTranscript, on_delete=models.CASCADE, related_name='summary_record')
    ai_provider = models.CharField(max_length=50, default='mock')
    executive_summary = models.TextField()
    key_decisions = models.JSONField(default=list, help_text="List of ratified decisions with rationale and context.")
    sentiment_overall = models.CharField(max_length=30, default='collaborative')
    raw_output_json = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary for {self.transcript.title}"


class AsanaProject(models.Model):
    """Simulated Asana project / board."""
    name = models.CharField(max_length=200)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='asana_projects')
    color_hex = models.CharField(max_length=20, default='#4F46E5')
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    simulated_asana_gid = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def open_tasks_count(self):
        return self.tasks.exclude(status='completed').count()


class AsanaTask(models.Model):
    """Simulated Asana task created upon human approval of extracted action items."""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('under_review', 'Under Review'),
        ('completed', 'Completed'),
    ]

    project = models.ForeignKey(AsanaProject, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignee_name = models.CharField(max_length=150, default='Unassigned')
    assignee_email = models.EmailField(blank=True)
    assignee_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_asana_tasks')
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    completed_at = models.DateTimeField(null=True, blank=True)
    
    source_meeting = models.ForeignKey(Meeting, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tasks')
    simulated_asana_gid = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.project.name}] {self.title} ({self.status})"

    @property
    def is_overdue(self):
        if self.status != 'completed' and self.due_date:
            return self.due_date < timezone.now().date()
        return False


class ExtractedActionItem(models.Model):
    """
    Action item proposed by AI extraction from transcript.
    Requires explicit human approval before creating a live Asana task.
    """
    CONFIDENCE_LEVELS = [
        ('high', 'High (Explicit Commitment)'),
        ('medium', 'Medium (Probable Obligation)'),
        ('low', 'Low (Inferred Suggestion)'),
    ]
    STATUS_CHOICES = [
        ('pending_review', 'Pending Human Review'),
        ('approved', 'Approved & Task Created'),
        ('rejected', 'Rejected'),
        ('modified', 'Modified & Approved'),
    ]
    URGENCY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    transcript = models.ForeignKey(MeetingTranscript, on_delete=models.CASCADE, related_name='extracted_actions')
    meeting = models.ForeignKey(Meeting, on_delete=models.SET_NULL, null=True, blank=True, related_name='extracted_actions')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='extracted_actions')
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    proposed_owner_name = models.CharField(max_length=150, help_text="Owner suggested by AI or detected in transcript")
    proposed_owner_email = models.CharField(max_length=150, blank=True)
    proposed_due_date = models.DateField(null=True, blank=True, help_text="Date mentioned in transcript or inferred")
    
    confidence_score = models.FloatField(default=0.85, help_text="0.0 to 1.0 confidence")
    confidence_level = models.CharField(max_length=20, choices=CONFIDENCE_LEVELS, default='medium')
    is_inferred = models.BooleanField(
        default=False, 
        help_text="True if deadline/owner was inferred from context rather than factually stated."
    )
    transcript_quote = models.TextField(
        help_text="Exact excerpt from transcript supporting this extraction."
    )
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='medium')
    suggested_project_name = models.CharField(max_length=200, default='Client Deliverables')
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_review')
    rejection_reason = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_actions')
    
    # Linked task after approval
    asana_task = models.OneToOneField(AsanaTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_action')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', '-created_at']

    @property
    def confidence_percent(self):
        return int(round(self.confidence_score * 100))

    def __str__(self):
        return f"{self.title} - [{self.status}]"


class AsanaComment(models.Model):
    """Simulated discussion / update comments on an Asana task."""
    task = models.ForeignKey(AsanaTask, on_delete=models.CASCADE, related_name='comments')
    author_name = models.CharField(max_length=150)
    author_email = models.EmailField(blank=True)
    author_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comment_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author_name} on {self.task.title}"


class WeeklyReport(models.Model):
    """Generated weekly accountability and overdue action digest."""
    period_label = models.CharField(max_length=150)
    generated_at = models.DateTimeField(auto_now_add=True)
    period_start = models.DateField()
    period_end = models.DateField()
    
    total_actions_tracked = models.IntegerField(default=0)
    overdue_actions_count = models.IntegerField(default=0)
    upcoming_deadlines_count = models.IntegerField(default=0)
    completed_this_period_count = models.IntegerField(default=0)
    unresolved_decisions_count = models.IntegerField(default=0)
    
    report_markdown = models.TextField()
    report_html = models.TextField()
    report_data = models.JSONField(default=dict)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"Weekly Report: {self.period_label}"


class EmailDeliveryLog(models.Model):
    """Simulated outbound SMTP delivery ledger."""
    TYPE_CHOICES = [
        ('weekly_report', 'Weekly Overdue & Accountability Digest'),
        ('briefing_pack', 'Executive Meeting Briefing Pack'),
        ('action_approval_summary', 'Action Items Approved Notification'),
        ('task_assignment', 'Asana Task Assignment Alert'),
    ]

    email_type = models.CharField(max_length=40, choices=TYPE_CHOICES, default='weekly_report')
    recipient_emails = models.CharField(max_length=500)
    recipient_count = models.IntegerField(default=1)
    subject = models.CharField(max_length=255)
    body_preview = models.TextField()
    full_body_html = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    simulated_status = models.CharField(max_length=30, default='delivered')
    smtp_message_id = models.CharField(max_length=100, default=uuid.uuid4)
    smtp_response = models.CharField(max_length=255, default='250 2.0.0 OK: queued as 4FA901CB-SIMULATED-SMTP')

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Email: {self.subject} -> {self.recipient_emails}"


class IntegrationSyncStatus(models.Model):
    """Simulated integration connection metadata and live status."""
    service_key = models.CharField(max_length=50, unique=True)
    service_title = models.CharField(max_length=100)
    is_connected = models.BooleanField(default=True)
    is_simulated = models.BooleanField(default=True)
    last_sync_time = models.DateTimeField(default=timezone.now)
    status_label = models.CharField(max_length=50, default='Operational (Simulated)')
    synced_items_count = models.IntegerField(default=0)
    sync_details = models.JSONField(default=dict)

    class Meta:
        ordering = ['service_title']

    def __str__(self):
        return f"{self.service_title} ({self.status_label})"


class AuditLogEvent(models.Model):
    """Immutable audit trail of all AI operations, reviews, and sync actions."""
    EVENT_TYPES = [
        ('briefing_generated', 'Meeting Briefing Generated'),
        ('transcript_uploaded', 'Transcript Uploaded'),
        ('transcript_processed', 'Transcript Processed with AI'),
        ('action_approved', 'Action Item Approved'),
        ('action_rejected', 'Action Item Rejected'),
        ('action_modified', 'Action Item Modified & Approved'),
        ('task_created', 'Asana Task Created'),
        ('task_updated', 'Asana Task Updated'),
        ('task_completed', 'Asana Task Marked Complete'),
        ('report_generated', 'Weekly Overdue Report Generated'),
        ('email_dispatched', 'Simulated Email Sent'),
        ('demo_reseeded', 'Demo Data Environment Reseeded'),
    ]

    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    actor_name = models.CharField(max_length=150, default='System / AI Agent')
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    meeting = models.ForeignKey(Meeting, on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.event_type}] {self.title} @ {self.created_at.strftime('%Y-%m-%d %H:%M')}"

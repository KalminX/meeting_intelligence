"""
Automated Test Suite for Meeting Intelligence.
Tests Briefing Generation, Transcript Extraction, Human Approval Gates,
Asana Task Generation, Idempotency, Overdue Reporting, and Mock Integrations.
Runs completely offline without external network or API keys.
"""

from datetime import timedelta
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from intelligence.models import (
    Client, Meeting, EmailMessage, BriefingPack, MeetingTranscript,
    MeetingSummaryRecord, ExtractedActionItem, AsanaProject, AsanaTask,
    AsanaComment, WeeklyReport, EmailDeliveryLog, IntegrationSyncStatus,
    AuditLogEvent
)
from intelligence.services.ai_client import DeterministicMockAI, AIService, BriefingPackSchema, TranscriptExtractionSchema
from intelligence.services.briefing_service import BriefingService
from intelligence.services.transcript_service import TranscriptService
from intelligence.services.task_service import TaskService
from intelligence.services.report_service import ReportService
from intelligence.services.integration_service import IntegrationService
from intelligence.services.seed_service import SeedService


class TestMeetingIntelligenceCore(TestCase):

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='test_reviewer',
            email='reviewer@test.demo',
            password='password123',
            first_name='Alex',
            last_name='Reviewer'
        )

        # Create client
        self.client_obj = Client.objects.create(
            name='Apex Cloud Solutions',
            slug='apex-cloud',
            domain='apexcloud.io',
            industry='Enterprise Cloud Infrastructure',
            tier='strategic',
            arr=500000.00,
            health_status='healthy',
            health_score=92,
            account_manager=self.user,
            primary_contact_name='Dr. Helen Cho',
            primary_contact_role='CTO',
            primary_contact_email='h.cho@apexcloud.io',
            relationship_summary='Multi-year flagship customer. Scaling cloud nodes across 4 continents.'
        )

        # Create scheduled meeting
        self.meeting = Meeting.objects.create(
            client=self.client_obj,
            title='Apex Cloud — Q4 Architecture & Renewal Strategy',
            meeting_type='qbr',
            scheduled_start=timezone.now() + timedelta(days=2),
            scheduled_end=timezone.now() + timedelta(days=2, hours=1),
            location_url='https://meet.google.com/test-apex',
            status='scheduled',
            goals=['Review throughput benchmarks', 'Discuss 24-month renewal terms'],
            attendees=[
                {'name': 'Alex Reviewer', 'email': 'reviewer@test.demo', 'role': 'Lead AE', 'is_internal': True},
                {'name': 'Dr. Helen Cho', 'email': 'h.cho@apexcloud.io', 'role': 'CTO', 'is_internal': False},
            ],
            simulated_calendar_id='gcal_test_001'
        )

        # Create sample email
        self.email = EmailMessage.objects.create(
            client=self.client_obj,
            meeting=self.meeting,
            sender_name='Dr. Helen Cho',
            sender_email='h.cho@apexcloud.io',
            recipient_name='Alex Reviewer',
            recipient_email='reviewer@test.demo',
            subject='Preparation for Q4 Architecture Review',
            body='Looking forward to reviewing our cluster throughput and renewal pricing.',
            sent_at=timezone.now() - timedelta(days=1),
            sentiment='positive'
        )

        self.http_client = TestClient()

    # ==========================================
    # 1. AI Schema Validation & Mock Engine Tests
    # ==========================================

    def test_mock_ai_briefing_schema_validation(self):
        """Validates that DeterministicMockAI generates valid BriefingPackSchema instances."""
        meeting_data = {
            'client_name': self.client_obj.name,
            'meeting_title': self.meeting.title,
            'arr': '$500,000',
            'health_status': 'Healthy',
            'renewal_date': '2027-01-15'
        }
        result = DeterministicMockAI.generate_briefing(meeting_data)
        self.assertIsInstance(result, BriefingPackSchema)
        self.assertTrue(len(result.executive_summary) > 20)
        self.assertTrue(len(result.strategic_talking_points) >= 2)
        self.assertTrue(len(result.stakeholder_analysis) >= 2)

    def test_mock_ai_transcript_schema_validation(self):
        """Validates that DeterministicMockAI extracts schema-compliant actions and decisions."""
        transcript_text = """
        Sarah Lin: Thanks everyone for joining our Acme HealthTech Q4 Strategy Review.
        Dr. Marcus Vance: We want to expand by 150 seats for EMEA.
        Sarah Lin: I will prepare the revised order form for the 150 seat tier and send it to procurement by Monday.
        Claire Dupont: We must ensure GDPR clauses are updated.
        """
        extraction = DeterministicMockAI.extract_from_transcript(transcript_text, client_name='Acme')
        self.assertIsInstance(extraction, TranscriptExtractionSchema)
        self.assertTrue(len(extraction.action_items) >= 2)
        self.assertTrue(len(extraction.key_decisions) >= 1)

        # Check action item schema compliance
        action = extraction.action_items[0]
        self.assertTrue(hasattr(action, 'transcript_quote'))
        self.assertTrue(hasattr(action, 'confidence_score'))
        self.assertTrue(0.0 <= action.confidence_score <= 1.0)
        self.assertIn(action.confidence_level, ['high', 'medium', 'low'])

    # ==========================================
    # 2. Briefing Generation & Idempotency Tests
    # ==========================================

    def test_briefing_service_generation_and_idempotency(self):
        """Tests generating a BriefingPack and verifying that re-calling without force_refresh is idempotent."""
        briefing1 = BriefingService.generate_briefing_for_meeting(
            meeting=self.meeting,
            user=self.user,
            force_refresh=False,
            force_mock=True
        )
        self.assertIsNotNone(briefing1)
        self.assertEqual(briefing1.meeting, self.meeting)
        self.assertEqual(BriefingPack.objects.filter(meeting=self.meeting).count(), 1)

        # Re-call without refresh: should return same object without recreating
        briefing2 = BriefingService.generate_briefing_for_meeting(
            meeting=self.meeting,
            user=self.user,
            force_refresh=False,
            force_mock=True
        )
        self.assertEqual(briefing1.id, briefing2.id)
        self.assertEqual(BriefingPack.objects.filter(meeting=self.meeting).count(), 1)

        # Check Audit Log was recorded
        audit = AuditLogEvent.objects.filter(event_type='briefing_generated', meeting=self.meeting).first()
        self.assertIsNotNone(audit)

    # ==========================================
    # 3. Transcript Processing & VTT Cleaning Tests
    # ==========================================

    def test_vtt_cleaner(self):
        """Tests that WebVTT timestamp headers are stripped accurately."""
        vtt_sample = """WEBVTT
00:00:01.000 --> 00:00:04.000
Speaker 1: Hello team.
00:00:05.000 --> 00:00:09.000
Speaker 2: Let us begin the review.
"""
        clean = TranscriptService.clean_vtt_content(vtt_sample)
        self.assertNotIn("WEBVTT", clean)
        self.assertNotIn("-->", clean)
        self.assertIn("Speaker 1: Hello team.", clean)
        self.assertIn("Speaker 2: Let us begin the review.", clean)

    def test_transcript_processing_workflow(self):
        """Tests processing a transcript into decisions and pending review action items."""
        transcript = MeetingTranscript.objects.create(
            meeting=self.meeting,
            client=self.client_obj,
            title='Apex Cloud Architecture Sync',
            source_filename='apex_sync.txt',
            format='txt',
            raw_content="""Alex: We investigated the latency issue.
Helen: Please deliver the synthetic benchmark latency report by Friday.
Alex: I will run the synthetic benchmark tests tomorrow morning and send over the report by Friday.""",
            duration_minutes=30
        )

        TranscriptService.process_transcript(transcript, user=self.user, force_mock=True)

        transcript.refresh_from_db()
        self.assertEqual(transcript.status, 'processed')
        self.assertIsNotNone(transcript.summary_record)
        self.assertTrue(transcript.extracted_actions.count() > 0)

        # All newly extracted items must be 'pending_review' initially
        for action in transcript.extracted_actions.all():
            self.assertEqual(action.status, 'pending_review')
            self.assertIsNone(action.asana_task)  # No task created before human approval!
            self.assertTrue(len(action.transcript_quote) > 0)

    # ==========================================
    # 4. Human Approval & Task Creation Tests
    # ==========================================

    def test_action_item_approval_creates_asana_task(self):
        """Tests that human approval transitions status and creates an Asana task."""
        transcript = MeetingTranscript.objects.create(
            meeting=self.meeting,
            client=self.client_obj,
            title='Apex Cloud Sync',
            source_filename='apex.txt',
            raw_content='Test transcript',
            status='processed'
        )

        action = ExtractedActionItem.objects.create(
            transcript=transcript,
            meeting=self.meeting,
            client=self.client_obj,
            title='Deliver finalized benchmark report',
            description='Export Grafana latency dashboard to PDF.',
            proposed_owner_name='Alex Reviewer',
            proposed_owner_email='reviewer@test.demo',
            proposed_due_date=timezone.now().date() + timedelta(days=3),
            confidence_score=0.95,
            confidence_level='high',
            is_inferred=False,
            transcript_quote='\"Alex: I will send over the full report by Friday.\"',
            urgency='high',
            suggested_project_name='Cloud Architecture & Benchmarks',
            status='pending_review'
        )

        task = TaskService.approve_action_item(action, user=self.user)

        action.refresh_from_db()
        self.assertEqual(action.status, 'approved')
        self.assertIsNotNone(action.asana_task)
        self.assertEqual(task.title, action.title)
        self.assertEqual(task.project.name, 'Cloud Architecture & Benchmarks')
        self.assertEqual(task.assignee_name, 'Alex Reviewer')
        self.assertEqual(task.comments.count(), 1)  # Initial audit comment

        # Idempotency check: Approving again should not duplicate the task
        task2 = TaskService.approve_action_item(action, user=self.user)
        self.assertEqual(task.id, task2.id)
        self.assertEqual(AsanaTask.objects.filter(title='Deliver finalized benchmark report').count(), 1)

    def test_action_item_modification_and_approval(self):
        """Tests editing proposed owner and deadline during approval."""
        transcript = MeetingTranscript.objects.create(
            meeting=self.meeting,
            client=self.client_obj,
            title='Apex Cloud Sync',
            source_filename='apex.txt',
            raw_content='Test transcript',
            status='processed'
        )

        action = ExtractedActionItem.objects.create(
            transcript=transcript,
            meeting=self.meeting,
            client=self.client_obj,
            title='Initial generic title',
            proposed_owner_name='Unassigned',
            confidence_score=0.70,
            confidence_level='low',
            is_inferred=True,
            transcript_quote='\"Someone should look into this.\"',
            urgency='medium',
            status='pending_review'
        )

        new_due = timezone.now().date() + timedelta(days=7)
        modifications = {
            'title': 'Investigate Redis queue throughput bottlenecks',
            'description': 'Profile latency with 5000 concurrent consumers.',
            'proposed_owner_name': 'David Miller',
            'proposed_owner_email': 'david.miller@meetingintel.demo',
            'proposed_due_date': new_due,
            'urgency': 'high',
            'suggested_project_name': 'Platform Infrastructure & SLAs'
        }

        task = TaskService.approve_action_item(action, user=self.user, modifications=modifications)

        action.refresh_from_db()
        self.assertEqual(action.status, 'modified')
        self.assertEqual(action.title, 'Investigate Redis queue throughput bottlenecks')
        self.assertEqual(action.proposed_owner_name, 'David Miller')
        self.assertEqual(task.title, 'Investigate Redis queue throughput bottlenecks')
        self.assertEqual(task.due_date, new_due)

    def test_action_item_rejection(self):
        """Tests that rejecting an action item sets rejection status and does not create an Asana task."""
        transcript = MeetingTranscript.objects.create(
            meeting=self.meeting,
            client=self.client_obj,
            title='Apex Cloud Sync',
            source_filename='apex.txt',
            raw_content='Test transcript',
            status='processed'
        )

        action = ExtractedActionItem.objects.create(
            transcript=transcript,
            meeting=self.meeting,
            client=self.client_obj,
            title='Out of scope suggestion',
            proposed_owner_name='Helen Cho',
            confidence_score=0.50,
            confidence_level='low',
            is_inferred=True,
            transcript_quote='\"Maybe we do this next year.\"',
            status='pending_review'
        )

        TaskService.reject_action_item(action, reason='Out of scope for current quarter.', user=self.user)

        action.refresh_from_db()
        self.assertEqual(action.status, 'rejected')
        self.assertEqual(action.rejection_reason, 'Out of scope for current quarter.')
        self.assertIsNone(action.asana_task)
        self.assertEqual(AsanaTask.objects.filter(title='Out of scope suggestion').count(), 0)

    # ==========================================
    # 5. Weekly Overdue Report & Email Dispatch
    # ==========================================

    def test_weekly_overdue_report_generation(self):
        """Tests calculating overdue tasks, compiling report markdown, and simulated dispatch."""
        project = AsanaProject.objects.create(name='Test Project', client=self.client_obj)

        # Create an overdue task
        yesterday = timezone.now().date() - timedelta(days=2)
        overdue_task = AsanaTask.objects.create(
            project=project,
            title='Overdue security audit deliverable',
            assignee_name='Alex Reviewer',
            due_date=yesterday,
            priority='urgent',
            status='in_progress'
        )

        # Create an upcoming task
        next_week = timezone.now().date() + timedelta(days=3)
        upcoming_task = AsanaTask.objects.create(
            project=project,
            title='Upcoming Q4 renewal order form',
            assignee_name='Alex Reviewer',
            due_date=next_week,
            priority='high',
            status='todo'
        )

        report = ReportService.generate_weekly_report(user=self.user)
        self.assertIsNotNone(report)
        self.assertEqual(report.overdue_actions_count, 1)
        self.assertEqual(report.upcoming_deadlines_count, 1)
        self.assertIn("Overdue security audit deliverable", report.report_markdown)

        # Simulate Email Dispatch
        delivery = ReportService.simulate_dispatch_email(
            report=report,
            recipient_emails="executive-team@test.demo, cto@apexcloud.io",
            user=self.user
        )
        self.assertEqual(delivery.simulated_status, 'delivered')
        self.assertEqual(delivery.recipient_count, 2)
        self.assertIn("250 2.0.0 OK", delivery.smtp_response)

    # ==========================================
    # 6. Simulated Integrations & Sync Status
    # ==========================================

    def test_mock_integrations_sync(self):
        """Tests that simulated integrations sync correctly update timestamps and metrics."""
        IntegrationService.ensure_initial_statuses()
        status = IntegrationSyncStatus.objects.get(service_key='google_calendar')
        self.assertTrue(status.is_simulated)
        self.assertTrue(status.is_connected)

        updated_status = IntegrationService.simulate_sync('google_calendar', user=self.user)
        self.assertEqual(updated_status.service_key, 'google_calendar')

        audit = AuditLogEvent.objects.filter(event_type='demo_reseeded', metadata__service_key='google_calendar').first()
        self.assertIsNotNone(audit)

    # ==========================================
    # 7. Seed Service Full Reseed Verification
    # ==========================================

    def test_seed_service_reseed(self):
        """Tests that full demo database reseeding completes cleanly with all mock objects."""
        result = SeedService.reseed_all_demo_data()
        self.assertEqual(result['clients_created'], 4)
        self.assertEqual(result['meetings_created'], 3)
        self.assertEqual(result['tasks_created'], 4)
        self.assertTrue(Client.objects.filter(slug='acme-healthtech').exists())
        self.assertTrue(Meeting.objects.filter(simulated_calendar_id='gcal_ev_acme_qbr_2026').exists())

    # ==========================================
    # 8. Web Views & Endpoints Smoke Tests
    # ==========================================

    def test_all_views_return_ok(self):
        """Tests that all core views render with HTTP 200/302."""
        # Reseed first to have rich data
        SeedService.reseed_all_demo_data()
        meeting = Meeting.objects.first()
        transcript = MeetingTranscript.objects.first()
        action = ExtractedActionItem.objects.first()

        # Dashboard
        resp = self.http_client.get(reverse('intelligence:dashboard'))
        self.assertEqual(resp.status_code, 200)

        # Calendar
        resp = self.http_client.get(reverse('intelligence:calendar'))
        self.assertEqual(resp.status_code, 200)

        # Meeting Detail & Briefing
        resp = self.http_client.get(reverse('intelligence:meeting_detail', args=[meeting.id]))
        self.assertEqual(resp.status_code, 200)

        resp = self.http_client.get(reverse('intelligence:meeting_briefing', args=[meeting.id]))
        self.assertEqual(resp.status_code, 200)

        # Transcript List & Detail
        resp = self.http_client.get(reverse('intelligence:transcript_list'))
        self.assertEqual(resp.status_code, 200)

        resp = self.http_client.get(reverse('intelligence:transcript_detail', args=[transcript.id]))
        self.assertEqual(resp.status_code, 200)

        # Approval Queue
        resp = self.http_client.get(reverse('intelligence:approval_queue'))
        self.assertEqual(resp.status_code, 200)

        # Asana Tasks (List & Board)
        resp = self.http_client.get(reverse('intelligence:task_list'))
        self.assertEqual(resp.status_code, 200)

        resp = self.http_client.get(reverse('intelligence:task_list') + '?view=board')
        self.assertEqual(resp.status_code, 200)

        # Weekly Report
        resp = self.http_client.get(reverse('intelligence:weekly_report'))
        self.assertEqual(resp.status_code, 200)

        # Integrations
        resp = self.http_client.get(reverse('intelligence:integrations'))
        self.assertEqual(resp.status_code, 200)

        # Audit Trail
        resp = self.http_client.get(reverse('intelligence:audit_trail'))
        self.assertEqual(resp.status_code, 200)

        # Demo Controls
        resp = self.http_client.get(reverse('intelligence:demo_controls'))
        self.assertEqual(resp.status_code, 200)

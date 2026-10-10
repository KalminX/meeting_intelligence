"""
Demo Data Seeding Service.
Populates realistic fictional enterprise clients, team members, meetings, emails, transcripts,
Asana boards, and audit history.
"""

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from ..models import (
    Client, Meeting, EmailMessage, MeetingTranscript, AsanaProject, AsanaTask,
    AsanaComment, AuditLogEvent, EmailDeliveryLog, IntegrationSyncStatus
)
from .briefing_service import BriefingService
from .transcript_service import TranscriptService
from .integration_service import IntegrationService


class SeedService:

    @classmethod
    def reseed_all_demo_data(cls) -> dict:
        """
        Clears existing intelligence demo records and recreates the full realistic enterprise state.
        """
        # 1. Clear existing application data (except superusers if any)
        MeetingTranscript.objects.all().delete()
        Meeting.objects.all().delete()
        EmailMessage.objects.all().delete()
        AsanaTask.objects.all().delete()
        AsanaProject.objects.all().delete()
        Client.objects.all().delete()
        AuditLogEvent.objects.all().delete()
        EmailDeliveryLog.objects.all().delete()
        IntegrationSyncStatus.objects.all().delete()

        now = timezone.now()
        today = now.date()

        # 2. Ensure standard Demo Users
        demo_user, _ = User.objects.get_or_create(
            username='demo',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Lin',
                'email': 'sarah.lin@meetingintel.demo',
                'is_staff': True,
                'is_active': True,
            }
        )
        demo_user.set_password('demo1234')
        demo_user.save()

        david_user, _ = User.objects.get_or_create(
            username='david.miller',
            defaults={
                'first_name': 'David',
                'last_name': 'Miller',
                'email': 'david.miller@meetingintel.demo',
                'is_staff': True,
                'is_active': True,
            }
        )
        david_user.set_password('demo1234')
        david_user.save()

        alex_user, _ = User.objects.get_or_create(
            username='alex.chen',
            defaults={
                'first_name': 'Alex',
                'last_name': 'Chen',
                'email': 'alex.chen@meetingintel.demo',
                'is_staff': True,
                'is_active': True,
            }
        )
        alex_user.set_password('demo1234')
        alex_user.save()

        # 3. Create Enterprise Clients
        acme = Client.objects.create(
            name='Acme HealthTech',
            slug='acme-healthtech',
            domain='acmehealth.io',
            industry='Healthcare SaaS & Telehealth',
            tier='strategic',
            arr=480000.00,
            health_status='healthy',
            health_score=94,
            account_manager=demo_user,
            primary_contact_name='Dr. Marcus Vance',
            primary_contact_role='VP of Engineering & Clinical Systems',
            primary_contact_email='marcus.vance@acmehealth.io',
            relationship_summary=(
                'Strategic partner since 2024. Processing over 18M patient records monthly. '
                'Strong alignment on HIPAA compliance and high availability. Currently expanding platform '
                'adoption to European telehealth business unit.'
            ),
            renewal_date=today + timedelta(days=120)
        )

        meridian = Client.objects.create(
            name='Meridian Logistics',
            slug='meridian-logistics',
            domain='meridianlogistics.net',
            industry='Global Freight & Fleet Telematics',
            tier='enterprise',
            arr=320000.00,
            health_status='needs_attention',
            health_score=76,
            account_manager=demo_user,
            primary_contact_name='Elena Rostova',
            primary_contact_role='Director of Platform Architecture',
            primary_contact_email='elena.rostova@meridianlogistics.net',
            relationship_summary=(
                'Enterprise customer for 18 months. Experiencing rapid fleet telemetry surge. '
                'Recent concerns regarding webhook timeout latency during 8 AM peak dispatch windows. '
                'Needs SLA reassurance before signing 3-year extension.'
            ),
            renewal_date=today + timedelta(days=45)
        )

        aura = Client.objects.create(
            name='Aura Fintech',
            slug='aura-fintech',
            domain='aurapayments.com',
            industry='Financial Infrastructure & Payments',
            tier='strategic',
            arr=640000.00,
            health_status='healthy',
            health_score=98,
            account_manager=demo_user,
            primary_contact_name='Julian Scott',
            primary_contact_role='Chief Information Security Officer',
            primary_contact_email='j.scott@aurapayments.com',
            relationship_summary=(
                'Flagship financial client. Requires SOC2 Type II compliance attestation and zero-trust '
                'multi-region database replication. Highly satisfied with current system stability.'
            ),
            renewal_date=today + timedelta(days=180)
        )

        zenith = Client.objects.create(
            name='Zenith Retail',
            slug='zenith-retail',
            domain='zenithretail.com',
            industry='Omnichannel Retail & E-Commerce',
            tier='growth',
            arr=195000.00,
            health_status='at_risk',
            health_score=62,
            account_manager=demo_user,
            primary_contact_name='Rachel Green',
            primary_contact_role='Head of Omnichannel Experience',
            primary_contact_email='rachel.green@zenithretail.com',
            relationship_summary=(
                'Growth tier client preparing for Black Friday traffic surge. Needs tailored developer '
                'enablement training and customized API throttling configurations.'
            ),
            renewal_date=today + timedelta(days=30)
        )

        # 4. Create Simulated Calendar Meetings
        m1_start = now.replace(minute=0, second=0) + timedelta(days=1, hours=4)
        m1 = Meeting.objects.create(
            client=acme,
            title='Acme HealthTech — Q4 Strategic Review & International Expansion',
            meeting_type='qbr',
            scheduled_start=m1_start,
            scheduled_end=m1_start + timedelta(minutes=45),
            location_url='https://meet.google.com/int-acme-qbr',
            status='scheduled',
            goals=[
                'Review Q3 platform adoption and 99.99% uptime achievement',
                'Present European multi-region architecture proposal',
                'Align on 150 additional user seat expansion for EMEA rollout',
                'Address updated Data Privacy Framework (DPA) requirements'
            ],
            attendees=[
                {'name': 'Sarah Lin', 'email': 'sarah.lin@meetingintel.demo', 'role': 'Principal Account Executive', 'is_internal': True},
                {'name': 'David Miller', 'email': 'david.miller@meetingintel.demo', 'role': 'Lead Solutions Architect', 'is_internal': True},
                {'name': 'Dr. Marcus Vance', 'email': 'marcus.vance@acmehealth.io', 'role': 'VP of Engineering', 'is_internal': False},
                {'name': 'Claire Dupont', 'email': 'claire.dupont@acmehealth.io', 'role': 'Head of European Operations', 'is_internal': False},
            ],
            simulated_calendar_id='gcal_ev_acme_qbr_2026'
        )

        m2_start = now.replace(minute=0, second=0) + timedelta(days=3, hours=2)
        m2 = Meeting.objects.create(
            client=meridian,
            title='Meridian Logistics — High-Throughput Webhook SLA & Latency Sync',
            meeting_type='technical_architecture',
            scheduled_start=m2_start,
            scheduled_end=m2_start + timedelta(minutes=60),
            location_url='https://meet.google.com/int-meridian-arch',
            status='scheduled',
            goals=[
                'Present p95/p99 synthetic load test benchmarks',
                'Demonstrate exponential backoff retry queue mechanism',
                'Agree on staging load test sign-off milestone before Q4 peak'
            ],
            attendees=[
                {'name': 'Sarah Lin', 'email': 'sarah.lin@meetingintel.demo', 'role': 'Principal Account Executive', 'is_internal': True},
                {'name': 'David Miller', 'email': 'david.miller@meetingintel.demo', 'role': 'Lead Solutions Architect', 'is_internal': True},
                {'name': 'Elena Rostova', 'email': 'elena.rostova@meridianlogistics.net', 'role': 'Director of Architecture', 'is_internal': False},
                {'name': 'Tomas Kovacs', 'email': 'tomas.kovacs@meridianlogistics.net', 'role': 'Lead DevOps Engineer', 'is_internal': False},
            ],
            simulated_calendar_id='gcal_ev_meridian_tech_2026'
        )

        m3_start = now.replace(minute=0, second=0) - timedelta(days=2, hours=3)
        m3 = Meeting.objects.create(
            client=aura,
            title='Aura Fintech — Executive Security Review & SOC2 Governance',
            meeting_type='renewal',
            scheduled_start=m3_start,
            scheduled_end=m3_start + timedelta(minutes=50),
            location_url='https://meet.google.com/int-aura-soc2',
            status='completed',
            goals=[
                'Review SOC2 Type II audit report findings',
                'Discuss zero-trust encryption key management',
                'Finalize early 24-month contract renewal terms'
            ],
            attendees=[
                {'name': 'Sarah Lin', 'email': 'sarah.lin@meetingintel.demo', 'role': 'Principal Account Executive', 'is_internal': True},
                {'name': 'Julian Scott', 'email': 'j.scott@aurapayments.com', 'role': 'CISO', 'is_internal': False},
            ],
            simulated_calendar_id='gcal_ev_aura_sec_2026'
        )

        # 5. Create Simulated Gmail Threads
        EmailMessage.objects.create(
            client=acme,
            meeting=m1,
            sender_name='Dr. Marcus Vance',
            sender_email='marcus.vance@acmehealth.io',
            recipient_name='Sarah Lin',
            recipient_email='sarah.lin@meetingintel.demo',
            subject='Re: Agenda topics for our upcoming Q4 Strategic Review',
            body=(
                "Hi Sarah,\n\nLooking forward to our session tomorrow. In addition to reviewing Q3 metrics, "
                "our European leadership (Claire Dupont) wants to ensure our telemetry pipelines comply with "
                "the latest EU DPA requirements. If David could prepare a quick slide on data residency in Frankfurt, "
                "that would be fantastic.\n\nBest,\nMarcus"
            ),
            sent_at=now - timedelta(days=1, hours=6),
            sentiment='positive',
            simulated_gmail_id='gmail_msg_acme_001'
        )

        EmailMessage.objects.create(
            client=meridian,
            meeting=m2,
            sender_name='Elena Rostova',
            sender_email='elena.rostova@meridianlogistics.net',
            recipient_name='David Miller',
            recipient_email='david.miller@meetingintel.demo',
            subject='URGENT: Webhook timeout alerts during morning peak dispatch',
            body=(
                "David,\n\nOur telemetry monitors flagged a 4.2% timeout rate on the batch status endpoint at 08:15 AM today. "
                "With holiday dispatch volumes climbing, we cannot risk dropped fleet pings. We need to see hard benchmark "
                "data during our sync this Thursday.\n\nRegards,\nElena"
            ),
            sent_at=now - timedelta(days=2, hours=4),
            sentiment='urgent',
            simulated_gmail_id='gmail_msg_meridian_002'
        )

        EmailMessage.objects.create(
            client=aura,
            meeting=m3,
            sender_name='Julian Scott',
            sender_email='j.scott@aurapayments.com',
            recipient_name='Sarah Lin',
            recipient_email='sarah.lin@meetingintel.demo',
            subject='SOC2 Type II Attestation & Renewal Agreement',
            body=(
                "Sarah,\n\nOur legal and compliance committee completed the review of your SOC2 Type II packet. "
                "Everything meets our criteria. Please send the revised 24-month renewal agreement order form for signature.\n\nJulian"
            ),
            sent_at=now - timedelta(days=3),
            sentiment='positive',
            simulated_gmail_id='gmail_msg_aura_003'
        )

        # 6. Create Asana Projects and Tasks (Including Overdue tasks for immediate rich reporting)
        p_sla = AsanaProject.objects.create(
            name='Platform Infrastructure & SLAs',
            client=meridian,
            color_hex='#0EA5E9',
            description='Load testing, API throughput guarantees, and SLA compliance tracking.'
        )

        p_renewals = AsanaProject.objects.create(
            name='Client Renewals & Contracts',
            client=acme,
            color_hex='#10B981',
            description='Order forms, legal addendums, and expansion contract management.'
        )

        p_security = AsanaProject.objects.create(
            name='Enterprise Security & Legal',
            client=aura,
            color_hex='#6366F1',
            description='Compliance audits, SOC2 packets, DPA reviews, and penetration test remediations.'
        )

        # Overdue Task 1 (Demonstrates Overdue Tracking)
        t_overdue1 = AsanaTask.objects.create(
            project=p_security,
            title='Deliver finalized SOC2 Type II attestation packet to CISO team',
            description='Export certified third-party audit report from Vanta and transmit via secure portal.',
            assignee_name='Sarah Lin',
            assignee_email='sarah.lin@meetingintel.demo',
            assignee_user=demo_user,
            due_date=today - timedelta(days=3),  # 3 days overdue!
            priority='urgent',
            status='in_progress',
            source_meeting=m3,
            simulated_asana_gid='1205938491001'
        )
        AsanaComment.objects.create(
            task=t_overdue1,
            author_name='Sarah Lin',
            author_email='sarah.lin@meetingintel.demo',
            author_user=demo_user,
            comment_text='Legal gave initial sign-off, waiting on final watermarked PDF from external auditors.'
        )

        # Overdue Task 2
        t_overdue2 = AsanaTask.objects.create(
            project=p_sla,
            title='Export Grafana webhook latency metrics for Meridian executive team',
            description='Compile p95 and p99 latency graphs from the October 4th traffic surge.',
            assignee_name='David Miller',
            assignee_email='david.miller@meetingintel.demo',
            assignee_user=david_user,
            due_date=today - timedelta(days=1),  # 1 day overdue!
            priority='high',
            status='todo',
            source_meeting=m2,
            simulated_asana_gid='1205938491002'
        )

        # Upcoming Task
        t_upcoming = AsanaTask.objects.create(
            project=p_renewals,
            title='Draft 24-month renewal agreement with 150 international seat add-on',
            description='Coordinate with sales operations on tier 2 international discount schedule.',
            assignee_name='Sarah Lin',
            assignee_email='sarah.lin@meetingintel.demo',
            assignee_user=demo_user,
            due_date=today + timedelta(days=4),
            priority='high',
            status='in_progress',
            source_meeting=m1,
            simulated_asana_gid='1205938491003'
        )

        # Completed Task
        t_completed = AsanaTask.objects.create(
            project=p_sla,
            title='Deploy exponential backoff retry worker cluster in staging',
            description='Scaled Redis queue consumers to handle burst webhook delivery with 5-second interval retries.',
            assignee_name='Alex Chen',
            assignee_email='alex.chen@meetingintel.demo',
            assignee_user=alex_user,
            due_date=today - timedelta(days=2),
            priority='medium',
            status='completed',
            completed_at=now - timedelta(days=2),
            source_meeting=m2,
            simulated_asana_gid='1205938491004'
        )
        AsanaComment.objects.create(
            task=t_completed,
            author_name='Alex Chen',
            author_email='alex.chen@meetingintel.demo',
            author_user=alex_user,
            comment_text='Verification tests passed in staging. Consumer latency dropped by 72% under simulated load.'
        )

        # 7. Generate Briefing Pack for Meeting 1 (Acme HealthTech)
        BriefingService.generate_briefing_for_meeting(m1, user=demo_user, force_mock=True)

        # 8. Create Realistic Meeting Transcripts for Sample Loading & Processing
        sample_vtt_text = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:05.000
Sarah Lin: Thanks everyone for joining our Acme HealthTech Q4 Strategy and Expansion Review.

00:00:05.500 --> 00:00:11.000
Dr. Marcus Vance: Thanks Sarah. On our side we have Claire Dupont leading our European expansion.

00:00:11.500 --> 00:00:17.500
Sarah Lin: Fantastic. We are excited about your rollout. Looking at Q3, your platform processed over 18 million patient interactions with 99.99% uptime.

00:00:18.000 --> 00:00:26.000
Dr. Marcus Vance: Yes, system reliability has been rock solid. Our primary focus now is expanding by 150 seats for our new telehealth clinics in France and Germany.

00:00:26.500 --> 00:00:34.000
Sarah Lin: I will prepare the revised order form for the 150 seat tier and send it to procurement by Monday.

00:00:34.500 --> 00:00:41.000
Claire Dupont: Excellent. Also we must ensure GDPR and Data Processing Agreement clauses are updated for the Frankfurt cluster.

00:00:41.500 --> 00:00:48.000
David Miller: I'll run the synthetic benchmark tests tomorrow morning and send over the full p95 latency report by Friday.

00:00:48.500 --> 00:00:55.000
Sarah Lin: And I will have our legal team review the updated DPA clauses and return the redlines to Marcus by next Wednesday.

00:00:55.500 --> 00:01:02.000
Alex Chen: I can lead the live training sessions for your EMEA team during the last week of October.

00:01:02.500 --> 00:01:08.000
Dr. Marcus Vance: Perfect, let's agree to finalize contract execution before October 28th.
"""

        transcript1 = MeetingTranscript.objects.create(
            meeting=m1,
            client=acme,
            title='Acme HealthTech Q4 Executive Review (Live Transcript)',
            source_filename='acme_qbr_transcript.vtt',
            format='vtt',
            raw_content=sample_vtt_text,
            duration_minutes=45,
            status='unprocessed'
        )

        sample_md_text = """# Meridian Logistics — Technical Escalation & Webhook Resilience
**Date:** October 8, 2026 | **Attendees:** David Miller, Elena Rostova, Tomas Kovacs

## Discussion Log
**Elena Rostova:** We noticed elevated response latency on the webhook dispatch endpoint during Monday's fleet dispatch. We need concrete commitments on latency thresholds.

**David Miller:** We investigated the trace telemetry. The root cause was a thread contention on the legacy synchronous dispatch worker. We have already deployed an asynchronous exponential backoff queue in staging.

**Tomas Kovacs:** What is the retry policy if our fleet ingress proxy is temporarily saturated?

**David Miller:** It will retry at 2s, 4s, 8s, up to 5 attempts before parking in the dead-letter queue. I will provide synthetic benchmark latency report (p95 < 50ms) to engineering leads by Friday.

**Elena Rostova:** We should schedule a follow-up architecture deep dive on Multi-Region failover before we sign off on staging.

**David Miller:** Agreed. I will coordinate the architecture deep dive with our core infrastructure architects by next Tuesday.
"""

        transcript2 = MeetingTranscript.objects.create(
            meeting=m2,
            client=meridian,
            title='Meridian Logistics Webhook SLA Sync (Markdown)',
            source_filename='meridian_tech_escalation.md',
            format='md',
            raw_content=sample_md_text,
            duration_minutes=35,
            status='unprocessed'
        )

        # Process transcript1 to pre-fill pending action items in review queue
        TranscriptService.process_transcript(transcript1, user=demo_user, force_mock=True)

        # 9. Initialize Mock Integrations
        IntegrationService.ensure_initial_statuses()

        # 10. Record Seed Audit Log
        AuditLogEvent.objects.create(
            event_type='demo_reseeded',
            actor_name='System Administrator',
            actor_user=demo_user,
            title='Demo Intelligence Environment Reseeded',
            description='Populated 4 enterprise clients, 3 calendar meetings, 3 email threads, 3 Asana boards, and 1 processed transcript queue.',
            metadata={'clients': 4, 'meetings': 3, 'tasks': 4}
        )

        return {
            'clients_created': 4,
            'meetings_created': 3,
            'tasks_created': 4,
            'transcripts_created': 2
        }

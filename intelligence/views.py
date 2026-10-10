"""
Views for Meeting Intelligence.
Provides end-to-end dashboard, calendar, AI briefings, transcript processing,
human approval triage, Asana task simulation, weekly reports, and integration panels.
"""

import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

from .models import (
    Client, Meeting, EmailMessage, BriefingPack, MeetingTranscript,
    MeetingSummaryRecord, ExtractedActionItem, AsanaProject, AsanaTask,
    AsanaComment, WeeklyReport, EmailDeliveryLog, IntegrationSyncStatus,
    AuditLogEvent
)
from .forms import (
    TranscriptUploadForm, ActionItemApprovalForm, ActionItemRejectionForm,
    TaskCommentForm, EmailDispatchForm, AISettingsForm
)
from .services.briefing_service import BriefingService
from .services.transcript_service import TranscriptService
from .services.task_service import TaskService
from .services.report_service import ReportService
from .services.integration_service import IntegrationService
from .services.seed_service import SeedService
from .services.ai_client import AIService


# ==========================================
# Authentication & Demo Switcher
# ==========================================

class DemoLoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('intelligence:dashboard')
        return render(request, 'intelligence/login.html')

    def post(self, request):
        action = request.POST.get('action', 'quick_demo')
        if action == 'quick_demo':
            user = User.objects.filter(username='demo').first()
            if not user:
                SeedService.reseed_all_demo_data()
                user = User.objects.filter(username='demo').first()
            login(request, user)
            messages.success(request, f"Logged in as {user.get_full_name()} (Demo Lead AE).")
            return redirect('intelligence:dashboard')
        
        username = request.POST.get('username')
        password = request.POST.get('password')
        from django.contrib.auth import authenticate
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect('intelligence:dashboard')
        
        messages.error(request, "Invalid credentials. Use 'demo' / 'demo1234' or click Quick Demo Login.")
        return render(request, 'intelligence/login.html')


def demo_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('intelligence:login')


# ==========================================
# 1. Dashboard View
# ==========================================

class DashboardView(View):
    def get(self, request):
        now = timezone.now()
        today = now.date()

        # Metrics
        upcoming_meetings = Meeting.objects.filter(scheduled_start__gte=now).order_by('scheduled_start')[:4]
        pending_actions = ExtractedActionItem.objects.filter(status='pending_review').select_related('transcript', 'meeting', 'client')[:5]
        overdue_tasks = AsanaTask.objects.filter(
            due_date__lt=today
        ).exclude(status='completed').select_related('project', 'project__client').order_by('due_date')[:5]
        
        open_tasks = AsanaTask.objects.exclude(status='completed').select_related('project')
        recent_transcripts = MeetingTranscript.objects.all().order_by('-created_at')[:3]
        recent_audits = AuditLogEvent.objects.all().order_by('-created_at')[:8]
        
        # Integrations health summary
        integrations = IntegrationSyncStatus.objects.all()

        context = {
            'upcoming_meetings': upcoming_meetings,
            'pending_actions': pending_actions,
            'overdue_tasks': overdue_tasks,
            'open_tasks_count': open_tasks.count(),
            'recent_transcripts': recent_transcripts,
            'recent_audits': recent_audits,
            'integrations': integrations,
            'today': today,
        }
        return render(request, 'intelligence/dashboard.html', context)


# ==========================================
# 2. Simulated Calendar & Meeting Briefings
# ==========================================

class CalendarView(View):
    def get(self, request):
        now = timezone.now()
        meetings = Meeting.objects.all().select_related('client', 'briefing_pack').order_by('scheduled_start')
        
        upcoming = [m for m in meetings if m.scheduled_start >= now]
        past = [m for m in meetings if m.scheduled_start < now]

        context = {
            'upcoming_meetings': upcoming,
            'past_meetings': past,
            'now': now,
        }
        return render(request, 'intelligence/calendar.html', context)


class MeetingDetailView(View):
    def get(self, request, pk):
        meeting = get_object_or_404(Meeting.objects.select_related('client'), pk=pk)
        related_emails = EmailMessage.objects.filter(client=meeting.client).order_by('-sent_at')[:5]
        transcripts = meeting.transcripts.all()
        tasks = AsanaTask.objects.filter(source_meeting=meeting)
        
        has_briefing = hasattr(meeting, 'briefing_pack') and meeting.briefing_pack is not None

        context = {
            'meeting': meeting,
            'related_emails': related_emails,
            'transcripts': transcripts,
            'tasks': tasks,
            'has_briefing': has_briefing,
        }
        return render(request, 'intelligence/meeting_detail.html', context)


class MeetingBriefingView(View):
    def get(self, request, pk):
        meeting = get_object_or_404(Meeting.objects.select_related('client'), pk=pk)
        
        briefing = None
        if hasattr(meeting, 'briefing_pack') and meeting.briefing_pack:
            briefing = meeting.briefing_pack
        else:
            # Generate briefing on demand if not yet created
            briefing = BriefingService.generate_briefing_for_meeting(
                meeting=meeting,
                user=request.user if request.user.is_authenticated else None
            )

        context = {
            'meeting': meeting,
            'briefing': briefing,
            'raw_prompt': briefing.raw_prompt,
            'raw_response': briefing.raw_response,
        }
        return render(request, 'intelligence/briefing_view.html', context)


class GenerateBriefingActionView(View):
    """Triggers generation or refresh of a Briefing Pack via HTMX or standard POST."""
    def post(self, request, pk):
        meeting = get_object_or_404(Meeting, pk=pk)
        force_refresh = request.POST.get('force_refresh', 'true').lower() in ('true', '1')
        force_mock = request.POST.get('force_mock', 'false').lower() in ('true', '1')
        
        briefing = BriefingService.generate_briefing_for_meeting(
            meeting=meeting,
            user=request.user if request.user.is_authenticated else None,
            force_refresh=force_refresh,
            force_mock=force_mock
        )

        messages.success(request, f"AI Briefing generated for {meeting.title} ({briefing.ai_provider}).")

        if request.headers.get('HX-Request'):
            return render(request, 'intelligence/partials/briefing_content.html', {
                'meeting': meeting,
                'briefing': briefing
            })
        return redirect('intelligence:meeting_briefing', pk=meeting.id)


# ==========================================
# 3. Transcript Processing & Human Approval
# ==========================================

class TranscriptListView(View):
    def get(self, request):
        transcripts = MeetingTranscript.objects.all().select_related('meeting', 'client', 'summary_record').order_by('-created_at')
        form = TranscriptUploadForm()
        
        context = {
            'transcripts': transcripts,
            'form': form,
        }
        return render(request, 'intelligence/transcript_list.html', context)


class TranscriptUploadView(View):
    def post(self, request):
        form = TranscriptUploadForm(request.POST, request.FILES)
        sample_choice = request.POST.get('sample_choice', '')

        # Check if user picked a pre-built sample
        if sample_choice:
            sample_data = self._get_sample_data(sample_choice)
            transcript = MeetingTranscript.objects.create(
                client=sample_data.get('client'),
                meeting=sample_data.get('meeting'),
                title=sample_data.get('title'),
                source_filename=sample_data.get('source_filename'),
                format=sample_data.get('format'),
                raw_content=sample_data.get('raw_content'),
                duration_minutes=sample_data.get('duration_minutes', 30),
                status='unprocessed'
            )
            messages.success(request, f"Loaded enterprise sample transcript: '{transcript.title}'. Ready to extract!")
            return redirect('intelligence:transcript_detail', pk=transcript.id)

        # File upload handling
        uploaded_file = request.FILES.get('transcript_file')
        raw_text = request.POST.get('raw_content', '').strip()
        
        if uploaded_file:
            content_bytes = uploaded_file.read()
            try:
                raw_text = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                raw_text = content_bytes.decode('latin-1', errors='replace')
            
            ext = uploaded_file.name.split('.')[-1].lower()
            detected_format = 'vtt' if ext == 'vtt' else ('md' if ext == 'md' else 'txt')
            source_filename = uploaded_file.name
            title = request.POST.get('title') or f"Uploaded Transcript: {uploaded_file.name}"
        elif raw_text:
            detected_format = request.POST.get('format', 'txt')
            source_filename = 'manual_entry.txt'
            title = request.POST.get('title') or f"Manual Notes ({timezone.now().strftime('%b %d, %H:%M')})"
        else:
            messages.error(request, "Please choose a sample, upload a file (.txt, .md, .vtt), or paste transcript content.")
            return redirect('intelligence:transcript_list')

        client_id = request.POST.get('client')
        meeting_id = request.POST.get('meeting')
        client = Client.objects.filter(id=client_id).first() if client_id else None
        meeting = Meeting.objects.filter(id=meeting_id).first() if meeting_id else None

        # Clean VTT if needed
        if detected_format == 'vtt':
            clean_text = TranscriptService.clean_vtt_content(raw_text)
        else:
            clean_text = raw_text

        transcript = MeetingTranscript.objects.create(
            client=client or (meeting.client if meeting else None),
            meeting=meeting,
            title=title,
            source_filename=source_filename,
            format=detected_format,
            raw_content=clean_text or raw_text,
            duration_minutes=30,
            status='unprocessed'
        )

        AuditLogEvent.objects.create(
            event_type='transcript_uploaded',
            actor_name=request.user.get_full_name() if request.user.is_authenticated else 'User',
            actor_user=request.user if request.user.is_authenticated else None,
            meeting=meeting,
            client=client,
            title=f"Uploaded Transcript: {transcript.title}",
            description=f"Format: {detected_format}, Words: {transcript.word_count}",
            metadata={'transcript_id': transcript.id, 'format': detected_format}
        )

        messages.success(request, f"Transcript '{transcript.title}' uploaded successfully.")
        return redirect('intelligence:transcript_detail', pk=transcript.id)

    def _get_sample_data(self, sample_choice: str) -> dict:
        acme = Client.objects.filter(slug='acme-healthtech').first()
        meridian = Client.objects.filter(slug='meridian-logistics').first()
        aura = Client.objects.filter(slug='aura-fintech').first()

        if sample_choice == 'meridian_tech':
            return {
                'client': meridian,
                'meeting': Meeting.objects.filter(client=meridian).first(),
                'title': 'Meridian Logistics — High-Throughput Webhook SLA & Latency Sync',
                'source_filename': 'meridian_tech_escalation.md',
                'format': 'md',
                'duration_minutes': 35,
                'raw_content': """# Meridian Logistics — Technical Escalation & Webhook Resilience
**Attendees:** David Miller (Lead Architect), Elena Rostova (Director Architecture), Tomas Kovacs (DevOps)

**Elena Rostova:** We noticed elevated response latency on the webhook dispatch endpoint during Monday's fleet dispatch. We need concrete commitments on latency thresholds.

**David Miller:** We investigated the trace telemetry. The root cause was thread contention on the synchronous dispatch worker. We already deployed an asynchronous exponential backoff queue in staging.

**Tomas Kovacs:** What is the retry policy if our fleet ingress proxy is temporarily saturated?

**David Miller:** It will retry at 2s, 4s, 8s, up to 5 attempts before parking in the dead-letter queue. I will provide synthetic benchmark latency report (p95 < 50ms) to engineering leads by Friday.

**Elena Rostova:** We should schedule a follow-up architecture deep dive on Multi-Region failover before we sign off on staging.

**David Miller:** Agreed. I will coordinate the architecture deep dive with our core infrastructure architects by next Tuesday."""
            }
        elif sample_choice == 'aura_sec':
            return {
                'client': aura,
                'meeting': Meeting.objects.filter(client=aura).first(),
                'title': 'Aura Fintech — SOC2 Compliance & Multi-Region Discovery',
                'source_filename': 'aura_security_discovery.txt',
                'format': 'txt',
                'duration_minutes': 40,
                'raw_content': """Meeting Transcript: Aura Fintech Security Review
Attendees: Sarah Lin, Julian Scott (CISO)

Julian: Our compliance audit committee reviewed the architecture summary. We need the final watermarked SOC2 Type II audit pack to approve the 24-month contract renewal.
Sarah: I will have our security team transmit the watermarked SOC2 Type II audit pack via the secure portal by Thursday.
Julian: We also need confirmation on KMS customer-managed key encryption for database snapshots.
Sarah: I will follow up with our lead database engineer to confirm the KMS key rotation policy by Monday."""
            }
        else:
            return {
                'client': acme,
                'meeting': Meeting.objects.filter(client=acme).first(),
                'title': 'Acme HealthTech — Q4 Executive Business Review & EMEA Expansion',
                'source_filename': 'acme_qbr_transcript.vtt',
                'format': 'vtt',
                'duration_minutes': 45,
                'raw_content': """WEBVTT

00:00:01.000 --> 00:00:05.000
Sarah Lin: Thanks everyone for joining our Acme HealthTech Q4 Strategy and Expansion Review.

00:00:05.500 --> 00:00:11.000
Dr. Marcus Vance: Thanks Sarah. We have Claire Dupont leading our European expansion.

00:00:11.500 --> 00:00:18.000
Dr. Marcus Vance: Our primary focus now is expanding by 150 seats for our new telehealth clinics in France and Germany.

00:00:18.500 --> 00:00:26.000
Sarah Lin: I will prepare the revised order form for the 150 seat tier and send it to procurement by Monday.

00:00:26.500 --> 00:00:34.000
Claire Dupont: Also we must ensure GDPR and Data Processing Agreement clauses are updated for the Frankfurt cluster.

00:00:34.500 --> 00:00:41.000
Sarah Lin: I will have our legal team review the updated DPA clauses and return the redlines to Marcus by next Wednesday."""
            }


class TranscriptDetailView(View):
    def get(self, request, pk):
        transcript = get_object_or_404(MeetingTranscript.objects.select_related('meeting', 'client'), pk=pk)
        summary = getattr(transcript, 'summary_record', None)
        actions = transcript.extracted_actions.all().order_by('status', '-confidence_score')

        context = {
            'transcript': transcript,
            'summary': summary,
            'actions': actions,
            'pending_count': actions.filter(status='pending_review').count(),
            'approved_count': actions.filter(status__in=['approved', 'modified']).count(),
            'rejected_count': actions.filter(status='rejected').count(),
        }
        return render(request, 'intelligence/transcript_detail.html', context)


class ProcessTranscriptActionView(View):
    """Triggers AI extraction on a transcript (HTMX / POST)."""
    def post(self, request, pk):
        transcript = get_object_or_404(MeetingTranscript, pk=pk)
        force_mock = request.POST.get('force_mock', 'false').lower() in ('true', '1')

        try:
            TranscriptService.process_transcript(
                transcript=transcript,
                user=request.user if request.user.is_authenticated else None,
                force_reprocess=True,
                force_mock=force_mock
            )
            messages.success(request, f"AI extracted commitments & decisions from '{transcript.title}'.")
        except Exception as e:
            messages.error(request, f"Processing failed: {e}")

        if request.headers.get('HX-Request'):
            summary = getattr(transcript, 'summary_record', None)
            actions = transcript.extracted_actions.all().order_by('status', '-confidence_score')
            return render(request, 'intelligence/partials/transcript_results.html', {
                'transcript': transcript,
                'summary': summary,
                'actions': actions,
            })

        return redirect('intelligence:transcript_detail', pk=transcript.id)


# ==========================================
# 4. Human Approval Triage Queue
# ==========================================

class ApprovalQueueView(View):
    def get(self, request):
        status_filter = request.GET.get('status', 'pending_review')
        client_filter = request.GET.get('client', '')

        actions = ExtractedActionItem.objects.select_related('transcript', 'meeting', 'client', 'asana_task', 'reviewed_by')
        
        if status_filter != 'all':
            actions = actions.filter(status=status_filter)
        if client_filter:
            actions = actions.filter(client_id=client_filter)

        actions = actions.order_by('-created_at')

        clients = Client.objects.all()
        pending_total = ExtractedActionItem.objects.filter(status='pending_review').count()

        context = {
            'actions': actions,
            'clients': clients,
            'current_status': status_filter,
            'current_client': client_filter,
            'pending_total': pending_total,
        }
        return render(request, 'intelligence/approval_queue.html', context)


class ActionApproveView(View):
    """One-click Approve Action Item -> Generates Asana Task."""
    def post(self, request, pk):
        action = get_object_or_404(ExtractedActionItem, pk=pk)
        task = TaskService.approve_action_item(
            action_item=action,
            user=request.user if request.user.is_authenticated else None
        )
        messages.success(request, f"Approved! Task created in '{task.project.name}': {task.title}")

        if request.headers.get('HX-Request'):
            return render(request, 'intelligence/partials/action_row.html', {'action': action})
        return redirect('intelligence:approval_queue')


class ActionEditApproveView(View):
    """Provides edit modal / handles edited approval."""
    def get(self, request, pk):
        action = get_object_or_404(ExtractedActionItem, pk=pk)
        form = ActionItemApprovalForm(instance=action)
        return render(request, 'intelligence/partials/action_edit_modal.html', {
            'action': action,
            'form': form
        })

    def post(self, request, pk):
        action = get_object_or_404(ExtractedActionItem, pk=pk)
        form = ActionItemApprovalForm(request.POST, instance=action)
        
        if form.is_valid():
            modifications = {
                'title': form.cleaned_data['title'],
                'description': form.cleaned_data['description'],
                'proposed_owner_name': form.cleaned_data['proposed_owner_name'],
                'proposed_owner_email': form.cleaned_data['proposed_owner_email'],
                'proposed_due_date': form.cleaned_data['proposed_due_date'],
                'urgency': form.cleaned_data['urgency'],
                'suggested_project_name': form.cleaned_data['suggested_project_name'],
            }
            task = TaskService.approve_action_item(
                action_item=action,
                user=request.user if request.user.is_authenticated else None,
                modifications=modifications
            )
            messages.success(request, f"Modified & Approved! Task created in '{task.project.name}'.")
            
            if request.headers.get('HX-Request'):
                return render(request, 'intelligence/partials/action_row.html', {'action': action})
            return redirect('intelligence:approval_queue')
        
        return render(request, 'intelligence/partials/action_edit_modal.html', {
            'action': action,
            'form': form,
            'has_errors': True
        })


class ActionRejectView(View):
    def post(self, request, pk):
        action = get_object_or_404(ExtractedActionItem, pk=pk)
        reason = request.POST.get('reason', 'Rejected during human review.')
        TaskService.reject_action_item(
            action_item=action,
            reason=reason,
            user=request.user if request.user.is_authenticated else None
        )
        messages.info(request, f"Action item '{action.title}' rejected.")

        if request.headers.get('HX-Request'):
            return render(request, 'intelligence/partials/action_row.html', {'action': action})
        return redirect('intelligence:approval_queue')


# ==========================================
# 5. Simulated Asana Task Manager
# ==========================================

class AsanaTaskListView(View):
    def get(self, request):
        project_id = request.GET.get('project', '')
        status_filter = request.GET.get('status', '')
        view_mode = request.GET.get('view', 'list')  # 'list' or 'board'
        
        today = timezone.now().date()
        tasks = AsanaTask.objects.select_related('project', 'project__client', 'assignee_user', 'source_meeting').prefetch_related('comments')

        if project_id:
            tasks = tasks.filter(project_id=project_id)
        if status_filter == 'overdue':
            tasks = tasks.filter(due_date__lt=today).exclude(status='completed')
        elif status_filter:
            tasks = tasks.filter(status=status_filter)

        tasks = tasks.order_by('status', 'due_date')

        projects = AsanaProject.objects.all().prefetch_related('tasks')
        
        # Board view column groups
        board_columns = {
            'todo': tasks.filter(status='todo'),
            'in_progress': tasks.filter(status='in_progress'),
            'under_review': tasks.filter(status='under_review'),
            'completed': tasks.filter(status='completed'),
        }

        context = {
            'tasks': tasks,
            'projects': projects,
            'current_project': project_id,
            'current_status': status_filter,
            'view_mode': view_mode,
            'board_columns': board_columns,
            'today': today,
        }
        return render(request, 'intelligence/asana_tasks.html', context)


class AsanaTaskDetailView(View):
    def get(self, request, pk):
        task = get_object_or_404(AsanaTask.objects.select_related('project', 'project__client', 'source_meeting'), pk=pk)
        comments = task.comments.all().order_by('created_at')
        comment_form = TaskCommentForm()

        context = {
            'task': task,
            'comments': comments,
            'comment_form': comment_form,
            'today': timezone.now().date(),
        }
        if request.headers.get('HX-Request'):
            return render(request, 'intelligence/partials/task_detail_modal.html', context)
        return render(request, 'intelligence/task_detail_page.html', context)


class AsanaTaskStatusUpdateView(View):
    def post(self, request, pk):
        task = get_object_or_404(AsanaTask, pk=pk)
        new_status = request.POST.get('status', 'todo')
        
        if new_status in dict(AsanaTask.STATUS_CHOICES):
            TaskService.update_task_status(
                task=task,
                new_status=new_status,
                user=request.user if request.user.is_authenticated else None
            )
            messages.success(request, f"Task '{task.title}' updated to {task.get_status_display()}.")

        if request.headers.get('HX-Request'):
            return render(request, 'intelligence/partials/task_row.html', {
                'task': task,
                'today': timezone.now().date()
            })
        return redirect('intelligence:task_list')


class AsanaTaskCommentAddView(View):
    def post(self, request, pk):
        task = get_object_or_404(AsanaTask, pk=pk)
        comment_text = request.POST.get('comment_text', '').strip()
        
        if comment_text:
            author_name = request.user.get_full_name() if request.user.is_authenticated else 'Sarah Lin (Demo)'
            author_email = request.user.email if request.user.is_authenticated else 'sarah.lin@meetingintel.demo'
            TaskService.add_comment(
                task=task,
                comment_text=comment_text,
                author_name=author_name,
                author_email=author_email,
                user=request.user if request.user.is_authenticated else None
            )

        if request.headers.get('HX-Request'):
            comments = task.comments.all().order_by('created_at')
            return render(request, 'intelligence/partials/task_comments_list.html', {
                'task': task,
                'comments': comments
            })
        return redirect('intelligence:task_list')


# ==========================================
# 6. Weekly Overdue Report & Email Dispatch
# ==========================================

class WeeklyReportView(View):
    def get(self, request):
        latest_report = WeeklyReport.objects.first()
        if not latest_report:
            latest_report = ReportService.generate_weekly_report(
                user=request.user if request.user.is_authenticated else None
            )
        
        reports_history = WeeklyReport.objects.all().order_by('-generated_at')[:10]
        delivery_logs = EmailDeliveryLog.objects.filter(email_type='weekly_report').order_by('-sent_at')[:5]
        dispatch_form = EmailDispatchForm()

        context = {
            'report': latest_report,
            'reports_history': reports_history,
            'delivery_logs': delivery_logs,
            'dispatch_form': dispatch_form,
        }
        return render(request, 'intelligence/weekly_report.html', context)


class WeeklyReportGenerateView(View):
    def post(self, request):
        report = ReportService.generate_weekly_report(
            user=request.user if request.user.is_authenticated else None
        )
        messages.success(request, f"New Weekly Report generated ({report.period_label}).")
        return redirect('intelligence:weekly_report')


class EmailDispatchView(View):
    """Simulates outbound SMTP delivery of the weekly report to stakeholder mailing lists."""
    def post(self, request, pk):
        report = get_object_or_404(WeeklyReport, pk=pk)
        recipients = request.POST.get('recipient_emails', 'executive-team@meetingintel.demo')
        
        delivery = ReportService.simulate_dispatch_email(
            report=report,
            recipient_emails=recipients,
            user=request.user if request.user.is_authenticated else None
        )

        messages.success(request, f"Simulated email delivery successful! Message ID: {delivery.smtp_message_id} ({delivery.smtp_response})")
        
        if request.headers.get('HX-Request'):
            delivery_logs = EmailDeliveryLog.objects.filter(email_type='weekly_report').order_by('-sent_at')[:5]
            return render(request, 'intelligence/partials/delivery_logs_table.html', {
                'delivery_logs': delivery_logs,
                'latest_delivery': delivery
            })
        return redirect('intelligence:weekly_report')


class EmailDeliveryLogListView(View):
    def get(self, request):
        logs = EmailDeliveryLog.objects.all().order_by('-sent_at')
        return render(request, 'intelligence/email_logs.html', {'logs': logs})


# ==========================================
# 7. Simulated Integrations Panel
# ==========================================

class IntegrationsView(View):
    def get(self, request):
        IntegrationService.ensure_initial_statuses()
        integrations = IntegrationSyncStatus.objects.all()
        recent_sync_audits = AuditLogEvent.objects.filter(
            event_type__in=['demo_reseeded', 'briefing_generated', 'transcript_processed', 'action_approved']
        ).order_by('-created_at')[:10]

        context = {
            'integrations': integrations,
            'recent_sync_audits': recent_sync_audits,
        }
        return render(request, 'intelligence/integrations.html', context)


class IntegrationSyncActionView(View):
    def post(self, request, service_key):
        status = IntegrationService.simulate_sync(
            service_key=service_key,
            user=request.user if request.user.is_authenticated else None
        )
        messages.success(request, f"Simulated sync completed for {status.service_title}. Indexed {status.synced_items_count} items.")

        if request.headers.get('HX-Request'):
            return render(request, 'intelligence/partials/integration_card.html', {'integration': status})
        return redirect('intelligence:integrations')


# ==========================================
# 8. Audit Trail
# ==========================================

class AuditTrailView(View):
    def get(self, request):
        event_filter = request.GET.get('type', '')
        search_query = request.GET.get('q', '')

        audits = AuditLogEvent.objects.select_related('actor_user', 'meeting', 'client')
        if event_filter:
            audits = audits.filter(event_type=event_filter)
        if search_query:
            audits = audits.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(actor_name__icontains=search_query)
            )

        audits = audits.order_by('-created_at')[:100]

        context = {
            'audits': audits,
            'event_types': AuditLogEvent.EVENT_TYPES,
            'current_type': event_filter,
            'search_query': search_query,
        }
        return render(request, 'intelligence/audit_trail.html', context)


# ==========================================
# 9. Demo Controls & Settings
# ==========================================

class DemoControlsView(View):
    def get(self, request):
        initial_data = {
            'ai_mode': AIService.get_active_mode(),
            'gemini_api_key': getattr(settings, 'GEMINI_API_KEY', ''),
            'gemini_model': getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-pro'),
        }
        settings_form = AISettingsForm(initial=initial_data)
        
        context = {
            'settings_form': settings_form,
            'clients_count': Client.objects.count(),
            'meetings_count': Meeting.objects.count(),
            'tasks_count': AsanaTask.objects.count(),
            'transcripts_count': MeetingTranscript.objects.count(),
            'audit_count': AuditLogEvent.objects.count(),
            'current_mode': AIService.get_active_mode(),
            'has_key': bool(getattr(settings, 'GEMINI_API_KEY', '')),
        }
        return render(request, 'intelligence/demo_controls.html', context)

    def post(self, request):
        action = request.POST.get('action')

        if action == 'reseed':
            res = SeedService.reseed_all_demo_data()
            messages.success(request, f"Environment successfully reseeded with {res['clients_created']} clients, {res['meetings_created']} meetings, {res['tasks_created']} Asana tasks.")
            return redirect('intelligence:dashboard')

        elif action == 'save_ai_settings':
            mode = request.POST.get('ai_mode', 'mock')
            key = request.POST.get('gemini_api_key', '').strip()
            model = request.POST.get('gemini_model', 'gemini-1.5-pro')

            # Update in-memory settings for active session
            settings.AI_MODE = mode
            if key:
                settings.GEMINI_API_KEY = key
            settings.GEMINI_MODEL = model

            messages.success(request, f"AI Configuration updated: Mode={mode.upper()}, Model={model}.")
            return redirect('intelligence:demo_controls')

        messages.info(request, "Action processed.")
        return redirect('intelligence:demo_controls')

"""
Report Service.
Compiles weekly accountability digests, overdue trackers, and simulated email dispatches.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.template.loader import render_to_string
from ..models import (
    WeeklyReport, EmailDeliveryLog, AsanaTask, ExtractedActionItem, 
    MeetingSummaryRecord, AuditLogEvent
)

logger = logging.getLogger(__name__)


class ReportService:

    @classmethod
    def generate_weekly_report(cls, user=None) -> WeeklyReport:
        """
        Compiles the weekly executive overdue and accountability report.
        """
        now = timezone.now()
        today = now.date()
        period_start = today - timedelta(days=7)
        period_end = today
        period_label = f"Week {today.isocalendar()[1]} ({period_start.strftime('%b %d')} - {period_end.strftime('%b %d, %Y')})"

        # 1. Query metrics
        overdue_tasks = AsanaTask.objects.filter(
            due_date__lt=today
        ).exclude(status='completed').select_related('project', 'project__client').order_by('due_date')

        upcoming_tasks = AsanaTask.objects.filter(
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7)
        ).exclude(status='completed').select_related('project', 'project__client').order_by('due_date')

        completed_tasks = AsanaTask.objects.filter(
            status='completed',
            completed_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('project', 'project__client').order_by('-completed_at')

        pending_actions = ExtractedActionItem.objects.filter(
            status='pending_review'
        ).select_related('transcript', 'meeting', 'client')

        total_actions_tracked = AsanaTask.objects.count()

        # Gather recent decisions from meeting summary records
        recent_summaries = MeetingSummaryRecord.objects.all().order_by('-created_at')[:5]
        key_decisions_list = []
        for s in recent_summaries:
            for d in s.key_decisions:
                key_decisions_list.append({
                    "decision": d.get("decision", ""),
                    "rationale": d.get("rationale", ""),
                    "meeting": s.transcript.title if s.transcript else "General Sync"
                })

        report_data = {
            "period_label": period_label,
            "period_start": str(period_start),
            "period_end": str(period_end),
            "overdue_tasks": [
                {
                    "title": t.title,
                    "assignee": t.assignee_name,
                    "project": t.project.name,
                    "client": t.project.client.name if t.project.client else "Internal",
                    "due_date": t.due_date.strftime('%Y-%m-%d') if t.due_date else "N/A",
                    "priority": t.get_priority_display(),
                    "status": t.get_status_display()
                }
                for t in overdue_tasks
            ],
            "upcoming_tasks": [
                {
                    "title": t.title,
                    "assignee": t.assignee_name,
                    "project": t.project.name,
                    "client": t.project.client.name if t.project.client else "Internal",
                    "due_date": t.due_date.strftime('%Y-%m-%d') if t.due_date else "N/A",
                    "priority": t.get_priority_display()
                }
                for t in upcoming_tasks
            ],
            "completed_tasks": [
                {
                    "title": t.title,
                    "assignee": t.assignee_name,
                    "project": t.project.name,
                    "completed_at": t.completed_at.strftime('%Y-%m-%d') if t.completed_at else "Recently"
                }
                for t in completed_tasks
            ],
            "pending_approvals_count": pending_actions.count(),
            "decisions_ratified": key_decisions_list
        }

        # Build Markdown content
        md_lines = [
            f"# Executive Weekly Intelligence & Overdue Report: {period_label}",
            f"\n**Period:** {period_start} to {period_end} | **Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
            "\n## Executive Summary",
            f"- **Total Open Tasks Tracked:** {total_actions_tracked}",
            f"- **Overdue Commitments Requiring Escalation:** {overdue_tasks.count()}",
            f"- **Upcoming Deadlines (Next 7 Days):** {upcoming_tasks.count()}",
            f"- **Completed Milestones This Week:** {completed_tasks.count()}",
            f"- **Unreviewed AI Action Items in Queue:** {pending_actions.count()}",
            "\n---",
            "\n## 1. Overdue Action Items (Urgent Escalation)",
        ]

        if overdue_tasks:
            for ot in overdue_tasks:
                client_str = f"[{ot.project.client.name}] " if ot.project.client else ""
                md_lines.append(f"- **{client_str}{ot.title}**")
                md_lines.append(f"  - **Owner:** {ot.assignee_name} | **Due:** {ot.due_date} | **Priority:** {ot.get_priority_display()}")
        else:
            md_lines.append("_No overdue tasks currently on the ledger. Clean SLA compliance._")

        md_lines.append("\n## 2. Upcoming Deadlines (Next 7 Days)")
        if upcoming_tasks:
            for ut in upcoming_tasks:
                client_str = f"[{ut.project.client.name}] " if ut.project.client else ""
                md_lines.append(f"- **{client_str}{ut.title}** (Due: {ut.due_date}, Owner: {ut.assignee_name})")
        else:
            md_lines.append("_No tasks due in the immediate 7-day window._")

        md_lines.append("\n## 3. Milestones Completed This Period")
        if completed_tasks:
            for ct in completed_tasks:
                md_lines.append(f"- [x] **{ct.title}** (Completed by {ct.assignee_name})")
        else:
            md_lines.append("_No tasks marked completed in the past 7 days._")

        md_lines.append("\n## 4. Key Strategic Decisions Ratified")
        if key_decisions_list:
            for kd in key_decisions_list[:5]:
                md_lines.append(f"- **{kd['decision']}** (Context: {kd['meeting']})")
        else:
            md_lines.append("_No new major governance decisions recorded this period._")

        report_markdown = "\n".join(md_lines)

        # Simple standalone HTML rendering for email preview and dashboard
        report_html = f"""
        <div class="weekly-report-body space-y-6">
            <div class="bg-indigo-900/40 border border-indigo-500/30 rounded-xl p-5 mb-6">
                <h2 class="text-xl font-bold text-white mb-2">Executive Weekly Intelligence Report</h2>
                <p class="text-slate-300 text-sm">{period_label} &bull; Generated {now.strftime('%b %d, %Y %H:%M')}</p>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div class="bg-rose-950/40 border border-rose-800/40 rounded-lg p-4">
                    <div class="text-rose-400 text-xs font-semibold uppercase tracking-wider">Overdue Actions</div>
                    <div class="text-2xl font-bold text-rose-200 mt-1">{overdue_tasks.count()}</div>
                </div>
                <div class="bg-amber-950/40 border border-amber-800/40 rounded-lg p-4">
                    <div class="text-amber-400 text-xs font-semibold uppercase tracking-wider">Due Next 7 Days</div>
                    <div class="text-2xl font-bold text-amber-200 mt-1">{upcoming_tasks.count()}</div>
                </div>
                <div class="bg-emerald-950/40 border border-emerald-800/40 rounded-lg p-4">
                    <div class="text-emerald-400 text-xs font-semibold uppercase tracking-wider">Completed This Week</div>
                    <div class="text-2xl font-bold text-emerald-200 mt-1">{completed_tasks.count()}</div>
                </div>
                <div class="bg-blue-950/40 border border-blue-800/40 rounded-lg p-4">
                    <div class="text-blue-400 text-xs font-semibold uppercase tracking-wider">Pending Review</div>
                    <div class="text-2xl font-bold text-blue-200 mt-1">{pending_actions.count()}</div>
                </div>
            </div>
        </div>
        """

        # Save to database
        report = WeeklyReport.objects.create(
            period_label=period_label,
            period_start=period_start,
            period_end=period_end,
            total_actions_tracked=total_actions_tracked,
            overdue_actions_count=overdue_tasks.count(),
            upcoming_deadlines_count=upcoming_tasks.count(),
            completed_this_period_count=completed_tasks.count(),
            unresolved_decisions_count=pending_actions.count(),
            report_markdown=report_markdown,
            report_html=report_html,
            report_data=report_data
        )

        AuditLogEvent.objects.create(
            event_type='report_generated',
            actor_name=user.get_full_name() if (user and user.is_authenticated) else 'Report Engine',
            actor_user=user if (user and user.is_authenticated) else None,
            title=f"Generated Weekly Report ({period_label})",
            description=f"Compiled weekly digest: {overdue_tasks.count()} overdue, {upcoming_tasks.count()} upcoming deadlines.",
            metadata={
                'report_id': report.id,
                'overdue_count': overdue_tasks.count(),
                'upcoming_count': upcoming_tasks.count()
            }
        )

        return report

    @classmethod
    def simulate_dispatch_email(cls, report: WeeklyReport, recipient_emails: str, user=None) -> EmailDeliveryLog:
        """
        Simulates outbound SMTP delivery of the weekly report to stakeholders and writes to EmailDeliveryLog.
        """
        recipients = [r.strip() for r in recipient_emails.split(',') if r.strip()]
        recipient_count = len(recipients) or 1
        subject = f"[Intelligence Digest] Executive Overdue & Action Report — {report.period_label}"

        delivery_log = EmailDeliveryLog.objects.create(
            email_type='weekly_report',
            recipient_emails="; ".join(recipients),
            recipient_count=recipient_count,
            subject=subject,
            body_preview=f"Weekly Report summary: {report.overdue_actions_count} overdue items, {report.upcoming_deadlines_count} upcoming deadlines.",
            full_body_html=report.report_markdown,
            simulated_status='delivered',
            smtp_response=f"250 2.0.0 OK: delivered to {recipient_count} recipients (Simulated MTA queue)"
        )

        AuditLogEvent.objects.create(
            event_type='email_dispatched',
            actor_name=user.get_full_name() if (user and user.is_authenticated) else 'System Mailer',
            actor_user=user if (user and user.is_authenticated) else None,
            title=f"Dispatched Weekly Digest to {recipient_count} recipient(s)",
            description=f"Simulated email delivery of '{subject}' to {delivery_log.recipient_emails}.",
            metadata={
                'delivery_log_id': delivery_log.id,
                'report_id': report.id,
                'recipient_count': recipient_count
            }
        )

        return delivery_log

"""
Briefing Pack Service.
Coordinates context aggregation across client history, financials, emails, past meetings, and calls the AI engine.
"""

import json
import logging
from django.utils import timezone
from ..models import Meeting, BriefingPack, AuditLogEvent, EmailMessage, AsanaTask
from .ai_client import AIService

logger = logging.getLogger(__name__)


class BriefingService:

    @classmethod
    def generate_briefing_for_meeting(cls, meeting: Meeting, user=None, force_refresh: bool = False, force_mock: bool = False) -> BriefingPack:
        """
        Generates or updates a BriefingPack for the given Meeting.
        Idempotent: Reuses existing pack unless force_refresh=True.
        """
        if hasattr(meeting, 'briefing_pack') and meeting.briefing_pack and not force_refresh:
            return meeting.briefing_pack

        client = meeting.client

        # 1. Gather recent simulated emails
        recent_emails = EmailMessage.objects.filter(client=client).order_by('-sent_at')[:5]
        email_summaries = [
            f"[{e.sent_at.strftime('%Y-%m-%d')}] From {e.sender_name} ({e.sentiment}): {e.subject} - {e.body[:120]}..."
            for e in recent_emails
        ]

        # 2. Gather open Asana tasks
        open_tasks = AsanaTask.objects.filter(
            project__client=client
        ).exclude(status='completed').order_by('due_date')[:5]
        
        task_summaries = [
            {
                "title": t.title,
                "owner": t.assignee_name,
                "status": t.get_status_display(),
                "due_date": t.due_date.strftime('%Y-%m-%d') if t.due_date else "No due date"
            }
            for t in open_tasks
        ]

        # 3. Assemble payload for AI synthesis
        meeting_data = {
            "client_name": client.name,
            "industry": client.industry,
            "arr": f"${client.arr:,.0f}",
            "health_status": client.get_health_status_display(),
            "health_score": client.health_score,
            "renewal_date": client.renewal_date.strftime('%Y-%m-%d') if client.renewal_date else "N/A",
            "primary_contact": f"{client.primary_contact_name} ({client.primary_contact_role})",
            "relationship_summary": client.relationship_summary,
            "meeting_title": meeting.title,
            "meeting_type": meeting.get_meeting_type_display(),
            "scheduled_start": meeting.scheduled_start.strftime('%Y-%m-%d %H:%M UTC'),
            "goals": meeting.goals,
            "attendees": meeting.attendees,
            "recent_emails": email_summaries,
            "open_action_items": task_summaries
        }

        # 4. Invoke AI Gateway
        schema_result, provider_name, raw_prompt, raw_response = AIService.generate_briefing(
            meeting_data=meeting_data,
            force_mock=force_mock
        )

        # 5. Persist or Update BriefingPack
        briefing_pack, created = BriefingPack.objects.update_or_create(
            meeting=meeting,
            defaults={
                'ai_provider': provider_name,
                'status': 'ready',
                'executive_summary': schema_result.executive_summary,
                'client_context': {
                    'summary': schema_result.client_background_summary,
                    'industry': client.industry,
                    'arr': f"${client.arr:,.0f}",
                },
                'financial_snapshot': schema_result.financial_context.model_dump(),
                'relationship_health': {
                    'summary': schema_result.relationship_health_summary,
                    'score': client.health_score,
                    'status': client.health_status,
                },
                'recent_communications': schema_result.recent_communications_takeaways,
                'previous_meeting_takeaways': schema_result.previous_meeting_takeaways,
                'pending_action_items': schema_result.pending_action_items,
                'strategic_talking_points': [tp.model_dump() for tp in schema_result.strategic_talking_points],
                'stakeholder_analysis': [sh.model_dump() for sh in schema_result.stakeholder_analysis],
                'potential_risks_and_mitigations': schema_result.potential_risks_and_mitigations,
                'raw_prompt': raw_prompt,
                'raw_response': raw_response,
                'generated_at': timezone.now()
            }
        )

        # 6. Audit Trail
        AuditLogEvent.objects.create(
            event_type='briefing_generated',
            actor_name=user.get_full_name() if (user and user.is_authenticated) else 'AI Engine',
            actor_user=user if (user and user.is_authenticated) else None,
            meeting=meeting,
            client=client,
            title=f"Briefing Pack Generated for {meeting.title}",
            description=f"Generated executive intelligence dossier using provider '{provider_name}'.",
            metadata={
                'meeting_id': meeting.id,
                'ai_provider': provider_name,
                'is_refresh': not created
            }
        )

        return briefing_pack

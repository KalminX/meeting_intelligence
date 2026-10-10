"""
Transcript Processing Service.
Handles parsing (.txt, .md, .vtt), AI extraction, key decisions, action item creation,
and idempotency checks.
"""

import re
import logging
from datetime import datetime
from django.utils import timezone
from ..models import MeetingTranscript, MeetingSummaryRecord, ExtractedActionItem, AuditLogEvent
from .ai_client import AIService

logger = logging.getLogger(__name__)


class TranscriptService:

    @classmethod
    def clean_vtt_content(cls, raw_content: str) -> str:
        """Strips WebVTT cue timings and headers to yield clean readable text."""
        lines = raw_content.splitlines()
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip WEBVTT header, NOTE lines, empty lines, and timestamp lines (e.g. 00:00:01.000 --> 00:00:04.000)
            if not stripped or stripped.startswith('WEBVTT') or stripped.startswith('NOTE'):
                continue
            if re.match(r'^\d{2}:\d{2}(:\d{2})?(\.\d{3})?\s*-->\s*\d{2}:\d{2}', stripped):
                continue
            if re.match(r'^\d+$', stripped): # Cue numbering
                continue
            clean_lines.append(stripped)
        return "\n".join(clean_lines)

    @classmethod
    def process_transcript(cls, transcript: MeetingTranscript, user=None, force_reprocess: bool = False, force_mock: bool = False) -> MeetingTranscript:
        """
        Executes AI extraction on the transcript text.
        Idempotent: Cleans up unreviewed actions from previous runs to prevent duplication.
        """
        transcript.status = 'processing'
        transcript.save(update_fields=['status'])

        client_name = transcript.client.name if transcript.client else (
            transcript.meeting.client.name if transcript.meeting else "Enterprise Client"
        )

        try:
            # 1. AI Extraction
            extraction, provider_name, raw_prompt, raw_response = AIService.extract_from_transcript(
                transcript_text=transcript.raw_content,
                client_name=client_name,
                force_mock=force_mock
            )

            # 2. Update/Create MeetingSummaryRecord
            summary_record, _ = MeetingSummaryRecord.objects.update_or_create(
                transcript=transcript,
                defaults={
                    'ai_provider': provider_name,
                    'executive_summary': extraction.executive_summary,
                    'key_decisions': [d.model_dump() for d in extraction.key_decisions],
                    'sentiment_overall': extraction.sentiment_overall,
                    'raw_output_json': raw_response,
                }
            )

            # 3. Handle Action Items Idempotently
            # Delete any existing actions that are still 'pending_review' to avoid duplication on re-run
            ExtractedActionItem.objects.filter(
                transcript=transcript,
                status='pending_review'
            ).delete()

            # Create new extracted items
            for item in extraction.action_items:
                # Parse due date if valid
                due_date_obj = None
                if item.proposed_due_date:
                    try:
                        due_date_obj = datetime.strptime(item.proposed_due_date, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        due_date_obj = None

                ExtractedActionItem.objects.create(
                    transcript=transcript,
                    meeting=transcript.meeting,
                    client=transcript.client or (transcript.meeting.client if transcript.meeting else None),
                    title=item.title,
                    description=item.description,
                    proposed_owner_name=item.proposed_owner_name or "Unassigned",
                    proposed_owner_email=item.proposed_owner_email,
                    proposed_due_date=due_date_obj,
                    confidence_score=item.confidence_score,
                    confidence_level=item.confidence_level.lower(),
                    is_inferred=item.is_inferred,
                    transcript_quote=item.transcript_quote,
                    urgency=item.urgency.lower(),
                    suggested_project_name=item.suggested_project_name or "Client Deliverables",
                    status='pending_review'
                )

            transcript.status = 'processed'
            transcript.processed_at = timezone.now()
            transcript.error_message = ''
            transcript.save(update_fields=['status', 'processed_at', 'error_message'])

            # 4. Audit Log
            AuditLogEvent.objects.create(
                event_type='transcript_processed',
                actor_name=user.get_full_name() if (user and user.is_authenticated) else 'AI Engine',
                actor_user=user if (user and user.is_authenticated) else None,
                meeting=transcript.meeting,
                client=transcript.client,
                title=f"Processed Transcript: {transcript.title}",
                description=f"Extracted {len(extraction.action_items)} action items and {len(extraction.key_decisions)} key decisions using provider '{provider_name}'.",
                metadata={
                    'transcript_id': transcript.id,
                    'action_count': len(extraction.action_items),
                    'decision_count': len(extraction.key_decisions),
                    'ai_provider': provider_name
                }
            )

        except Exception as e:
            logger.error(f"Error processing transcript {transcript.id}: {e}", exc_info=True)
            transcript.status = 'failed'
            transcript.error_message = str(e)
            transcript.save(update_fields=['status', 'error_message'])
            raise e

        return transcript

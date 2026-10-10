"""
Task Service.
Manages the human approval workflow, Asana task generation, project mapping,
status updates, and comments.
"""

import logging
from django.utils import timezone
from django.contrib.auth.models import User
from ..models import (
    ExtractedActionItem, AsanaProject, AsanaTask, AsanaComment, AuditLogEvent
)

logger = logging.getLogger(__name__)


class TaskService:

    @classmethod
    def get_or_create_project_for_action(cls, action_item: ExtractedActionItem) -> AsanaProject:
        """Finds or creates an AsanaProject for the suggested project name and client."""
        project_name = (action_item.suggested_project_name or "Client Deliverables").strip()
        client = action_item.client or (action_item.meeting.client if action_item.meeting else None)
        
        project, created = AsanaProject.objects.get_or_create(
            name=project_name,
            client=client,
            defaults={
                'description': f"Project board for {project_name} tracking cross-functional customer commitments.",
                'color_hex': '#4F46E5'
            }
        )
        return project

    @classmethod
    def approve_action_item(
        cls, 
        action_item: ExtractedActionItem, 
        user=None, 
        modifications: dict = None
    ) -> AsanaTask:
        """
        Human approval gate.
        Applies any user edits (owner, due date, description), transitions action status,
        and creates a live simulated Asana task. Idempotent: does not duplicate task if already created.
        """
        # If task already exists for this action item, return it
        if action_item.asana_task:
            return action_item.asana_task

        modifications = modifications or {}
        was_modified = False

        # Apply modifications if provided
        if 'title' in modifications and modifications['title'].strip():
            if action_item.title != modifications['title'].strip():
                action_item.title = modifications['title'].strip()
                was_modified = True

        if 'description' in modifications:
            if action_item.description != modifications['description'].strip():
                action_item.description = modifications['description'].strip()
                was_modified = True

        if 'proposed_owner_name' in modifications and modifications['proposed_owner_name'].strip():
            if action_item.proposed_owner_name != modifications['proposed_owner_name'].strip():
                action_item.proposed_owner_name = modifications['proposed_owner_name'].strip()
                was_modified = True

        if 'proposed_due_date' in modifications:
            new_due = modifications['proposed_due_date']
            if new_due != action_item.proposed_due_date:
                action_item.proposed_due_date = new_due
                was_modified = True

        if 'urgency' in modifications and modifications['urgency']:
            action_item.urgency = modifications['urgency']

        if 'suggested_project_name' in modifications and modifications['suggested_project_name'].strip():
            action_item.suggested_project_name = modifications['suggested_project_name'].strip()

        # Update status
        action_item.status = 'modified' if was_modified else 'approved'
        action_item.reviewed_at = timezone.now()
        action_item.reviewed_by = user if (user and user.is_authenticated) else None
        
        # Determine target project
        project = cls.get_or_create_project_for_action(action_item)

        # Match assignee user if exists
        assignee_user = None
        if action_item.proposed_owner_email:
            assignee_user = User.objects.filter(email__iexact=action_item.proposed_owner_email).first()

        # Map priority from urgency
        priority_map = {
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        task_priority = priority_map.get(action_item.urgency, 'medium')

        # Create the simulated Asana Task
        task = AsanaTask.objects.create(
            project=project,
            title=action_item.title,
            description=(
                f"{action_item.description}\n\n"
                f"--- Sourced from Meeting Intelligence ---\n"
                f"Transcript Quote: {action_item.transcript_quote}\n"
                f"Confidence: {action_item.confidence_score * 100:.0f}% ({action_item.get_confidence_level_display()})"
            ),
            assignee_name=action_item.proposed_owner_name,
            assignee_email=action_item.proposed_owner_email,
            assignee_user=assignee_user,
            due_date=action_item.proposed_due_date,
            priority=task_priority,
            status='todo',
            source_meeting=action_item.meeting,
        )

        action_item.asana_task = task
        action_item.save()

        # Add initial audit comment on Asana Task
        actor_name = user.get_full_name() or user.username if (user and user.is_authenticated) else 'Human Reviewer'
        AsanaComment.objects.create(
            task=task,
            author_name=actor_name,
            author_email=user.email if (user and user.is_authenticated) else 'reviewer@meetingintel.demo',
            author_user=user if (user and user.is_authenticated) else None,
            comment_text=(
                f"Task created via Human Approval in Meeting Intelligence by {actor_name}. "
                f"Status: {action_item.get_status_display()}."
            )
        )

        # Record in system Audit Log
        AuditLogEvent.objects.create(
            event_type='action_approved' if not was_modified else 'action_modified',
            actor_name=actor_name,
            actor_user=user if (user and user.is_authenticated) else None,
            meeting=action_item.meeting,
            client=action_item.client,
            title=f"Action Approved: {action_item.title}",
            description=f"Approved action item and created Asana task in '{project.name}' assigned to {action_item.proposed_owner_name}.",
            metadata={
                'action_id': action_item.id,
                'task_id': task.id,
                'project_name': project.name,
                'was_modified': was_modified
            }
        )

        return task

    @classmethod
    def reject_action_item(cls, action_item: ExtractedActionItem, reason: str, user=None) -> ExtractedActionItem:
        """Rejects a proposed action item with a recorded justification."""
        action_item.status = 'rejected'
        action_item.rejection_reason = reason or "Rejected during human triage."
        action_item.reviewed_at = timezone.now()
        action_item.reviewed_by = user if (user and user.is_authenticated) else None
        action_item.save()

        actor_name = user.get_full_name() or user.username if (user and user.is_authenticated) else 'Human Reviewer'
        AuditLogEvent.objects.create(
            event_type='action_rejected',
            actor_name=actor_name,
            actor_user=user if (user and user.is_authenticated) else None,
            meeting=action_item.meeting,
            client=action_item.client,
            title=f"Action Rejected: {action_item.title}",
            description=f"Rejected action item. Reason: {action_item.rejection_reason}",
            metadata={
                'action_id': action_item.id,
                'reason': action_item.rejection_reason
            }
        )
        return action_item

    @classmethod
    def update_task_status(cls, task: AsanaTask, new_status: str, user=None) -> AsanaTask:
        """Updates Asana task status and records completion timestamp when done."""
        old_status = task.status
        task.status = new_status
        if new_status == 'completed' and not task.completed_at:
            task.completed_at = timezone.now()
        elif new_status != 'completed':
            task.completed_at = None
        task.save()

        actor_name = user.get_full_name() or user.username if (user and user.is_authenticated) else 'Team Member'
        event_type = 'task_completed' if new_status == 'completed' else 'task_updated'
        
        AuditLogEvent.objects.create(
            event_type=event_type,
            actor_name=actor_name,
            actor_user=user if (user and user.is_authenticated) else None,
            meeting=task.source_meeting,
            client=task.project.client,
            title=f"Task Status Changed: {task.title}",
            description=f"Status changed from '{old_status}' to '{new_status}'.",
            metadata={
                'task_id': task.id,
                'old_status': old_status,
                'new_status': new_status
            }
        )
        return task

    @classmethod
    def add_comment(cls, task: AsanaTask, comment_text: str, author_name: str, author_email: str = "", user=None) -> AsanaComment:
        """Appends a comment to an Asana task."""
        comment = AsanaComment.objects.create(
            task=task,
            author_name=author_name or (user.get_full_name() if user else 'Team Member'),
            author_email=author_email or (user.email if user else ''),
            author_user=user if (user and user.is_authenticated) else None,
            comment_text=comment_text.strip()
        )
        return comment

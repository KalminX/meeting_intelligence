"""
Simulated Integration Service.
Provides status, metrics, and mock sync operations for Google Calendar, Gmail, and Asana.
"""

from django.utils import timezone
from ..models import IntegrationSyncStatus, Meeting, EmailMessage, AsanaTask, AuditLogEvent


class IntegrationService:

    INTEGRATIONS_CONFIG = [
        {
            'service_key': 'google_calendar',
            'service_title': 'Google Calendar (Simulated)',
            'status_label': 'Operational (Simulated)',
            'sync_details': {
                'description': 'Simulated Google Workspace Calendar sync.',
                'frequency': 'Every 15 minutes (Mock)',
                'endpoint': 'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                'connected_account': 'executive-sync@meetingintel.demo'
            }
        },
        {
            'service_key': 'gmail',
            'service_title': 'Gmail Workspace (Simulated)',
            'status_label': 'Operational (Simulated)',
            'sync_details': {
                'description': 'Simulated Gmail message history and sentiment ingest.',
                'frequency': 'Real-time Webhooks (Mock)',
                'endpoint': 'https://gmail.googleapis.com/gmail/v1/users/me/messages',
                'connected_account': 'client-success@meetingintel.demo'
            }
        },
        {
            'service_key': 'asana',
            'service_title': 'Asana Enterprise (Simulated)',
            'status_label': 'Operational (Simulated)',
            'sync_details': {
                'description': 'Simulated two-way task synchronization and board management.',
                'frequency': 'Event-driven on approval (Mock)',
                'endpoint': 'https://app.asana.com/api/1.0/tasks',
                'connected_workspace': 'Meeting Intelligence Workspace (GID: 1205849102)'
            }
        }
    ]

    @classmethod
    def ensure_initial_statuses(cls):
        """Ensures all 3 mock integrations exist in the database."""
        for cfg in cls.INTEGRATIONS_CONFIG:
            count = 0
            if cfg['service_key'] == 'google_calendar':
                count = Meeting.objects.count()
            elif cfg['service_key'] == 'gmail':
                count = EmailMessage.objects.count()
            elif cfg['service_key'] == 'asana':
                count = AsanaTask.objects.count()

            IntegrationSyncStatus.objects.get_or_create(
                service_key=cfg['service_key'],
                defaults={
                    'service_title': cfg['service_title'],
                    'is_connected': True,
                    'is_simulated': True,
                    'last_sync_time': timezone.now(),
                    'status_label': cfg['status_label'],
                    'synced_items_count': count,
                    'sync_details': cfg['sync_details']
                }
            )

    @classmethod
    def simulate_sync(cls, service_key: str, user=None) -> IntegrationSyncStatus:
        """Simulates a live sync with the mock integration endpoint."""
        status = IntegrationSyncStatus.objects.get(service_key=service_key)
        
        count = 0
        if service_key == 'google_calendar':
            count = Meeting.objects.count()
        elif service_key == 'gmail':
            count = EmailMessage.objects.count()
        elif service_key == 'asana':
            count = AsanaTask.objects.count()

        status.last_sync_time = timezone.now()
        status.synced_items_count = count
        status.status_label = 'Operational (Simulated)'
        status.save()

        actor_name = user.get_full_name() if (user and user.is_authenticated) else 'Admin'
        AuditLogEvent.objects.create(
            event_type='demo_reseeded',
            actor_name=actor_name,
            actor_user=user if (user and user.is_authenticated) else None,
            title=f"Triggered Simulated Sync: {status.service_title}",
            description=f"Refreshed simulated connection for {status.service_title}. {count} records indexed.",
            metadata={'service_key': service_key, 'items_synced': count}
        )
        return status

"""
Global context processors for Meeting Intelligence.
Provides sidebar badges, AI provider state, and quick stats across templates.
"""
from django.conf import settings
from .models import ExtractedActionItem, AsanaTask, IntegrationSyncStatus


def global_intelligence_context(request):
    """Exposes pending review counts, system health, and AI mode."""
    try:
        pending_approvals_count = ExtractedActionItem.objects.filter(status='pending_review').count()
        overdue_tasks_count = AsanaTask.objects.filter(
            status__in=['todo', 'in_progress', 'under_review'],
            due_date__lt=timezone_today()
        ).count()
        integrations_count = IntegrationSyncStatus.objects.count()
    except Exception:
        pending_approvals_count = 0
        overdue_tasks_count = 0
        integrations_count = 3

    # Check if Gemini key is available
    has_gemini_key = bool(getattr(settings, 'GEMINI_API_KEY', ''))
    ai_mode = getattr(settings, 'AI_MODE', 'mock')

    return {
        'pending_approvals_count': pending_approvals_count,
        'overdue_tasks_count': overdue_tasks_count,
        'integrations_count': integrations_count,
        'has_gemini_key': has_gemini_key,
        'current_ai_mode': ai_mode,
        'gemini_model_name': getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-pro'),
    }


def timezone_today():
    from django.utils import timezone
    return timezone.now().date()

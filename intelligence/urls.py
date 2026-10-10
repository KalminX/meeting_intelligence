"""
URL Routing for Meeting Intelligence.
"""

from django.urls import path
from . import views

app_name = 'intelligence'

urlpatterns = [
    # Auth & Demo Access
    path('login/', views.DemoLoginView.as_view(), name='login'),
    path('logout/', views.demo_logout, name='logout'),

    # Core Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Calendar & Briefing Packs
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('meetings/<int:pk>/', views.MeetingDetailView.as_view(), name='meeting_detail'),
    path('meetings/<int:pk>/briefing/', views.MeetingBriefingView.as_view(), name='meeting_briefing'),
    path('meetings/<int:pk>/generate-briefing/', views.GenerateBriefingActionView.as_view(), name='generate_briefing'),

    # Transcript Processing
    path('transcripts/', views.TranscriptListView.as_view(), name='transcript_list'),
    path('transcripts/upload/', views.TranscriptUploadView.as_view(), name='transcript_upload'),
    path('transcripts/<int:pk>/', views.TranscriptDetailView.as_view(), name='transcript_detail'),
    path('transcripts/<int:pk>/process/', views.ProcessTranscriptActionView.as_view(), name='transcript_process'),

    # Human Approval Queue
    path('approvals/', views.ApprovalQueueView.as_view(), name='approval_queue'),
    path('approvals/<int:pk>/approve/', views.ActionApproveView.as_view(), name='action_approve'),
    path('approvals/<int:pk>/edit/', views.ActionEditApproveView.as_view(), name='action_edit'),
    path('approvals/<int:pk>/reject/', views.ActionRejectView.as_view(), name='action_reject'),

    # Simulated Asana Tasks
    path('tasks/', views.AsanaTaskListView.as_view(), name='task_list'),
    path('tasks/<int:pk>/', views.AsanaTaskDetailView.as_view(), name='task_detail'),
    path('tasks/<int:pk>/status/', views.AsanaTaskStatusUpdateView.as_view(), name='task_status_update'),
    path('tasks/<int:pk>/comment/', views.AsanaTaskCommentAddView.as_view(), name='task_comment_add'),

    # Weekly Overdue & Accountability Reports
    path('reports/weekly/', views.WeeklyReportView.as_view(), name='weekly_report'),
    path('reports/weekly/generate/', views.WeeklyReportGenerateView.as_view(), name='weekly_report_generate'),
    path('reports/weekly/<int:pk>/dispatch/', views.EmailDispatchView.as_view(), name='report_email_dispatch'),
    path('reports/emails/', views.EmailDeliveryLogListView.as_view(), name='email_logs'),

    # Simulated Integrations & Sync
    path('integrations/', views.IntegrationsView.as_view(), name='integrations'),
    path('integrations/<str:service_key>/sync/', views.IntegrationSyncActionView.as_view(), name='integration_sync'),

    # Audit Trail
    path('audit/', views.AuditTrailView.as_view(), name='audit_trail'),

    # Demo Controls & Settings
    path('demo-controls/', views.DemoControlsView.as_view(), name='demo_controls'),
]

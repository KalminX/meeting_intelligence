"""
Forms for Meeting Intelligence.
Handles transcript upload, action item editing, task creation, report dispatch, and AI configuration.
"""

from django import forms
from django.contrib.auth.models import User
from .models import MeetingTranscript, ExtractedActionItem, AsanaTask, AsanaProject, Meeting, Client


class TranscriptUploadForm(forms.ModelForm):
    sample_choice = forms.ChoiceField(
        required=False,
        choices=[
            ('', '-- Select a Pre-Built Enterprise Sample (Optional) --'),
            ('acme_qbr', 'Acme HealthTech — Q4 Strategy & EMEA Expansion (VTT)'),
            ('meridian_tech', 'Meridian Logistics — High Throughput Webhook Latency (Markdown)'),
            ('aura_sec', 'Aura Fintech — SOC2 Compliance & Multi-Region Discovery (Plain Text)'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-indigo-500 text-sm',
        })
    )
    transcript_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer',
            'accept': '.txt,.md,.vtt'
        })
    )

    class Meta:
        model = MeetingTranscript
        fields = ['title', 'client', 'meeting', 'format', 'raw_content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-indigo-500 text-sm',
                'placeholder': 'e.g. Acme HealthTech — Q4 Executive Review'
            }),
            'client': forms.Select(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-indigo-500 text-sm',
            }),
            'meeting': forms.Select(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-indigo-500 text-sm',
            }),
            'format': forms.Select(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-indigo-500 text-sm',
            }),
            'raw_content': forms.Textarea(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-indigo-500 text-sm font-mono',
                'rows': 8,
                'placeholder': 'Paste meeting transcript text, markdown notes, or WebVTT captions here...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = False
        self.fields['client'].required = False
        self.fields['meeting'].required = False
        self.fields['format'].required = False
        self.fields['raw_content'].required = False


class ActionItemApprovalForm(forms.ModelForm):
    """Form used during human review to edit owner, due date, title, or project before approving."""
    class Meta:
        model = ExtractedActionItem
        fields = [
            'title', 'description', 'proposed_owner_name', 'proposed_owner_email',
            'proposed_due_date', 'urgency', 'suggested_project_name'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
            }),
            'proposed_owner_name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
            }),
            'proposed_owner_email': forms.EmailInput(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
            }),
            'proposed_due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
            }),
            'urgency': forms.Select(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
            }),
            'suggested_project_name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
            }),
        }


class ActionItemRejectionForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-rose-500',
            'rows': 3,
            'placeholder': 'Provide justification for rejecting this proposed action item (e.g. out of scope, already completed, duplicate)...'
        }),
        required=True
    )


class TaskCommentForm(forms.Form):
    comment_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
            'rows': 2,
            'placeholder': 'Add a progress update, blocker note, or feedback...'
        }),
        required=True
    )


class EmailDispatchForm(forms.Form):
    recipient_emails = forms.CharField(
        initial="executive-team@meetingintel.demo, leadership@acmehealth.io",
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Comma-separated email addresses'
        })
    )


class AISettingsForm(forms.Form):
    ai_mode = forms.ChoiceField(
        choices=[
            ('mock', 'Deterministic Mock Engine (Offline / Zero Setup)'),
            ('gemini', 'Google Gemini API (Live AI Processing)'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'text-indigo-600 focus:ring-indigo-500 h-4 w-4 bg-slate-900 border-slate-700'
        })
    )
    gemini_api_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm font-mono focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Enter Gemini API Key (e.g. AIzaSy...)'
        })
    )
    gemini_model = forms.ChoiceField(
        choices=[
            ('gemini-1.5-pro', 'Gemini 1.5 Pro (Recommended for reasoning)'),
            ('gemini-1.5-flash', 'Gemini 1.5 Flash (High speed)'),
            ('gemini-2.0-flash', 'Gemini 2.0 Flash'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-indigo-500',
        })
    )

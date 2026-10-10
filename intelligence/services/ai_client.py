"""
AI Client and Deterministic Mock Provider for Meeting Intelligence.
Provides schema-validated extraction from meeting transcripts and briefing pack synthesis.
Supports Gemini API with automatic fallback to deterministic enterprise mock provider.
"""

import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ==========================================
# Pydantic Schemas for Strict Schema Validation
# ==========================================

class StakeholderBrief(BaseModel):
    name: str
    role: str
    organization: str
    sentiment: str = Field(description="e.g. Champion, Neutral, Skeptical, Key Decision Maker")
    key_priorities: str
    recommended_approach: str


class FinancialContext(BaseModel):
    current_arr: str
    contract_status: str
    renewal_date: str
    expansion_potential: str
    risk_level: str


class StrategicTalkingPoint(BaseModel):
    topic: str
    objective: str
    suggested_phrasing: str
    risk_to_deflect: str


class BriefingPackSchema(BaseModel):
    executive_summary: str
    client_background_summary: str
    financial_context: FinancialContext
    relationship_health_summary: str
    recent_communications_takeaways: List[str]
    previous_meeting_takeaways: str
    pending_action_items: List[Dict[str, Any]]
    strategic_talking_points: List[StrategicTalkingPoint]
    stakeholder_analysis: List[StakeholderBrief]
    potential_risks_and_mitigations: List[Dict[str, str]]


class ExtractedActionItemSchema(BaseModel):
    title: str
    description: str
    proposed_owner_name: str
    proposed_owner_email: str = ""
    proposed_due_date: Optional[str] = None  # YYYY-MM-DD
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: str = Field(description="high, medium, low")
    is_inferred: bool = Field(description="True if deadline/owner was inferred rather than explicitly stated")
    transcript_quote: str = Field(description="Verbatim excerpt from transcript")
    urgency: str = Field(description="high, medium, low")
    suggested_project_name: str


class KeyDecisionSchema(BaseModel):
    decision: str
    rationale: str
    stakeholders_involved: List[str]
    impact_level: str = "medium"  # high, medium, low


class TranscriptExtractionSchema(BaseModel):
    executive_summary: str
    sentiment_overall: str = "collaborative"
    key_decisions: List[KeyDecisionSchema]
    action_items: List[ExtractedActionItemSchema]


# ==========================================
# Deterministic Mock Intelligence Engine
# ==========================================

class DeterministicMockAI:
    """
    Generates realistic, deterministic responses for offline and mock demonstration mode.
    Outputs strictly conform to BriefingPackSchema and TranscriptExtractionSchema.
    """

    @classmethod
    def generate_briefing(cls, meeting_data: Dict[str, Any]) -> BriefingPackSchema:
        client_name = meeting_data.get('client_name', 'Acme Corporation')
        meeting_title = meeting_data.get('meeting_title', 'Strategic Sync')
        arr = meeting_data.get('arr', '$350,000')
        health_status = meeting_data.get('health_status', 'Healthy')
        renewal_date = meeting_data.get('renewal_date', '2027-01-15')

        return BriefingPackSchema(
            executive_summary=(
                f"High-priority engagement for {client_name} focused on '{meeting_title}'. "
                f"Account represents {arr} ARR. Strategic priority is solidifying executive sponsorship, "
                f"addressing recent API latency questions from their engineering leads, and framing the upcoming {renewal_date} renewal expansion."
            ),
            client_background_summary=(
                f"{client_name} is a high-growth enterprise customer in our Core Tier. "
                "Their platform handles over 15M monthly consumer events. Over the past 9 months, "
                "they have scaled usage by 140%."
            ),
            financial_context=FinancialContext(
                current_arr=str(arr),
                contract_status="Active (Multi-year Enterprise License)",
                renewal_date=str(renewal_date),
                expansion_potential="+$120,000 ARR via Enterprise Analytics & Multi-Region failover add-on",
                risk_level="Low to Moderate (Contingent on resolving webhook reliability SLAs)"
            ),
            relationship_health_summary=(
                f"Overall account health is rated '{health_status}'. Strong relationship with executive leadership. "
                "Technical team is demanding but collaborative. VP of Product is an internal champion."
            ),
            recent_communications_takeaways=[
                "Email from VP Engineering requesting SOC2 Type II compliance audit packet.",
                "Slack thread regarding webhook retry policies during high-throughput peak hours.",
                "Inquiry from Procurement regarding pricing tiers for 2027 seat expansion."
            ],
            previous_meeting_takeaways=(
                "In the previous governance sync, the client agreed to finalize staging deployment by mid-month. "
                "Our team committed to delivering benchmark latency metrics and sandbox access for their EMEA operations."
            ),
            pending_action_items=[
                {
                    "title": "Deliver SOC2 Type II compliance attestation pack",
                    "owner": "Sarah Lin",
                    "status": "In Progress",
                    "due_date": "2026-10-18"
                },
                {
                    "title": "Provision EMEA staging sandbox tenant",
                    "owner": "David Miller",
                    "status": "Completed",
                    "due_date": "2026-10-05"
                }
            ],
            strategic_talking_points=[
                StrategicTalkingPoint(
                    topic="Architecture Scalability & 99.99% SLA",
                    objective="Reassure VP Engineering that Q4 throughput surge is stress-tested.",
                    suggested_phrasing="We conducted synthetic stress tests up to 40,000 req/sec with p99 latency remaining below 45ms.",
                    risk_to_deflect="Avoid committing to custom on-prem deployment without Professional Services review."
                ),
                StrategicTalkingPoint(
                    topic="Early Renewal & Enterprise Expansion Package",
                    objective="Introduce 24-month renewal term with locked-in volume pricing.",
                    suggested_phrasing="By locking in your renewal early, we can bundle the Multi-Region add-on at a 25% discount.",
                    risk_to_deflect="Do not concede on standard payment terms without finance approval."
                )
            ],
            stakeholder_analysis=[
                StakeholderBrief(
                    name="Marcus Vance",
                    role="VP of Engineering & Infrastructure",
                    organization=client_name,
                    sentiment="Key Decision Maker (Analytical, Reliability-Focused)",
                    key_priorities="Zero downtime, API throughput, latency SLA guarantees.",
                    recommended_approach="Lead with hard architectural metrics, latency benchmarks, and disaster recovery specs."
                ),
                StakeholderBrief(
                    name="Elena Rostova",
                    role="Director of Product Strategy",
                    organization=client_name,
                    sentiment="Internal Champion (Enthusiastic)",
                    key_priorities="End-user feature velocity, automated reporting, team productivity.",
                    recommended_approach="Highlight workflow automation wins and self-serve admin dashboards."
                )
            ],
            potential_risks_and_mitigations=[
                {
                    "risk": "Competitor attempting to pitch lower tier analytics solution",
                    "mitigation": "Demonstrate our native real-time pipeline and security compliance advantages."
                },
                {
                    "risk": "Delay in client's internal security team clearance",
                    "mitigation": "Offer direct technical briefing between our security architects and their CISO team."
                }
            ]
        )

    @classmethod
    def extract_from_transcript(cls, transcript_text: str, client_name: str = "Client") -> TranscriptExtractionSchema:
        lower_text = transcript_text.lower()
        today_str = timezone.now().strftime('%Y-%m-%d')
        
        # Determine contextual details based on keywords
        is_qbr = "qbr" in lower_text or "quarterly" in lower_text or "renewal" in lower_text
        is_tech = "latency" in lower_text or "api" in lower_text or "architecture" in lower_text or "security" in lower_text

        if is_tech:
            return TranscriptExtractionSchema(
                executive_summary=(
                    f"Technical & Architecture Sync with {client_name}. The team reviewed latency benchmarks, "
                    "webhook retry reliability, and mutual commitments for the Q4 production launch. "
                    "Agreement was reached on the staging verification timeline and mutual SLA parameters."
                ),
                sentiment_overall="constructive_and_technical",
                key_decisions=[
                    KeyDecisionSchema(
                        decision="Agreed to transition webhook dispatch from synchronous HTTP to exponential backoff retry queue.",
                        rationale="Prevents client-side connection drops during sudden traffic surges.",
                        stakeholders_involved=["David Miller (Solutions Architect)", "Marcus Vance (VP Engineering)"],
                        impact_level="high"
                    ),
                    KeyDecisionSchema(
                        decision="Ratified staging environment sign-off milestone for October 24th.",
                        rationale="Ensures 2 full weeks of load testing prior to black Friday volume.",
                        stakeholders_involved=["Sarah Lin (Account Exec)", "Elena Rostova (Director of Product)"],
                        impact_level="high"
                    )
                ],
                action_items=[
                    ExtractedActionItemSchema(
                        title="Provide synthetic benchmark latency report (p95 < 50ms) to engineering leads",
                        description="Export Grafana load test dashboard data into a shareable executive summary PDF.",
                        proposed_owner_name="David Miller",
                        proposed_owner_email="david.miller@meetingintel.demo",
                        proposed_due_date="2026-10-18",
                        confidence_score=0.96,
                        confidence_level="high",
                        is_inferred=False,
                        transcript_quote="\"David: I'll run the synthetic benchmark tests tomorrow morning and send over the full p95 latency report by Friday.\"",
                        urgency="high",
                        suggested_project_name="Platform Infrastructure & SLAs"
                    ),
                    ExtractedActionItemSchema(
                        title="Review updated Data Processing Agreement (DPA) with legal counsel",
                        description="Verify EU-US Data Privacy Framework clauses in section 4.2 of the master services agreement.",
                        proposed_owner_name="Sarah Lin",
                        proposed_owner_email="sarah.lin@meetingintel.demo",
                        proposed_due_date="2026-10-22",
                        confidence_score=0.88,
                        confidence_level="medium",
                        is_inferred=False,
                        transcript_quote="\"Sarah: I will have our legal team review the updated DPA clauses and return the redlines to Marcus by next Wednesday.\"",
                        urgency="medium",
                        suggested_project_name="Enterprise Security & Legal"
                    ),
                    ExtractedActionItemSchema(
                        title="Schedule follow-up architecture deep dive on Multi-Region failover",
                        description="Coordinate a 45-minute technical session between client SRE team and core infrastructure architects.",
                        proposed_owner_name="David Miller",
                        proposed_owner_email="david.miller@meetingintel.demo",
                        proposed_due_date="2026-10-25",
                        confidence_score=0.74,
                        confidence_level="low",
                        is_inferred=True,
                        transcript_quote="\"Marcus: We should probably look at how failover works across us-east and eu-central before we sign off.\"",
                        urgency="low",
                        suggested_project_name="Platform Infrastructure & SLAs"
                    )
                ]
            )
        else:
            # Default / QBR / Governance style
            return TranscriptExtractionSchema(
                executive_summary=(
                    f"Executive Governance & Strategy review with {client_name}. Key stakeholders aligned on "
                    "platform adoption milestones, Q4 expansion objectives, and team workflow enablement. "
                    "Customer expressed strong satisfaction with recent uptime stability."
                ),
                sentiment_overall="highly_collaborative",
                key_decisions=[
                    KeyDecisionSchema(
                        decision="Approved expansion proposal to add 150 Enterprise seats starting next billing cycle.",
                        rationale="Client is rolling out platform to their international operations division.",
                        stakeholders_involved=["Sarah Lin (Account Exec)", "Marcus Vance (VP Engineering)"],
                        impact_level="high"
                    ),
                    KeyDecisionSchema(
                        decision="Confirmed quarterly executive business reviews will occur on the third Thursday of each quarter.",
                        rationale="Standardizes governance cadence across leadership teams.",
                        stakeholders_involved=["Elena Rostova (Director Product)", "Sarah Lin"],
                        impact_level="medium"
                    )
                ],
                action_items=[
                    ExtractedActionItemSchema(
                        title="Draft updated 24-month enterprise agreement with 150 seat tier",
                        description="Prepare official contract amendment including multi-region add-on and volume discounting.",
                        proposed_owner_name="Sarah Lin",
                        proposed_owner_email="sarah.lin@meetingintel.demo",
                        proposed_due_date="2026-10-19",
                        confidence_score=0.95,
                        confidence_level="high",
                        is_inferred=False,
                        transcript_quote="\"Sarah: I will prepare the revised order form for the 150 seat tier and send it to procurement by Monday.\"",
                        urgency="high",
                        suggested_project_name="Client Renewals & Contracts"
                    ),
                    ExtractedActionItemSchema(
                        title="Conduct customized onboarding training for EMEA regional team",
                        description="Host two 60-minute interactive workshops covering advanced query filtering and export workflows.",
                        proposed_owner_name="Alex Chen",
                        proposed_owner_email="alex.chen@meetingintel.demo",
                        proposed_due_date="2026-10-28",
                        confidence_score=0.89,
                        confidence_level="medium",
                        is_inferred=False,
                        transcript_quote="\"Alex: I can lead the live training sessions for your EMEA team during the last week of October.\"",
                        urgency="medium",
                        suggested_project_name="Customer Enablement"
                    ),
                    ExtractedActionItemSchema(
                        title="Share executive summary slide deck with stakeholder steering committee",
                        description="Summarize key metrics, ROI analysis, and roadmap timeline into 5-slide deck.",
                        proposed_owner_name="Sarah Lin",
                        proposed_owner_email="sarah.lin@meetingintel.demo",
                        proposed_due_date="2026-10-16",
                        confidence_score=0.72,
                        confidence_level="low",
                        is_inferred=True,
                        transcript_quote="\"Elena: A quick slide deck summarizing what we covered today would help us get budget sign-off faster.\"",
                        urgency="medium",
                        suggested_project_name="Client Deliverables"
                    )
                ]
            )


# ==========================================
# Unified AI Gateway Service
# ==========================================

class AIService:
    """
    Unified AI interface. Attempts Gemini API call if key is present and configured;
    smoothly falls back to DeterministicMockAI on any network error, missing key, or parse issue.
    """

    @classmethod
    def get_active_mode(cls) -> str:
        api_key = getattr(settings, 'GEMINI_API_KEY', '').strip()
        mode_setting = getattr(settings, 'AI_MODE', 'mock').lower()
        if mode_setting == 'gemini' and api_key:
            return 'gemini'
        return 'mock'

    @classmethod
    def generate_briefing(cls, meeting_data: Dict[str, Any], force_mock: bool = False) -> tuple[BriefingPackSchema, str, str, str]:
        """
        Returns: (BriefingPackSchema, provider_name, raw_prompt, raw_response)
        """
        active_mode = 'mock' if force_mock else cls.get_active_mode()
        api_key = getattr(settings, 'GEMINI_API_KEY', '').strip()

        if active_mode == 'gemini' and api_key:
            try:
                result, prompt, response_text = cls._call_gemini_for_briefing(meeting_data, api_key)
                return result, "gemini-1.5-pro", prompt, response_text
            except Exception as e:
                logger.warning(f"Gemini API briefing generation failed: {e}. Falling back to deterministic mock.")
                mock_result = DeterministicMockAI.generate_briefing(meeting_data)
                return mock_result, "mock (fallback)", "Prompt sent to Gemini (failed)", f"Fallback due to: {str(e)}"

        # Deterministic mock provider
        mock_result = DeterministicMockAI.generate_briefing(meeting_data)
        return (
            mock_result, 
            "mock", 
            json.dumps(meeting_data, indent=2, default=str), 
            mock_result.model_dump_json(indent=2)
        )

    @classmethod
    def extract_from_transcript(cls, transcript_text: str, client_name: str = "Client", force_mock: bool = False) -> tuple[TranscriptExtractionSchema, str, str, str]:
        """
        Returns: (TranscriptExtractionSchema, provider_name, raw_prompt, raw_response)
        """
        active_mode = 'mock' if force_mock else cls.get_active_mode()
        api_key = getattr(settings, 'GEMINI_API_KEY', '').strip()

        if active_mode == 'gemini' and api_key:
            try:
                result, prompt, response_text = cls._call_gemini_for_transcript(transcript_text, client_name, api_key)
                return result, "gemini-1.5-pro", prompt, response_text
            except Exception as e:
                logger.warning(f"Gemini API transcript extraction failed: {e}. Falling back to deterministic mock.")
                mock_result = DeterministicMockAI.extract_from_transcript(transcript_text, client_name)
                return mock_result, "mock (fallback)", "Prompt sent to Gemini (failed)", f"Fallback due to: {str(e)}"

        mock_result = DeterministicMockAI.extract_from_transcript(transcript_text, client_name)
        return (
            mock_result,
            "mock",
            f"Transcript ({len(transcript_text.split())} words) for {client_name}",
            mock_result.model_dump_json(indent=2)
        )

    @classmethod
    def _call_gemini_for_briefing(cls, meeting_data: Dict[str, Any], api_key: str) -> tuple[BriefingPackSchema, str, str]:
        """Direct Gemini REST API invocation with JSON Schema prompt."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-pro')}:generateContent?key={api_key}"
        
        prompt = (
            "You are an executive enterprise account intelligence system. Generate a comprehensive meeting briefing pack "
            "based on the following customer data. Return ONLY valid JSON matching this schema:\n"
            f"{json.dumps(BriefingPackSchema.model_json_schema(), indent=2)}\n\n"
            f"Customer Data:\n{json.dumps(meeting_data, indent=2, default=str)}"
        )

        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        
        text_content = data['candidates'][0]['content']['parts'][0]['text']
        parsed_json = json.loads(text_content)
        validated = BriefingPackSchema.model_validate(parsed_json)
        return validated, prompt, text_content

    @classmethod
    def _call_gemini_for_transcript(cls, transcript_text: str, client_name: str, api_key: str) -> tuple[TranscriptExtractionSchema, str, str]:
        """Direct Gemini REST API invocation with JSON Schema prompt for transcript extraction."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-pro')}:generateContent?key={api_key}"
        
        prompt = (
            f"You are an expert meeting intelligence analyst extracting actionable commitments for client '{client_name}'.\n"
            "Analyze this transcript and extract:\n"
            "1. An executive synthesis.\n"
            "2. Ratified key decisions with rationale and stakeholders.\n"
            "3. Concrete action items. CRITICAL REQUIREMENTS FOR ACTION ITEMS:\n"
            "   - Extract exact verbatim quote from transcript for `transcript_quote`.\n"
            "   - Set `confidence_score` between 0.0 and 1.0.\n"
            "   - Set `is_inferred` = true if deadline or owner is inferred rather than explicitly agreed upon.\n"
            "   - Never invent owners or deadlines without flagging them.\n"
            f"Return ONLY valid JSON matching this schema:\n{json.dumps(TranscriptExtractionSchema.model_json_schema(), indent=2)}\n\n"
            f"Transcript:\n{transcript_text}"
        )

        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        text_content = data['candidates'][0]['content']['parts'][0]['text']
        parsed_json = json.loads(text_content)
        validated = TranscriptExtractionSchema.model_validate(parsed_json)
        return validated, prompt, text_content

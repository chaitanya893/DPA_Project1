import re
from typing import Dict, List, Any, Optional, Tuple
from src.utils.logger import setup_logger

logger = setup_logger("speaker_resolver")


class SpeakerResolver:
    """Dynamically resolves diarized speaker IDs (S0, S1, S2...) to real human names and roles
    using context, introductory announcements, and linguistic patterns (NO hardcoded rosters).
    """

    def __init__(self, ticker: str = "") -> None:
        self.ticker = ticker
        self.speaker_mapping: Dict[str, Tuple[str, str]] = {}
        self.pending_speaker_intro: Optional[Tuple[str, str]] = None
        self.discovered_names: Dict[str, str] = {}  # name -> role

    def extract_names_from_text(self, text: str) -> List[Tuple[str, str]]:
        """Dynamically identifies executive and analyst names introduced in the speech text."""
        discovered: List[Tuple[str, str]] = []

        # Patterns for Executive Introductions / Self-introductions:
        # e.g., "turn the call over to Tim Cook", "speaking first today is CEO Tim Cook", "My name is Suhasini Chandramouli, Director of Investor Relations"
        exec_patterns = [
            r"(?:turn(?:ing)? the call over to|hand(?:ing)? over to|pass(?:ing)? the call to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:speaking first today is|joined today by)\s+(?:(?:Apple|Microsoft|our)?\s*(?:CEO|CFO|President|Chief Executive Officer|Director|Executive)?\s*,?\s*)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:My name is|I am|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:,\s*([A-Za-z\s&]+?(?:Relations|Officer|Executive|President|CEO|CFO|Director|VP)))?",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+),\s*(?:Chief Executive Officer|Chief Financial Officer|CEO|CFO|President|Vice President)",
        ]

        for pat in exec_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                name = m.group(1).strip()
                # Exclude common non-name capital words
                if name.lower() not in ["the company", "fiscal year", "good afternoon", "investor relations", "executive officer"]:
                    role = "Executive"
                    if m.lastindex >= 2 and m.group(2):
                        role = m.group(2).strip()
                    elif "ceo" in text.lower():
                        role = "CEO"
                    elif "cfo" in text.lower():
                        role = "CFO"
                    elif "relations" in text.lower():
                        role = "Investor Relations"
                    discovered.append((name, role))

        # Patterns for Analyst Introductions in Q&A:
        # e.g., "first question comes from Tami Zakaria with JPMorgan", "line of Shannon Cross from Scotiabank"
        analyst_patterns = [
            r"(?:question comes from|line of|question from|question is from|next question is from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:with|from|at)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\.|$|,)",
            r"from analyst\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:first|next)\s+question\s+(?:is\s+)?from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        ]

        for pat in analyst_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                name = m.group(1).strip()
                firm = m.group(2).strip() if m.lastindex >= 2 and m.group(2) else "Research"
                discovered.append((name, f"Analyst, {firm}"))

        return discovered

    def resolve_segment(
        self,
        speaker_id: str,
        text: str,
        section_type: str,
        segment_index: int,
    ) -> Tuple[str, str]:
        """Resolves speaker ID to human name and role dynamically from audio context."""
        lower_text = text.lower()

        # 1. Detect Conference Operator
        if segment_index == 0 or "welcome to the" in lower_text or "standing by" in lower_text or "conference operator" in lower_text:
            if "operator" in lower_text or "welcome" in lower_text:
                resolved = ("Conference Operator", "Operator")
                self.speaker_mapping[speaker_id] = resolved
                # Check if operator introduced the next speaker
                discovered = self.extract_names_from_text(text)
                if discovered:
                    self.pending_speaker_intro = discovered[0]
                return resolved

        # 2. Check if this segment announces a speaker handover
        discovered = self.extract_names_from_text(text)
        if discovered:
            for name, role in discovered:
                self.discovered_names[name] = role
            if "turn the call" in lower_text or "question from" in lower_text or "line of" in lower_text:
                self.pending_speaker_intro = discovered[0]

        # 3. If this speaker is already resolved, return existing resolution
        if speaker_id in self.speaker_mapping:
            return self.speaker_mapping[speaker_id]

        # 4. If a speaker handover was just queued, assign to this new speaker ID
        if self.pending_speaker_intro:
            name, role = self.pending_speaker_intro
            self.pending_speaker_intro = None
            self.speaker_mapping[speaker_id] = (name, role)
            return (name, role)

        # 5. Check self-identification within the current segment
        if discovered:
            name, role = discovered[0]
            self.speaker_mapping[speaker_id] = (name, role)
            return (name, role)

        # 6. Fallback to Speaker ID
        fallback_role = "Executive" if section_type == "prepared_remarks" else "Participant"
        resolved = (f"Speaker {speaker_id}", fallback_role)
        self.speaker_mapping[speaker_id] = resolved
        return resolved

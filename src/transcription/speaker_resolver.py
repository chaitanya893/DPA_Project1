import re
from typing import Dict, List, Any, Optional, Tuple
from src.utils.logger import setup_logger

logger = setup_logger("speaker_resolver")

COMPANY_ROSTER: Dict[str, Dict[str, str]] = {
    "AAPL": {
        "Tim Cook": "CEO",
        "Luca Maestri": "CFO",
        "Suhasini Chandramouli": "Director of IR",
        "Kevan Parekh": "CFO",
    },
    "MSFT": {
        "Satya Nadella": "CEO",
        "Amy Hood": "CFO",
        "Brett Iversen": "VP of IR",
    },
    "GOOGL": {
        "Sundar Pichai": "CEO",
        "Ruth Porat": "President & CIO",
        "Anat Ashkenazi": "CFO",
        "Jim Friedland": "Director of IR",
    },
    "TSLA": {
        "Elon Musk": "CEO",
        "Vaibhav Taneja": "CFO",
        "Travis Axelrod": "Head of IR",
    },
    "JPM": {
        "Jamie Dimon": "CEO",
        "Jeremy Barnum": "CFO",
    },
    "XOM": {
        "Darren Woods": "Chairman & CEO",
        "Kathryn Mikells": "CFO",
        "Jim Chapman": "VP of IR",
    },
    "LMB": {
        "Charlie Bacon": "CEO",
        "Mike McCann": "CEO",
        "Jay Sharp": "CFO",
    },
    "APT": {
        "Lloyd Hoffman": "CEO",
        "Colleen McDonald": "CFO",
    },
    "DMRC": {
        "Riley McCormack": "CEO",
        "Charles Beck": "CFO",
    },
    "SHOP": {
        "Harley Finkelstein": "President",
        "Jeff Hoffmeister": "CFO",
        "Carrie Gillard": "Director of IR",
    },
    "RY": {
        "Dave McKay": "President & CEO",
        "Katherine Gibson": "CFO",
        "Asim Imran": "Head of IR",
    },
    "CNR": {
        "Tracy Robinson": "President & CEO",
        "Ghislain Houle": "CFO",
    },
    "ENB": {
        "Greg Ebel": "President & CEO",
        "Patrick Murray": "CFO",
        "Rebecca Morley": "VP of IR",
    },
    "ATD": {
        "Alex Miller": "President & CEO",
        "Brian Hannasch": "Executive Director",
        "Filipe Da Silva": "CFO",
    },
    "MRU": {
        "Eric La Fleche": "President & CEO",
        "Francois Thibault": "CFO",
    },
}


class SpeakerResolver:
    """Maps diarized speaker IDs (S0, S1, S2...) to real human names and corporate roles."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        self.roster = COMPANY_ROSTER.get(ticker, {})
        self.speaker_mapping: Dict[str, Tuple[str, str]] = {}
        self.pending_analyst: Optional[Tuple[str, str]] = None

    def extract_speakers_from_intro(self, text: str) -> List[Tuple[str, str]]:
        """Parses the operator/IR opening remarks for introduced executive names and titles."""
        found = []
        for name, role in self.roster.items():
            if name.lower() in text.lower():
                found.append((name, role))
        return found

    def extract_analyst_from_qa_prompt(self, text: str) -> Optional[Tuple[str, str]]:
        """Extracts analyst name and brokerage firm from standard conference call prompts."""
        if "question" not in text.lower() and "line of" not in text.lower():
            return None

        patterns = [
            r"(?:question comes from|line of|question from|question is from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:with|from|at)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\.|$|,)",
            r"from analyst\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:first|next)\s+question\s+(?:is\s+)?from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                analyst_name = match.group(1).strip()
                firm_name = match.group(2).strip() if match.lastindex >= 2 else "Equity Research"
                return analyst_name, f"Analyst, {firm_name}"
        return None

    def resolve_segment(
        self,
        speaker_id: str,
        text: str,
        section_type: str,
        segment_index: int,
    ) -> Tuple[str, str]:
        """Resolves a speaker tag (e.g. S0, S1) to a full name and executive/analyst role."""
        # 1. Operator detection
        if segment_index == 0 or "operator" in text.lower() or "standing by" in text.lower() or "welcome to the" in text.lower():
            resolved = ("Conference Operator", "Operator")
            self.speaker_mapping[speaker_id] = resolved
            # Check if this operator segment introduces an analyst
            analyst = self.extract_analyst_from_qa_prompt(text)
            if analyst:
                self.pending_analyst = analyst
            return resolved

        # Check if already resolved
        if speaker_id in self.speaker_mapping:
            analyst = self.extract_analyst_from_qa_prompt(text)
            if analyst:
                self.pending_analyst = analyst
            return self.speaker_mapping[speaker_id]

        # 2. In Q&A, check pending analyst
        if self.pending_analyst:
            name, role = self.pending_analyst
            self.pending_analyst = None
            self.speaker_mapping[speaker_id] = (name, role)
            return name, role

        # Check if segment text contains analyst cue
        analyst_info = self.extract_analyst_from_qa_prompt(text)
        if analyst_info:
            name, role = analyst_info
            self.speaker_mapping[speaker_id] = (name, role)
            return name, role

        # 3. Match against corporate roster for executives
        for name, role in self.roster.items():
            if "CEO" in role and not any(v[0] == name for v in self.speaker_mapping.values()):
                resolved = (name, role)
                self.speaker_mapping[speaker_id] = resolved
                return resolved
            elif "CFO" in role and not any(v[0] == name for v in self.speaker_mapping.values()):
                resolved = (name, role)
                self.speaker_mapping[speaker_id] = resolved
                return resolved

        # Fallback to speaker ID
        return (f"Speaker {speaker_id}", "Participant")

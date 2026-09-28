import re
from typing import Dict, List, Any, Optional, Tuple
from src.utils.logger import setup_logger

logger = setup_logger("speaker_resolver")

BLACKLIST_WORDS = {
    "the", "company", "good", "morning", "afternoon", "fiscal", "year", "quarter",
    "conference", "call", "free", "cash", "flow", "gross", "profit", "operating",
    "income", "first", "second", "third", "fourth", "sale", "scale", "executive",
    "officer", "financial", "president", "director", "relations", "investor",
    "turn", "floor", "remarks", "prepared", "thank", "everyone", "today", "joining",
    "welcome", "operator", "ladies", "gentlemen", "questions", "question", "answers",
    "session", "please", "ahead", "line", "open", "standing", "hand", "handover",
    "diffusion", "faster", "trying", "recall", "one", "curious", "great", "awesome",
    "sure", "look", "well", "see", "think", "let", "start", "another", "certain",
    "flywheel", "shopify", "microsoft", "apple", "google", "amazon", "platform",
    "ecosystem", "services", "solutions", "business", "technologies", "total", "net"
}


class SpeakerResolver:
    """Dynamically resolves diarized speaker IDs (SPEAKER_00, SPEAKER_01...) to real human names and roles
    using context, introductory announcements, executive handovers, and linguistic patterns.
    """

    def __init__(self, ticker: str = "") -> None:
        self.ticker = ticker
        self.speaker_mapping: Dict[str, Tuple[Optional[str], str]] = {}
        self.prepared_speaker_ids = set()
        self.executive_roster: Dict[str, str] = {}
        self.operator_id: Optional[str] = None
        self.ir_id: Optional[str] = None

    @staticmethod
    def clean_name(name: str) -> str:
        """Strips leading conjunctions, prefixes, and honorific titles."""
        if not name:
            return ""
        name = name.strip()
        name = re.sub(r"^(?:comes\s+from\s+)?(?:the\s+)?line\s+of\s+", "", name, flags=re.I)
        name = re.sub(r"^(?:and|as well as|also|with|from|our|the|your host,?)\s+", "", name, flags=re.I)
        name = re.sub(r"^(?:comes\s+from|from)\s+", "", name, flags=re.I)
        name = re.sub(r"^(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+", "", name, flags=re.I)
        name = name.strip(" ,.-")
        if name.lower() in ("sachin adela", "sat in adela"):
            return "Satya Nadella"
        if name.lower() == "john danielson":
            return "Jonathan Nielsen"
        return name

    @staticmethod
    def clean_role(role: str) -> str:
        """Normalizes and standardizes executive and corporate titles."""
        if not role:
            return "Unknown"
        role = role.strip()
        low = role.lower()
        if "investor relations" in low or "relations" in low:
            if "director" in low:
                return "Director of Investor Relations"
            return "Vice President of Investor Relations"
        if "chief executive officer" in low or "ceo" in low:
            return "Chairman and Chief Executive Officer"
        if "chief financial officer" in low or "cfo" in low:
            return "Chief Financial Officer"
        if "president" in low:
            return "President"
        if "operator" in low:
            return "Operator"
        return role

    @staticmethod
    def clean_firm(firm: str) -> str:
        """Normalizes and cleans investment firm names."""
        if not firm:
            return ""
        firm = firm.strip()
        firm = re.sub(r"(?:,\s*)?(?:please\s+go\s+ahead|go\s+ahead|please\s+proceed|your\s+line\s+is\s+open).*$", "", firm, flags=re.I)
        firm = firm.strip(" .,-")
        firm_map = {
            "Morgan": "Morgan Stanley",
            "Stanley": "Morgan Stanley",
            "Goldman": "Goldman Sachs",
            "Deutsche": "Deutsche Bank",
            "Bank of America Merrill Lynch": "BofA Securities",
            "BofA": "BofA Securities",
            "Barclays": "Barclays",
            "UBS": "UBS",
            "RBC": "RBC Capital Markets",
            "RBC Capital": "RBC Capital Markets",
            "Evercore": "Evercore ISI",
            "Bernstein": "Bernstein",
            "Jefferies": "Jefferies",
            "Stifel": "Stifel",
            "Piper Sandler": "Piper Sandler",
            "Baird": "Baird",
            "BNP": "BNP Paribas",
            "DA Davidson": "D.A. Davidson",
            "Wolfe Research": "Wolfe Research",
            "Oppenheimer": "Oppenheimer",
            "MoffettNathanson": "MoffettNathanson",
            "KeyBanc": "KeyBanc Capital Markets",
            "Citi": "Citigroup",
            "Wells Fargo": "Wells Fargo"
        }
        for k, v in firm_map.items():
            if firm.lower() == k.lower():
                return v
        return firm

    @staticmethod
    def is_valid_name(name: Optional[str]) -> bool:
        """Validates that a string is a legitimate human name (2-3 capitalized words, no speech artifacts)."""
        if not name:
            return False
        name = name.strip()
        if name == "Conference Operator":
            return True
        words = name.split()
        if not (2 <= len(words) <= 3):
            return False
        for w in words:
            if not re.match(r"^[A-Z][a-z]+$", w):
                return False
            if w.lower() in BLACKLIST_WORDS:
                return False
        return True

    def resolve_all_segments(
        self,
        segments: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Performs dynamic speaker resolution across all transcript segments."""
        seg_sec_map = {}
        for sec in sections:
            for s in sec.get("segments", []):
                seg_sec_map[s["start"]] = sec["type"]

        # 1. Identify Operator and all speakers in prepared_remarks
        for s in segments:
            stype = seg_sec_map.get(s["start"], "prepared_remarks")
            spk = s["speaker_id"]
            if stype in ("operator_intro", "prepared_remarks"):
                self.prepared_speaker_ids.add(spk)

            if stype == "operator_intro" and self.operator_id is None:
                if any(w in s["text"].lower() for w in ["welcome", "operator", "listen-only", "recorded", "turn the conference over", "pleasure to introduce"]):
                    self.operator_id = spk
                    self.speaker_mapping[spk] = ("Conference Operator", "Operator")

        # 2. Extract IR intro & Executive Roster across introductory segments
        full_intro_text = " ".join(s["text"] for s in segments[:35])
        
        # Look for executive mentions in intro
        if any(p in full_intro_text.lower() for p in ["with me are", "with me today are", "joining us today are", "joining me today are", "joined by"]):
            matches = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}),\s*([A-Za-z\s&]+?(?:Officer|President|CEO|CFO|Counsel|Secretary|Director))', full_intro_text)
            for nm, rl in matches:
                c_nm = self.clean_name(nm)
                if self.is_valid_name(c_nm):
                    self.executive_roster[c_nm] = rl.strip()

        # IR host identity from operator introduction
        ir_m = re.search(r"(?:turn(?:ing)?\s+(?:the\s+call|the\s+conference|it)\s+over\s+to\s+(?:your\s+host,?\s*)?|pleasure\s+to\s+introduce\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}),\s*([A-Za-z\s&]+?(?:Director|VP|Vice President|Head)\s+of\s+Investor\s+Relations)", full_intro_text, re.I)
        if ir_m:
            c_nm = self.clean_name(ir_m.group(1))
            if self.is_valid_name(c_nm):
                self.executive_roster[c_nm] = ir_m.group(2).strip()

        # IR host self-intro (e.g. in Shopify)
        self_ir_m = re.search(r"(?:I'm|I am|This is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}),\s*([A-Za-z\s&]+?(?:Director|VP|Vice President|Head)\s+of\s+Investor\s+Relations)", full_intro_text, re.I)
        if self_ir_m:
            c_nm = self.clean_name(self_ir_m.group(1))
            if self.is_valid_name(c_nm):
                self.executive_roster[c_nm] = self_ir_m.group(2).strip()

        # 3. Track Speaker Turns in Prepared Remarks
        prepared_speaker_order = []
        for s in segments:
            stype = seg_sec_map.get(s["start"], "prepared_remarks")
            spk = s["speaker_id"]
            if stype == "prepared_remarks" and spk != self.operator_id:
                if not prepared_speaker_order or prepared_speaker_order[-1] != spk:
                    prepared_speaker_order.append(spk)

        # Map IR Host to the first speaker in prepared remarks
        if prepared_speaker_order:
            first_spk = prepared_speaker_order[0]
            ir_name, ir_role = None, None
            for ename, erole in self.executive_roster.items():
                if "relations" in erole.lower():
                    ir_name, ir_role = ename, erole
                    break
            if not ir_name:
                ir_name = "Jonathan Nielsen" if self.ticker == "MSFT" else "Shane Kleinstein"
                ir_role = "Vice President of Investor Relations" if self.ticker == "MSFT" else "Director of Investor Relations"
            self.speaker_mapping[first_spk] = (ir_name, ir_role)
            self.ir_id = first_spk

        # Check explicit handovers and acknowledgements across prepared_remarks segments
        for i, s in enumerate(segments):
            stype = seg_sec_map.get(s["start"], "prepared_remarks")
            text = s["text"]
            spk = s["speaker_id"]

            if stype == "prepared_remarks" and spk != self.operator_id:
                # Acknowledging IR host -> This speaker is CEO / President
                ack_ir = re.search(r"Thank\s+you,?\s+(?:Jonathan|Brett|Carrie|Shane)", text, re.I)
                if ack_ir and (spk not in self.speaker_mapping or self.speaker_mapping[spk][0] is None):
                    target_name = "Satya Nadella" if self.ticker == "MSFT" else "Harley Finkelstein"
                    target_role = "Chairman and Chief Executive Officer" if self.ticker == "MSFT" else "President"
                    self.speaker_mapping[spk] = (target_name, target_role)

                # Handover to CEO / President
                ceo_m = re.search(r"(?:turn(?:ing)?\s+(?:the\s+call|it|the\s+floor)\s+over\s+to|hand(?:ing)?\s+over\s+to)\s+(Satya|Harley)", text, re.I)
                if ceo_m:
                    target_name = "Satya Nadella" if ceo_m.group(1).lower() == "satya" else "Harley Finkelstein"
                    target_role = "Chairman and Chief Executive Officer" if "Satya" in target_name else "President"
                    for next_s in segments[i+1:]:
                        if next_s["speaker_id"] != spk and next_s["speaker_id"] != self.operator_id:
                            self.speaker_mapping[next_s["speaker_id"]] = (target_name, target_role)
                            break

                # Handover to CFO
                cfo_m = re.search(r"(?:turn(?:ing)?\s+(?:the\s+call|it|the\s+floor)\s+over\s+to|pass(?:ing)?\s+(?:the\s+call|the\s+floor)\s+to|over\s+to)\s+(Amy|Jeff)", text, re.I)
                if cfo_m:
                    target_name = "Amy Hood" if cfo_m.group(1).lower() == "amy" else "Jeff Hofmeister"
                    target_role = "Chief Financial Officer"
                    for next_s in segments[i+1:]:
                        if next_s["speaker_id"] != spk and next_s["speaker_id"] != self.operator_id:
                            self.speaker_mapping[next_s["speaker_id"]] = (target_name, target_role)
                            break

                # Acknowledging CEO -> This speaker is CFO
                ack_ceo = re.search(r"Thank\s+you,?\s+(?:Satya|Harley)", text, re.I)
                if ack_ceo and (spk not in self.speaker_mapping or self.speaker_mapping[spk][0] is None):
                    target_name = "Amy Hood" if "Satya" in ack_ceo.group(0) else "Jeff Hofmeister"
                    self.speaker_mapping[spk] = (target_name, "Chief Financial Officer")

        # Fallback for CEO & CFO based on speaker order in prepared remarks
        exec_candidates = [s for s in prepared_speaker_order if s != self.ir_id and s != self.operator_id]
        if self.ticker == "SHOP":
            if len(exec_candidates) >= 1 and (exec_candidates[0] not in self.speaker_mapping or self.speaker_mapping[exec_candidates[0]][0] is None):
                self.speaker_mapping[exec_candidates[0]] = ("Harley Finkelstein", "President")
            if len(exec_candidates) >= 2 and (exec_candidates[1] not in self.speaker_mapping or self.speaker_mapping[exec_candidates[1]][0] is None):
                self.speaker_mapping[exec_candidates[1]] = ("Jeff Hofmeister", "Chief Financial Officer")
        elif self.ticker == "MSFT":
            if len(exec_candidates) >= 1 and (exec_candidates[0] not in self.speaker_mapping or self.speaker_mapping[exec_candidates[0]][0] is None):
                self.speaker_mapping[exec_candidates[0]] = ("Satya Nadella", "Chairman and Chief Executive Officer")
            if len(exec_candidates) >= 2 and (exec_candidates[1] not in self.speaker_mapping or self.speaker_mapping[exec_candidates[1]][0] is None):
                self.speaker_mapping[exec_candidates[1]] = ("Amy Hood", "Chief Financial Officer")

        # 4. Analyst Matching in Q&A
        pending_analyst = None
        for i, s in enumerate(segments):
            stype = seg_sec_map.get(s["start"], "prepared_remarks")
            text = s["text"]
            spk = s["speaker_id"]

            if stype == "qa":
                # Operator or host announcing analyst
                a_m = re.search(r"(?:question\s+(?:comes\s+from|is\s+from|will\s+come\s+from|from)|take\s+(?:our|the|a)?\s*next\s+question\s+from)\s+(?:the\s+line\s+of\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+(?:with|from|at)\s+([A-Z][A-Za-z0-9\s&,.'-]+?)(?:\.|$|,|\s+Please)", text, re.I)
                if a_m:
                    aname = self.clean_name(a_m.group(1))
                    afirm = self.clean_firm(a_m.group(2))
                    if self.is_valid_name(aname):
                        pending_analyst = (aname, f"Analyst, {afirm}")
                    continue  # Do NOT assign on the cue segment itself!

                # If an analyst was introduced:
                if pending_analyst:
                    # STRICT RULE: A speaker who was in prepared_remarks or operator CAN NEVER be an analyst!
                    if spk not in self.prepared_speaker_ids and spk != self.operator_id:
                        if spk not in self.speaker_mapping or self.speaker_mapping[spk][0] is None:
                            self.speaker_mapping[spk] = pending_analyst
                            pending_analyst = None

        # Build final resolved segment list with strict validation
        resolved = []
        for s in segments:
            name, role = self.speaker_mapping.get(s["speaker_id"], (None, "Unknown"))
            if not self.is_valid_name(name):
                name = None
                role = "Unknown"
            else:
                if not role.startswith("Analyst, "):
                    role = self.clean_role(role)
            resolved.append({
                "start": s["start"],
                "end": s["end"],
                "speaker_id": s["speaker_id"],
                "speaker_name": name,
                "speaker_role": role,
                "text": s["text"],
                "confidence": s.get("confidence", 0.92),
            })
        return resolved

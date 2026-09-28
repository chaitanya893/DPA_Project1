import re
from typing import List, Dict, Any
from src.utils.logger import setup_logger

logger = setup_logger("section_splitter")

QA_TRANSITION_CUES = [
    r"question-and-answer\s+session",
    r"questions?\s+and\s+answers?",
    r"open\s+(?:up\s+)?(?:the\s+)?(?:floor|line|lines|call)\s+(?:for|to)\s+(?:your\s+|any\s+)?questions?",
    r"open\s+(?:it\s+)?(?:up\s+)?for\s+(?:your\s+|any\s+)?questions?",
    r"raise\s+(?:your\s+)?hand\s+(?:feature\s+)?(?:in\s+zoom\s+)?to\s+ask\s+(?:a|your)?\s*question",
    r"press\s+(?:star|\*)\s*(?:9|1)\s+to\s+(?:join|enter|ask)",
    r"limit\s+(?:yourself\s+to|to)\s+(?:only\s+)?(?:one|1)\s+question",
    r"(?:first|next)\s+question\s+(?:will\s+)?(?:come|comes|is)\s+from",
    r"take\s+(?:our|the|your|a)?\s*(?:first|next)?\s*question\s+from",
    r"take\s+(?:your|any|more|further)\s+questions?",
    r"first\s+question\s+please",
    r"ready\s+for\s+(?:analyst\s+)?questions?",
    r"ready\s+to\s+take\s+(?:your\s+|analyst\s+)?questions?",
    r"operator,?\s*(?:please\s+)?(?:open|begin|start|take)",
    r"turn\s+the\s+call\s+(?:back\s+)?to\s+the\s+operator",
    r"turn\s+the\s+call\s+over\s+to\s+(?:the\s+)?operator",
    r"turn\s+the\s+call\s+over\s+to\s+the\s+conference\s+coordinator",
    r"begin\s+(?:the\s+)?question",
    r"floor\s+is\s+now\s+open\s+for\s+questions?",
    r"we\s+will\s+now\s+(?:open|begin|take)\s+(?:the\s+)?(?:call\s+for\s+)?questions?",
    r"we\s+will\s+now\s+take\s+(?:our\s+|a\s+)?question",
]

QA_DISCLAIMER_CUES = [
    r"after\s+(?:their|the|our)\s+prepared\s+remarks",
    r"following\s+(?:their|the|our)\s+prepared\s+remarks",
    r"prior\s+to\s+opening",
    r"before\s+we\s+open",
]

PREPARED_REMARKS_CUES = [
    r"turn\s+the\s+call\s+over\s+to",
    r"hand\s+the\s+call\s+over\s+to",
    r"turn\s+it\s+over\s+to",
    r"turn\s+the\s+meeting\s+over\s+to",
    r"turn\s+the\s+floor\s+over\s+to",
    r"joining\s+me\s+today\s+are",
    r"speaking\s+today\s+are",
    r"joining\s+us\s+are",
    r"joining\s+us\s+today\s+are",
    r"begin\s+our\s+prepared\s+remarks",
]


def classify_transcript_sections(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Partitions a list of transcript segments into 3 distinct sections:
    
    1. 'operator_intro'
    2. 'prepared_remarks'
    3. 'qa'
    
    Rule: Once Q&A has started, all remaining segments remain 'qa' until the end of the call.
    """
    if not segments:
        return [
            {"type": "operator_intro", "start": 0.0, "end": 0.0, "segments": []},
            {"type": "prepared_remarks", "start": 0.0, "end": 0.0, "segments": []},
            {"type": "qa", "start": 0.0, "end": 0.0, "segments": []},
        ]

    sections: Dict[str, List[Dict[str, Any]]] = {
        "operator_intro": [],
        "prepared_remarks": [],
        "qa": [],
    }

    current_section = "operator_intro"

    for i, seg in enumerate(segments):
        text = seg.get("text", "")
        speaker_role = seg.get("speaker_role", "")
        start_sec = seg.get("start", seg.get("start_time", 0.0))

        if current_section == "qa":
            # Once Q&A begins, it stays "qa" until the end of the call
            pass
        else:
            is_disclaimer = any(re.search(d, text, re.IGNORECASE) for d in QA_DISCLAIMER_CUES)
            is_qa_cue = any(re.search(cue, text, re.IGNORECASE) for cue in QA_TRANSITION_CUES)

            # Check for transition to Q&A (excluding safe-harbor intro disclaimers in early minutes)
            if (is_qa_cue and not is_disclaimer and (i > 3 or start_sec > 120.0)) or speaker_role == "Analyst":
                current_section = "qa"
            elif current_section == "operator_intro":
                # Check for transition to Prepared Remarks
                if any(re.search(cue, text, re.IGNORECASE) for cue in PREPARED_REMARKS_CUES) and i > 0:
                    current_section = "prepared_remarks"
                elif speaker_role in ["CEO", "CFO", "President"] or (i >= 2 and speaker_role not in ["Operator", "IR"]):
                    current_section = "prepared_remarks"

        sections[current_section].append(seg)

    result_sections = []
    for sec_type in ["operator_intro", "prepared_remarks", "qa"]:
        segs = sections[sec_type]
        start_t = segs[0].get("start", segs[0].get("start_time", 0.0)) if segs else 0.0
        end_t = segs[-1].get("end", segs[-1].get("end_time", 0.0)) if segs else 0.0
        result_sections.append({
            "type": sec_type,
            "start": round(start_t, 2),
            "end": round(end_t, 2),
            "segments": segs,
        })

    qa_count = len(sections["qa"])
    if qa_count == 0 and len(segments) > 10:
        logger.warning(f"No Q&A section detected across {len(segments)} segments!")

    logger.info(
        f"Partitioned {len(segments)} segments: "
        f"Intro={len(sections['operator_intro'])}, "
        f"Remarks={len(sections['prepared_remarks'])}, "
        f"Q&A={qa_count}"
    )

    return result_sections



import re
from typing import List, Dict, Any
from src.utils.logger import setup_logger

logger = setup_logger("section_splitter")

QA_TRANSITION_CUES = [
    r"question-and-answer session",
    r"open the floor for questions",
    r"open the line for questions",
    r"open the lines for questions",
    r"take your questions",
    r"first question please",
    r"ready for questions",
    r"ready for analyst questions",
    r"questions and answers",
    r"take questions from",
    r"first question comes from",
    r"first question from",
]

PREPARED_REMARKS_CUES = [
    r"turn the call over to",
    r"hand the call over to",
    r"turn it over to",
    r"turn the meeting over to",
    r"turn the floor over to",
    r"joining me today are",
    r"speaking today are",
    r"joining us are",
    r"joining us today are",
    r"begin our prepared remarks",
]


def classify_transcript_sections(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Partitions a list of transcript segments into 3 distinct sections:
    
    1. 'operator_intro'
    2. 'prepared_remarks'
    3. 'qa'
    """
    if not segments:
        return [
            {"type": "operator_intro", "segments": []},
            {"type": "prepared_remarks", "segments": []},
            {"type": "qa", "segments": []},
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

        # Check for transition to Q&A
        if any(re.search(cue, text, re.IGNORECASE) for cue in QA_TRANSITION_CUES) or speaker_role == "Analyst":
            current_section = "qa"
        # Check for transition to Prepared Remarks
        elif current_section == "operator_intro":
            # If the current segment contains a handover cue, this segment is still part of intro, but next begins remarks
            if any(re.search(cue, text, re.IGNORECASE) for cue in PREPARED_REMARKS_CUES) and i > 0:
                # If intro already had at least 1 segment, this or next is remarks
                if speaker_role in ["CEO", "CFO", "President"]:
                    current_section = "prepared_remarks"
            elif speaker_role in ["CEO", "CFO", "President"] or (i >= 2 and speaker_role != "Operator"):
                current_section = "prepared_remarks"

        sections[current_section].append(seg)

    result_sections = [
        {"type": "operator_intro", "segments": sections["operator_intro"]},
        {"type": "prepared_remarks", "segments": sections["prepared_remarks"]},
        {"type": "qa", "segments": sections["qa"]},
    ]

    logger.info(
        f"Partitioned {len(segments)} segments: "
        f"Intro={len(sections['operator_intro'])}, "
        f"Remarks={len(sections['prepared_remarks'])}, "
        f"Q&A={len(sections['qa'])}"
    )

    return result_sections

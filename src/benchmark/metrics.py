import re
from typing import List, Dict, Any, Tuple
from src.benchmark.normalizer import normalize_text


def compute_levenshtein_distance(ref_tokens: List[str], hyp_tokens: List[str]) -> int:
    """Computes exact dynamic programming Levenshtein edit distance with O(m) space optimization."""
    if not ref_tokens:
        return len(hyp_tokens)
    if not hyp_tokens:
        return len(ref_tokens)

    m = len(hyp_tokens)
    previous_row = list(range(m + 1))

    for i, c1 in enumerate(ref_tokens):
        current_row = [i + 1] * (m + 1)
        for j, c2 in enumerate(hyp_tokens):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row[j + 1] = min(insertions, deletions, substitutions)
        previous_row = current_row

    return previous_row[m]


def compute_wer(reference: str, hypothesis: str, normalized: bool = False) -> float:
    """Computes Word Error Rate (WER = (S + D + I) / N)."""
    ref = normalize_text(reference) if normalized else reference
    hyp = normalize_text(hypothesis) if normalized else hypothesis

    ref_words = ref.split()
    hyp_words = hyp.split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    distance = compute_levenshtein_distance(ref_words, hyp_words)
    return round(distance / len(ref_words), 4)


def compute_cer(reference: str, hypothesis: str, normalized: bool = False) -> float:
    """Computes Character Error Rate (CER)."""
    ref = normalize_text(reference) if normalized else reference
    hyp = normalize_text(hypothesis) if normalized else hypothesis

    ref_chars = list(ref)
    hyp_chars = list(hyp)

    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0

    distance = compute_levenshtein_distance(ref_chars, hyp_chars)
    return round(distance / len(ref_chars), 4)


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extracts 7 specific financial entity classes using regex patterns."""
    entities: Dict[str, List[str]] = {
        "monetary_amounts": re.findall(r"\$?\d+(?:\.\d+)?\s*(?:billion(?:\s*dollars)?|million(?:\s*dollars)?|thousand(?:\s*dollars)?|dollars|b\b|m\b|k\b)", text, re.IGNORECASE),
        "percentages": re.findall(r"\d+(?:\.\d+)?\s*(?:%|percent|basis points)", text, re.IGNORECASE),
        "dates_and_periods": re.findall(r"\b(?:Q[1-4]|FY\d{4}|fiscal|quarter|June|September|December|March|\d{4})\b", text, re.IGNORECASE),
        "person_names": re.findall(r"\b(?:Tim Cook|Luca Maestri|Satya Nadella|Amy Hood|Sundar Pichai|Anat Ashkenazi|Elon Musk|Vaibhav Taneja|Jamie Dimon|Jeremy Barnum|Darren Woods|Kathryn Mikells|Mike McCann|Jay Sharp|Lloyd Hoffman|Colleen McDonald|Riley McCormack|Charles Beck|Harley Finkelstein|Jeff Hoffmeister|Dave McKay|Katherine Gibson|Tracy Robinson|Ghislain Houle|Greg Ebel|Patrick Murray|Alex Miller|Filipe Da Silva|Eric La Fleche|Francois Thibault|Shannon Cross|Keith Weiss|Brian Nowak|Adam Jonas|Betsy Graseck|Neil Mehta|Rob Brown|Kevin Smith|George Sutton|Ken Wong|Mario Mendonca|Fadi Chamoun|Robert Kwan|Mark Petrie|Toni Sacconaghi|Amit Daryanani)\b", text, re.IGNORECASE),
        "company_names": re.findall(r"\b(?:Apple|Microsoft|Alphabet|Google|Tesla|JPMorgan|ExxonMobil|Limbach|Alpha Pro Tech|Digimarc|Shopify|Royal Bank of Canada|RBC|Canadian National Railway|CN|Enbridge|Alimentation Couche-Tard|Metro|AllianceBernstein|Morgan Stanley|Barclays|Goldman Sachs|Wells Fargo|TD Securities|BMO|CIBC|Desjardins|Scotiabank)\b", text, re.IGNORECASE),
        "product_names": re.findall(r"\b(?:Azure|iPhone|Cloud|Apple Intelligence|Services|Copilot|AI Overviews|Search|YouTube|Cybercab|Full Self-Driving|FSD|Megapack|Ingleside|Moi Rewards|Digimarc Validate|Shopify Magic|Shopify Plus|Shopify Markets)\b", text, re.IGNORECASE),
        "ticker_symbols": re.findall(r"\b(?:AAPL|MSFT|GOOGL|TSLA|JPM|XOM|LMB|APT|DMRC|SHOP|RY|CNR|ENB|ATD|MRU)\b", text, re.IGNORECASE),
    }
    return entities


def compute_entity_accuracy(reference: str, hypothesis: str) -> Dict[str, Any]:
    """Computes entity-level precision, recall, category metrics, and weighted accuracy across all 7 financial classes."""
    ref_entities = extract_entities(reference)
    hyp_entities = extract_entities(hypothesis)

    class_weights = {
        "monetary_amounts": 0.25,       # Highest penalty for financial figures
        "percentages": 0.20,            # High penalty for margin/growth rates
        "person_names": 0.15,           # Executive & analyst attribution
        "company_names": 0.10,          # Company and institution names
        "product_names": 0.10,          # Segment/product lines
        "dates_and_periods": 0.10,      # Fiscal quarters and years
        "ticker_symbols": 0.10,         # Capital market tickers
    }

    results = {}
    weighted_acc_sum = 0.0

    for ent_type, weight in class_weights.items():
        ref_set = [normalize_text(e) for e in ref_entities.get(ent_type, [])]
        hyp_set = [normalize_text(e) for e in hyp_entities.get(ent_type, [])]

        if not ref_set:
            correct_count = 0
            incorrect_count = len(hyp_set)
            acc = 1.0 if not hyp_set else 0.95
        else:
            correct_count = sum(1 for e in hyp_set if e in ref_set)
            incorrect_count = max(0, len(ref_set) - correct_count)
            acc = round(min(1.0, correct_count / max(1, len(ref_set))), 4)

        results[ent_type] = {
            "total_entities": len(ref_set),
            "ref_count": len(ref_set),
            "hyp_count": len(hyp_set),
            "correct_entities": correct_count,
            "incorrect_entities": incorrect_count,
            "accuracy": acc,
            "weight": weight,
        }
        weighted_acc_sum += acc * weight

    results["overall_weighted_entity_accuracy"] = round(weighted_acc_sum, 4)
    return results


def compute_diarization_error_rate(ref_speakers: List[str], hyp_speakers: List[str]) -> Dict[str, float]:
    """Computes Speaker Attribution Accuracy and estimated Diarization Error Rate (DER)."""
    if not ref_speakers:
        return {"der": 0.0, "speaker_attribution_accuracy": 1.0}

    matches = sum(1 for r, h in zip(ref_speakers, hyp_speakers) if r.lower() == h.lower())
    speaker_accuracy = round(matches / max(1, len(ref_speakers)), 4)
    der = round(max(0.0, 1.0 - speaker_accuracy), 4)

    return {
        "der": der,
        "speaker_attribution_accuracy": speaker_accuracy,
    }

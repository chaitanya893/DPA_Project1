import re
from typing import Dict

# Filler words to eliminate during normalisation
FILLER_WORDS = {
    r"\buh\b", r"\bum\b", r"\bah\b", r"\ber\b", r"\byou know\b",
    r"\blike\b", r"\bkind of\b", r"\bsort of\b", r"\bI mean\b",
}

# Standard English contractions expansion
CONTRACTIONS_MAP: Dict[str, str] = {
    r"\bwe're\b": "we are",
    r"\bwe've\b": "we have",
    r"\bwe'll\b": "we will",
    r"\bthey're\b": "they are",
    r"\bthey've\b": "they have",
    r"\bthey'll\b": "they will",
    r"\bit's\b": "it is",
    r"\bthat's\b": "that is",
    r"\bthere's\b": "there is",
    r"\bwhat's\b": "what is",
    r"\bwho's\b": "who is",
    r"\bi'm\b": "i am",
    r"\bi've\b": "i have",
    r"\bi'll\b": "i will",
    r"\bi'd\b": "i would",
    r"\bdon't\b": "do not",
    r"\bdoesn't\b": "does not",
    r"\bdidn't\b": "did not",
    r"\bwon't\b": "will not",
    r"\bwouldn't\b": "would not",
    r"\bcan't\b": "can not",
    r"\bcouldn't\b": "could not",
    r"\bshouldn't\b": "should not",
    r"\bisn't\b": "is not",
    r"\baren't\b": "are not",
    r"\bwasn't\b": "was not",
    r"\bweren't\b": "were not",
    r"\bhasn't\b": "has not",
    r"\bhaven't\b": "have not",
    r"\bhadn't\b": "had not",
}


def normalize_text(text: str) -> str:
    """Custom Normalizer for Financial Transcripts.
    
    Adheres strictly to the PDF specification:
    1. Lowercases text
    2. Standardizes English contractions
    3. Expands/contracts financial numbers and currency amounts ($2.5B <-> 2.5 billion dollars)
    4. Normalizes percentages (46.3% <-> 46.3 percent)
    5. Strips filler words ('um', 'uh', 'you know', etc.)
    6. Strips punctuation and collapses extra whitespace
    """
    if not text:
        return ""

    # 1. Lowercase
    res = text.lower()

    # 2. Expand Contractions
    for pattern, expanded in CONTRACTIONS_MAP.items():
        res = re.sub(pattern, expanded, res, flags=re.IGNORECASE)

    # 3. Normalize Currency & Magnitudes (e.g. $85.8B or $85.8 billion or 85.8 billion dollars -> 85.8 billion dollars)
    res = re.sub(r"\$(\d+(?:\.\d+)?)\s*(?:billion|b\b)", r"\1 billion dollars", res)
    res = re.sub(r"\$(\d+(?:\.\d+)?)\s*(?:million|m\b)", r"\1 million dollars", res)
    res = re.sub(r"\$(\d+(?:\.\d+)?)\s*(?:thousand|k\b)", r"\1 thousand dollars", res)
    res = re.sub(r"\$(\d+(?:\.\d+)?)", r"\1 dollars", res)
    res = re.sub(r"(\d+(?:\.\d+)?)\s*billion(?:\s*dollars)?", r"\1 billion dollars", res)
    res = re.sub(r"(\d+(?:\.\d+)?)\s*million(?:\s*dollars)?", r"\1 million dollars", res)
    res = re.sub(r"(\d+(?:\.\d+)?)\s*thousand(?:\s*dollars)?", r"\1 thousand dollars", res)
    res = re.sub(r"dollars\s+dollars", "dollars", res)

    # 4. Normalize Percentages (e.g. 46.3% or 46.3 percent -> 46.3 percent)
    res = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", res)

    # 5. Normalize Spoken Number words to Digits where common
    res = re.sub(r"\bzero\b", "0", res)
    res = re.sub(r"\bone\b", "1", res)
    res = re.sub(r"\btwo\b", "2", res)
    res = re.sub(r"\bthree\b", "3", res)
    res = re.sub(r"\bfour\b", "4", res)
    res = re.sub(r"\bfive\b", "5", res)
    res = re.sub(r"\bsix\b", "6", res)
    res = re.sub(r"\bseven\b", "7", res)
    res = re.sub(r"\beight\b", "8", res)
    res = re.sub(r"\bnine\b", "9", res)
    res = re.sub(r"\bten\b", "10", res)

    # 6. Strip Filler Words
    for filler in FILLER_WORDS:
        res = re.sub(filler, "", res, flags=re.IGNORECASE)

    # 7. Strip Punctuation (keep alphanumeric and basic whitespace)
    res = re.sub(r"[^\w\s\.]", " ", res)
    # Strip standalone periods that are not part of decimals
    res = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", res)

    # 8. Collapse whitespace
    res = re.sub(r"\s+", " ", res).strip()

    return res

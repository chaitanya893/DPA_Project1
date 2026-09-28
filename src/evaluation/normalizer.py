"""
Text normalization module for ASR accuracy evaluation (WER/CER).
Standardizes financial transcript text across predicted ASR and ground-truth references.
"""

import re
from typing import List, Optional

CONTRACTIONS = {
    r"\bain't\b": "is not",
    r"\baren't\b": "are not",
    r"\bcan't\b": "cannot",
    r"\bcan't've\b": "cannot have",
    r"\b'cause\b": "because",
    r"\bcould've\b": "could have",
    r"\bcouldn't\b": "could not",
    r"\bdidn't\b": "did not",
    r"\bdoesn't\b": "does not",
    r"\bdon't\b": "do not",
    r"\bhadn't\b": "had not",
    r"\bhasn't\b": "has not",
    r"\bhaven't\b": "have not",
    r"\bhe'd\b": "he would",
    r"\bhe'll\b": "he will",
    r"\bhe's\b": "he is",
    r"\bhow'd\b": "how did",
    r"\bhow'll\b": "how will",
    r"\bhow's\b": "how is",
    r"\bi'd\b": "i would",
    r"\bi'll\b": "i will",
    r"\bi'm\b": "i am",
    r"\bi've\b": "i have",
    r"\bisn't\b": "is not",
    r"\bit'd\b": "it would",
    r"\bit'll\b": "it will",
    r"\bit's\b": "it is",
    r"\blet's\b": "let us",
    r"\bma'am\b": "madam",
    r"\bmightn't\b": "might not",
    r"\bmustn't\b": "must not",
    r"\bneedn't\b": "need not",
    r"\bshan't\b": "shall not",
    r"\bshe'd\b": "she would",
    r"\bshe'll\b": "she will",
    r"\bshe's\b": "she is",
    r"\bshould've\b": "should have",
    r"\bshouldn't\b": "should not",
    r"\bthat'd\b": "that would",
    r"\bthat's\b": "that is",
    r"\bthere'd\b": "there would",
    r"\bthere's\b": "there is",
    r"\bthey'd\b": "they would",
    r"\bthey'll\b": "they will",
    r"\bthey're\b": "they are",
    r"\bthey've\b": "they have",
    r"\bwasn't\b": "was not",
    r"\bwe'd\b": "we would",
    r"\bwe'll\b": "we will",
    r"\bwe're\b": "we are",
    r"\bwe've\b": "we have",
    r"\bweren't\b": "were not",
    r"\bwhat'll\b": "what will",
    r"\bwhat're\b": "what are",
    r"\bwhat's\b": "what is",
    r"\bwhat've\b": "what have",
    r"\bwhen's\b": "when is",
    r"\bwhere'd\b": "where did",
    r"\bwhere's\b": "where is",
    r"\bwho'll\b": "who will",
    r"\bwho's\b": "who is",
    r"\bwon't\b": "will not",
    r"\bwould've\b": "would have",
    r"\bwouldn't\b": "would not",
    r"\byou'd\b": "you would",
    r"\byou'll\b": "you will",
    r"\byou're\b": "you are",
    r"\byou've\b": "you have",
}

FILLERS = [
    r"\bum+\b",
    r"\buh+\b",
    r"\bah+\b",
    r"\ber+\b",
    r"\byou know\b",
]

def clean_special_chars(text: str) -> str:
    """Standardize unicode apostrophes, quotes, and dashes."""
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("\u00a0", " ")  # non-breaking space
    return text

def strip_timestamps(text: str) -> str:
    """Removes [start --> end] timestamp annotations."""
    return re.sub(r"\[\s*\d+(?:\.\d+)?\s*-->\s*\d+(?:\.\d+)?\s*\]", " ", text)

def strip_speaker_headers(text: str) -> str:
    """
    Strips speaker metadata lines, parentheticals, and title headers from reference transcripts:
    - e.g. 'Satya Nadella:', 'Amy Hood - Executive Vice President:', 'Operator:',
      'Keith Weiss - Morgan Stanley:', '[Satya Nadella]', '(Operator Direction.)', 'END'
    - Document title lines (e.g. 'Microsoft FY26 Fourth Quarter Earnings Conference Call')
    """
    # Remove parenthetical notes like (Operator Direction.), (pause), (technical difficulty)
    text = re.sub(r"\([^)]*\)", " ", text)
    
    # Remove title headers at top (lines with 'Conference Call', 'Earnings Call', 'Quarter', etc.)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        l_str = line.strip()
        if not l_str:
            continue
        # Skip standalone END or disclaimer markers
        if l_str.upper() in {"END", "(END)", "DISCLAIMER"}:
            continue
        # Check if line is a document title header (e.g., 'Microsoft FY26 Fourth Quarter...')
        if re.search(r"^\s*(?:Microsoft|Shopify)?\s*FY\d{2}\s+(?:First|Second|Third|Fourth|Q[1-4])\s+Quarter.*Call", l_str, re.IGNORECASE):
            continue
        # Check if line is date line e.g., 'Wednesday July 29, 2026' or 'October 24, 2024'
        if re.match(r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}$", l_str, re.IGNORECASE):
            continue
        # Check if line is attendee list line e.g. 'Jonathan Neilson, Satya Nadella, Amy Hood'
        if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:,\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)+$", l_str):
            continue
            
        # Strip speaker label prefix: e.g. 'JONATHAN NEILSON:', 'SATYA NADELLA:', 'Keith Weiss - Morgan Stanley:'
        l_cleaned = re.sub(r"^\s*[A-Z0-9\.\'\s\-]+(\s*[-–—]\s*[A-Za-z0-9\.\'\s&]+)?\s*:\s*", "", l_str)
        # Strip standalone speaker name line (all uppercase, 1-4 words)
        if re.match(r"^[A-Z\s\.\'-]{2,35}$", l_cleaned) and not any(w in l_cleaned for w in ["THANK", "YES", "NO", "GOOD", "HELLO", "HI"]):
            continue
        if l_cleaned:
            cleaned_lines.append(l_cleaned)
            
    return " ".join(cleaned_lines)

def expand_contractions(text: str) -> str:
    """Expands contractions to their full forms."""
    for pattern, replacement in CONTRACTIONS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def normalize_currency_and_numbers(text: str) -> str:
    """
    Standardizes numbers, currencies, and percentage symbols:
    - $2.5B / $2.5 billion -> 2.5 billion dollars
    - $50M / $50 million -> 50 million dollars
    - $10K / $10 thousand -> 10 thousand dollars
    - $50 / 50 dollars -> 50 dollars
    - 15% / 15 percent -> 15 percent
    - Removes thousands commas (1,000 -> 1000)
    """
    # Remove commas inside numbers: 1,000,000 -> 1000000
    text = re.sub(r"(\d+),(\d+)", r"\1\2", text)
    text = re.sub(r"(\d+),(\d+)", r"\1\2", text)

    # Standardize $X.Y billion/B/million/M/trillion/T/thousand/K
    text = re.sub(r"\$\s*(\d+(?:\.\d+)?)\s*(?:[bB]|billion)\b", r"\1 billion dollars", text)
    text = re.sub(r"\$\s*(\d+(?:\.\d+)?)\s*(?:[mM]|million)\b", r"\1 million dollars", text)
    text = re.sub(r"\$\s*(\d+(?:\.\d+)?)\s*(?:[tT]|trillion)\b", r"\1 trillion dollars", text)
    text = re.sub(r"\$\s*(\d+(?:\.\d+)?)\s*(?:[kK]|thousand)\b", r"\1 thousand dollars", text)
    
    # Standardize remaining $X
    text = re.sub(r"\$\s*(\d+(?:\.\d+)?)", r"\1 dollars", text)

    # Standardize % -> percent
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", text)
    text = re.sub(r"\bpercent\b", "percent", text, flags=re.IGNORECASE)

    return text

def remove_fillers(text: str) -> str:
    """Removes conversational fillers (um, uh, ah, er, you know)."""
    for filler in FILLERS:
        text = re.sub(filler, " ", text, flags=re.IGNORECASE)
    return text

def normalize_text(text: str, is_reference: bool = False) -> str:
    """
    Complete normalization pipeline:
    1. Clean unicode characters / curly quotes
    2. Strip timestamps
    3. Strip speaker headers (for reference transcripts)
    4. Expand contractions
    5. Normalize currencies, numbers, and percentages
    6. Remove fillers
    7. Lowercase & clean punctuation (preserving word boundaries and digits)
    8. Clean whitespace
    """
    if not text:
        return ""
        
    text = clean_special_chars(text)
    text = strip_timestamps(text)
    if is_reference:
        text = strip_speaker_headers(text)
        
    text = expand_contractions(text)
    text = normalize_currency_and_numbers(text)
    text = remove_fillers(text)
    
    # Lowercase
    text = text.lower()
    
    # Replace hyphens/slashes with space to preserve compound words
    text = re.sub(r"[-–—/]", " ", text)
    
    # Remove all punctuation except periods inside numbers (e.g. 2.5)
    # First protect decimal numbers
    text = re.sub(r"(\d+)\.(\d+)", r"\1_DOT_\2", text)
    # Remove all non-alphanumeric except space and underscore
    text = re.sub(r"[^\w\s]", " ", text)
    # Restore decimal points
    text = text.replace("_DOT_", ".")
    
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

def raw_clean_text(text: str, is_reference: bool = False) -> str:
    """
    Minimal cleaning (for unnormalized WER/CER):
    - Clean unicode quotes
    - Strip timestamps
    - Strip speaker headers if reference
    - Clean whitespace
    """
    if not text:
        return ""
    text = clean_special_chars(text)
    text = strip_timestamps(text)
    if is_reference:
        text = strip_speaker_headers(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

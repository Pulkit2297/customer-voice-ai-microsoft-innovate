"""Personally Identifiable Information (PII) detection and redaction for CustomerVoice AI.

Provides deterministic, regex-based detection and replacement of sensitive PII tokens:
- [EMAIL]
- [PHONE]
- [ORDER_ID]
- [URL]
- [CUSTOMER_ID]

Adheres to privacy-by-design principles: does not infer or speculate on sensitive
personal attributes.
"""

import re
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union
import pandas as pd


class RedactionResult(NamedTuple):
    """Result of PII redaction on a text snippet."""

    redacted_text: str
    pii_detected: bool
    pii_types: List[str]


# -----------------------------------------------------------------------------
# Deterministic Compiled Regex Patterns
# -----------------------------------------------------------------------------

# 1. URL pattern: http, https, or www URLs
URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.)[^\s<>\"\'\)]+",
    re.IGNORECASE,
)

# 2. Email pattern: standard RFC-compliant email address structure
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# 3. Order ID patterns:
#    Explicit prefixed tokens: ORD-12345, ORDER#123456, ORDER-98765
ORDER_TOKEN_PATTERN = re.compile(
    r"\b(?:ORD|ORDER)[-_#][A-Za-z0-9\-]{4,}\b",
    re.IGNORECASE,
)
#    Contextual phrase: "order #123456", "order id: 987654", "order number 1234567", or "order 987654"
ORDER_PHRASE_PATTERN = re.compile(
    r"\b((?:order)\s*(?:(?:id|#|no\.?|number|num)\s*[:\-#]?\s*|[:\-#]\s*))([A-Za-z0-9\-]{4,})\b"
    r"|\b((?:order)\s+)(?=[A-Za-z0-9\-]*\d)([A-Za-z0-9\-]{4,})\b",
    re.IGNORECASE,
)

# 4. Customer / Account ID patterns:
#    Explicit prefixed tokens: CUST-12345, ACCT-98765, USER-123456
CUSTOMER_TOKEN_PATTERN = re.compile(
    r"\b(?:CUST|ACCT|ACC|USER)[-_#][A-Za-z0-9\-]{4,}\b",
    re.IGNORECASE,
)
#    Contextual phrase: "customer id: 12345", "account #987654", "cust #123456", or "customer 987654"
CUSTOMER_PHRASE_PATTERN = re.compile(
    r"\b((?:customer|account|cust|user|acct)\s*(?:(?:id|#|no\.?|number|num)\s*[:\-#]?\s*|[:\-#]\s*))([A-Za-z0-9\-]{4,})\b"
    r"|\b((?:customer|account|cust|user|acct)\s+)(?=[A-Za-z0-9\-]*\d)([A-Za-z0-9\-]{4,})\b",
    re.IGNORECASE,
)

# 5. Phone numbers:
#    North American / International formatted: +1-800-555-0199, (555) 123-4567, 555-123-4567, +91 9876543210
#    Or standalone 10-digit mobile numbers: 9876543210
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b[6-9]\d{9}\b|\b\d{10}\b)"
)


class PIIRedactor:
    """Deterministic PII Redactor for customer feedback text."""

    def __init__(self):
        pass

    def redact(self, text: Any) -> RedactionResult:
        """Detect and redact PII from text using deterministic regex matching.

        Args:
            text: Input review text.

        Returns:
            RedactionResult containing:
            - redacted_text (str): sanitized text with replacement tokens
            - pii_detected (bool): True if any PII was found
            - pii_types (List[str]): Unique list of detected PII types
        """
        if text is None or pd.isna(text):
            return RedactionResult(redacted_text="", pii_detected=False, pii_types=[])

        original_text = str(text)
        current_text = original_text
        detected_types: List[str] = []

        # Step 1: Detect and redact URLs (prioritized to avoid query string false positives)
        if URL_PATTERN.search(current_text):
            current_text = URL_PATTERN.sub("[URL]", current_text)
            detected_types.append("URL")

        # Step 2: Detect and redact Email Addresses
        if EMAIL_PATTERN.search(current_text):
            current_text = EMAIL_PATTERN.sub("[EMAIL]", current_text)
            detected_types.append("EMAIL")

        # Step 3: Detect and redact Order IDs
        has_order = False
        if ORDER_TOKEN_PATTERN.search(current_text):
            current_text = ORDER_TOKEN_PATTERN.sub("[ORDER_ID]", current_text)
            has_order = True
        if ORDER_PHRASE_PATTERN.search(current_text):
            current_text = ORDER_PHRASE_PATTERN.sub(
                lambda m: (m.group(1) or m.group(3)) + "[ORDER_ID]",
                current_text,
            )
            has_order = True
        if has_order:
            detected_types.append("ORDER_ID")

        # Step 4: Detect and redact Customer / Account IDs
        has_cust = False
        if CUSTOMER_TOKEN_PATTERN.search(current_text):
            current_text = CUSTOMER_TOKEN_PATTERN.sub("[CUSTOMER_ID]", current_text)
            has_cust = True
        if CUSTOMER_PHRASE_PATTERN.search(current_text):
            current_text = CUSTOMER_PHRASE_PATTERN.sub(
                lambda m: (m.group(1) or m.group(3)) + "[CUSTOMER_ID]",
                current_text,
            )
            has_cust = True
        if has_cust:
            detected_types.append("CUSTOMER_ID")

        # Step 5: Detect and redact Phone numbers
        if PHONE_PATTERN.search(current_text):
            current_text = PHONE_PATTERN.sub("[PHONE]", current_text)
            detected_types.append("PHONE")

        pii_detected = len(detected_types) > 0
        return RedactionResult(
            redacted_text=current_text,
            pii_detected=pii_detected,
            pii_types=detected_types,
        )


# Singleton redactor instance
_default_redactor = PIIRedactor()


def redact_text(text: Any) -> RedactionResult:
    """Convenience function to redact PII from text.

    Args:
        text: Input review text string.

    Returns:
        RedactionResult(redacted_text, pii_detected, pii_types)
    """
    return _default_redactor.redact(text)


def redact_reviews_dataframe(
    df: pd.DataFrame,
    text_column: str = "cleaned_text",
) -> pd.DataFrame:
    """Apply PII redaction across a DataFrame while preserving the raw input.

    Args:
        df: Input DataFrame containing customer reviews.
        text_column: Name of the text column to sanitize (defaults to 'cleaned_text').

    Returns:
        A new DataFrame with sanitized text and PII audit metadata columns.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame() if df is None else df.copy()

    # Work strictly on a deep copy to preserve original dataset
    safe_df = df.copy(deep=True)

    target_col = text_column if text_column in safe_df.columns else "review_text"
    if target_col not in safe_df.columns:
        raise ValueError(f"Neither '{text_column}' nor 'review_text' found in DataFrame.")

    results = [redact_text(val) for val in safe_df[target_col]]

    # Update cleaned_text with redacted content
    safe_df["cleaned_text"] = [r.redacted_text for r in results]
    safe_df["pii_detected"] = [r.pii_detected for r in results]
    safe_df["pii_types"] = [",".join(r.pii_types) for r in results]

    return safe_df

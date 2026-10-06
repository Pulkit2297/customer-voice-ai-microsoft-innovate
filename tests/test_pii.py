"""Unit tests for Phase 3: PII detection and redaction."""

import pandas as pd
import pytest

from src.pii.redactor import (
    PIIRedactor,
    RedactionResult,
    redact_reviews_dataframe,
    redact_text,
)


def test_email_redaction():
    """Verify that email addresses are detected and replaced with [EMAIL]."""
    text = "Please reach out to support@customervoice.ai or john.doe+promo@example.co.uk for help."
    result = redact_text(text)

    assert result.pii_detected is True
    assert "EMAIL" in result.pii_types
    assert "[EMAIL]" in result.redacted_text
    assert "support@customervoice.ai" not in result.redacted_text
    assert "john.doe+promo@example.co.uk" not in result.redacted_text


def test_phone_number_redaction_10_digit():
    """Verify that 10-digit contiguous phone numbers are redacted."""
    text = "Call me directly at 9876543210 regarding my complaint."
    result = redact_text(text)

    assert result.pii_detected is True
    assert "PHONE" in result.pii_types
    assert result.redacted_text == "Call me directly at [PHONE] regarding my complaint."


def test_phone_number_redaction_formatted():
    """Verify that international and formatted phone numbers are redacted."""
    texts = [
        "Support phone: +1-800-555-0199.",
        "Reach me at (555) 123-4567 today.",
        "My number is 555-234-5678.",
        "Call +91 9876543210 please.",
    ]
    for text in texts:
        result = redact_text(text)
        assert result.pii_detected is True
        assert "PHONE" in result.pii_types
        assert "[PHONE]" in result.redacted_text


def test_url_redaction():
    """Verify that HTTP, HTTPS, and WWW URLs are redacted with [URL]."""
    text = "Check the specs at https://electronics.com/item/49281?ref=promo or www.support.store.org."
    result = redact_text(text)

    assert result.pii_detected is True
    assert "URL" in result.pii_types
    assert "https://electronics.com" not in result.redacted_text
    assert "www.support.store.org" not in result.redacted_text
    assert "[URL]" in result.redacted_text


def test_order_id_redaction():
    """Verify that order ID patterns are redacted with [ORDER_ID]."""
    text1 = "My order #ORD-984712 was never delivered."
    res1 = redact_text(text1)
    assert res1.pii_detected is True
    assert "ORDER_ID" in res1.pii_types
    assert "[ORDER_ID]" in res1.redacted_text

    text2 = "Referencing order id: 554921 for full refund."
    res2 = redact_text(text2)
    assert res2.pii_detected is True
    assert "ORDER_ID" in res2.pii_types
    assert "[ORDER_ID]" in res2.redacted_text


def test_customer_id_redaction():
    """Verify that customer / account IDs are redacted with [CUSTOMER_ID]."""
    text1 = "Customer ID: CUST-883921 needs assistance."
    res1 = redact_text(text1)
    assert res1.pii_detected is True
    assert "CUSTOMER_ID" in res1.pii_types
    assert "[CUSTOMER_ID]" in res1.redacted_text

    text2 = "Linked to account #9876543 on file."
    res2 = redact_text(text2)
    assert res2.pii_detected is True
    assert "CUSTOMER_ID" in res2.pii_types
    assert "[CUSTOMER_ID]" in res2.redacted_text


def test_multiple_pii_prompt_example():
    """Verify the exact example specified in the prompt:

    Input: "My phone is 9876543210 and email is abc@example.com"
    Output: "My phone is [PHONE] and email is [EMAIL]"
    """
    text = "My phone is 9876543210 and email is abc@example.com"
    result = redact_text(text)

    assert result.redacted_text == "My phone is [PHONE] and email is [EMAIL]"
    assert result.pii_detected is True
    assert set(result.pii_types) == {"PHONE", "EMAIL"}


def test_text_without_pii():
    """Verify that reviews without PII are left untouched."""
    text = "The device boots fast, screen contrast is exceptional, and battery lasts two full days!"
    result = redact_text(text)

    assert result.pii_detected is False
    assert result.pii_types == []
    assert result.redacted_text == text


def test_non_pii_numbers_preserved():
    """Verify that ratings, prices, years, and general numerical quantities are not redacted."""
    text = "Bought 2 units for $49.99 in 2023, rating is 5 stars."
    result = redact_text(text)

    assert result.pii_detected is False
    assert result.pii_types == []
    assert result.redacted_text == text


def test_empty_and_null_text():
    """Verify that empty or None text gracefully returns empty results."""
    assert redact_text(None) == RedactionResult(redacted_text="", pii_detected=False, pii_types=[])
    assert redact_text("") == RedactionResult(redacted_text="", pii_detected=False, pii_types=[])


def test_dataframe_redaction_pipeline():
    """Verify DataFrame batch redaction preserves raw data and adds audit columns."""
    df = pd.DataFrame([
        {
            "review_id": "REV_001",
            "cleaned_text": "Call me at 9876543210 or email user@test.com",
        },
        {
            "review_id": "REV_002",
            "cleaned_text": "Great kindle book, love it!",
        },
    ])
    original_df = df.copy(deep=True)

    safe_df = redact_reviews_dataframe(df)

    # Immutability check
    pd.testing.assert_frame_equal(df, original_df)

    # Verify audit columns
    assert "pii_detected" in safe_df.columns
    assert "pii_types" in safe_df.columns

    assert safe_df.loc[0, "pii_detected"] == True
    assert "[PHONE]" in safe_df.loc[0, "cleaned_text"]
    assert "[EMAIL]" in safe_df.loc[0, "cleaned_text"]

    assert safe_df.loc[1, "pii_detected"] == False
    assert safe_df.loc[1, "cleaned_text"] == "Great kindle book, love it!"

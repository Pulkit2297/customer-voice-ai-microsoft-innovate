# Privacy and PII Redaction Architecture

## Overview

Customer feedback frequently contains unintentional disclosures of Personally Identifiable Information (PII), including contact details, order references, and account numbers. In compliance with data protection standards (such as GDPR, CCPA, and SOC 2), **CustomerVoice AI** enforces an automated privacy layer that sanitizes customer review corpora prior to downstream analytical modeling, topic discovery, or Power BI presentation.

---

## Core Privacy Principles

1. **Privacy by Design**: PII detection and redaction occur early in the processing lifecycle, immediately following text normalization and before any model feature extraction or storage.
2. **Deterministic & Explainable Matching**: The initial implementation relies strictly on deterministic regular expression matching rather than probabilistic ML models, ensuring complete auditability, predictable transformations, and sub-millisecond execution latency.
3. **No Sensitive Inference**: The platform explicitly **does not infer** sensitive personal information (such as political affiliation, health status, race, sexual orientation, or biometric profiles) from unstructured text. Only explicit identifiers are detected and redacted.
4. **Data Immutability**: Raw ingestion datasets are treated as strictly immutable and read-only. Processed privacy-safe data is written exclusively to `data/processed/reviews_pii_safe.csv`.
5. **Standardized Token Replacement**: Detected entities are replaced with deterministic placeholder tokens to maintain linguistic context for downstream NLP models without leaking user identity.

---

## Redacted Entities & Token Map

| Entity Type | Replacement Token | Detection Mechanism | Example Match |
| :--- | :--- | :--- | :--- |
| **Email Address** | `[EMAIL]` | RFC-compliant email regex | `user.name@example.com` |
| **Phone Number** | `[PHONE]` | 10-digit mobile & formatted international | `9876543210`, `+1-800-555-0199` |
| **URL / Link** | `[URL]` | HTTP, HTTPS, and WWW prefixes | `https://store.com/item/42` |
| **Order Identifier** | `[ORDER_ID]` | Prefixed tokens & contextual phrases | `ORD-984712`, `order #123456` |
| **Customer / Account ID** | `[CUSTOMER_ID]` | Prefixed tokens & contextual phrases | `CUST-883921`, `account #987654` |

---

## Execution Order

To prevent false-positive token fragmentation, regex patterns are applied sequentially:
1. **URLs**: Processed first to prevent query strings containing numbers or keys from being falsely parsed as phones or IDs.
2. **Emails**: Processed second to prevent usernames with digits from triggering phone number detection.
3. **Order IDs**: Processed third using contextual prefixes (`ORD-`, `order #`, `order id:`).
4. **Customer IDs**: Processed fourth using contextual prefixes (`CUST-`, `account #`, `user:`).
5. **Phone Numbers**: Processed fifth on remaining numeric patterns, preserving non-PII integers (such as ratings, dates, and prices).

---

## Privacy Audit Trail

Every review processed through `redact_reviews_dataframe` is augmented with two audit columns:
- `pii_detected` (`bool`): Indicates whether any PII pattern was encountered in the review.
- `pii_types` (`str`): Comma-separated list of all PII tokens replaced (e.g., `EMAIL,PHONE`).

This allows compliance teams to easily audit the frequency, distribution, and types of sensitive information submitted by customers.

---

## Future Enhancements

- Integration of Named Entity Recognition (e.g., Microsoft Presidio or spaCy transformer models) for contextual person name and physical address identification.
- Differential privacy layers for aggregate reporting.
- Cryptographic HMAC-based pseudonymous hashing where downstream re-identification is legally mandated for customer support ticketing.

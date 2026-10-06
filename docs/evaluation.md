# Model Evaluation Architecture & Performance Benchmark

## 1. Ethical Principle: Ground-Truth Integrity

> [!IMPORTANT]
> **Production Policy**: Model performance metrics (accuracy, precision, recall, F1) must **never** be asserted or claimed based on training data, heuristic guesses, or unverified outputs. All performance claims within **CustomerVoice AI** must be derived empirically from an actual, human-annotated validation benchmark dataset.

---

## 2. Core Evaluation Concepts

### 2.1 Validation Set (`data/validation/validation_set.csv`)
A validation set is a curated, held-out corpus of customer reviews that has undergone verified human review and annotation. It serves as an impartial benchmark that is never used during model training or prompt tuning.

Schema requirements:
- `review_id`: Unique identifier referencing the customer review.
- `actual_sentiment`: Verified ground-truth sentiment label (`positive`, `neutral`, `negative`).
- `actual_topic`: Verified ground-truth topic label(s) matching the controlled taxonomy (comma-separated for multi-topic reviews).

### 2.2 Ground Truth
Ground truth represents the empirical objective reality against which statistical hypotheses and model inferences are tested. In NLP, human consensus (often verified via multi-annotator agreement or Cohen's Kappa) defines the gold standard.

---

## 3. Evaluation Metrics Explained

### 3.1 Precision
Precision measures exactness—*out of all reviews the model classified as positive, how many were truly positive?*
$$\text{Precision} = \frac{\text{True Positives (TP)}}{\text{True Positives (TP)} + \text{False Positives (FP)}}$$
- **High Precision** ensures that when the system alerts teams to an urgent complaint or negative trend, it is almost certainly a genuine issue rather than a false alarm.

### 3.2 Recall (Sensitivity)
Recall measures completeness—*out of all actual negative reviews submitted by customers, how many did the model successfully identify?*
$$\text{Recall} = \frac{\text{True Positives (TP)}}{\text{True Positives (TP)} + \text{False Negatives (FN)}}$$
- **High Recall** ensures that critical complaints (e.g., safety hazards, battery explosions, or billing errors) do not slip through undetected.

### 3.3 F1-Score
The F1-score is the harmonic mean of Precision and Recall, balancing false alarms against missed detections:
$$\text{F1} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
- **Macro F1**: Averages F1 across all classes with equal weight, highlighting performance deficits on minority classes (e.g. neutral feedback).
- **Weighted F1**: Averages F1 weighted by class support, reflecting overall volume impact.

### 3.4 Multi-Label Topic Metrics
Because customer reviews often span multiple topics (e.g., both `battery` and `delivery`), standard single-class accuracy is insufficient:
- **Exact Match Ratio (Subset Accuracy)**: The percentage of reviews where the predicted topic set exactly matches the ground-truth set. This is a strict metric.
- **Hamming Loss**: The fraction of incorrect topic assignments (either missed true topics or falsely assigned topics) across all labels. A Hamming loss of `0.0` represents flawless multi-label classification.
- **Micro/Macro F1**: Micro F1 aggregates global true positives, while Macro F1 treats each taxonomy topic equally regardless of frequency.

---

## 4. Confusion Matrix

The Confusion Matrix provides a cross-tabulation of actual versus predicted classes, exposing systematic misclassification tendencies:

```
                  PREDICTED
              Pos     Neu     Neg
ACTUAL  Pos [ TP_p    FN_p    FN_p ]
        Neu [ FP_neu  TP_neu  FN_neu]
        Neg [ FP_neg  FN_neg  TP_neg]
```

- **Off-diagonal values** reveal specific model confusions (e.g. subtle negative reviews being classified as neutral, or sarcastic positive phrases being misclassified).

---

## 5. Evaluation Limitations

1. **Annotator Subjectivity**: Sentiment in natural language is inherently subjective; two human raters may disagree on whether *"the screen is okay for the price"* is positive or neutral.
2. **Class Imbalance**: In many live environments, negative reviews comprise <15% of total volume. High accuracy can be deceptive if a model simply predicts the majority class.
3. **Distribution Shift**: A model evaluated on a holiday electronics validation set will exhibit degraded metrics when deployed on everyday apparel feedback. Continuous drift monitoring is essential.
4. **Sample Size Constraints**: Small validation sample sizes exhibit wide confidence intervals; production benchmarks should target a minimum of 500–1,000 stratified samples.

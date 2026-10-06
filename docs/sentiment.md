# Sentiment Analysis Baseline Architecture

## 1. Overview

**CustomerVoice AI** implements a modular, decoupled sentiment analysis subsystem. The system is designed around the `BaseSentimentEngine` abstract interface, allowing local open-source baseline models and enterprise cloud services (such as Azure AI Language) to be swapped interchangeably with zero downstream pipeline modification.

The initial baseline is powered by **VADER** (*Valence Aware Dictionary and sEntiment Reasoner*), a deterministic, open-source rule-based sentiment model optimized for customer feedback, social commentary, and micro-reviews.

---

## 2. How the Model Works

VADER operates through a curated sentiment lexicon paired with grammatical and syntactical heuristics:

1. **Lexical Polarity Scoring**:
   - The engine maintains an empirically validated gold-standard sentiment lexicon where words are assigned valences from `-4.0` (extremely negative) to `+4.0` (extremely positive).
2. **Contextual Heuristics**:
   - **Punctuation Booster**: Exclamation marks and question marks amplify sentiment intensity (e.g., `"Great!!!"` vs `"Great"`).
   - **Capitalization**: ALL-CAPS words emphasize sentiment valence (e.g., `"GREAT"` vs `"great"`).
   - **Degree Modifiers & Adverbs**: Words like *"extremely"*, *"barely"*, or *"slightly"* scale the sentiment of subsequent terms.
   - **Negation Handling**: Words like *"not"*, *"never"*, or *"didn't"* invert or flip polarity across a sliding window of subsequent tokens.
3. **Compound Score Computation**:
   - The individual valence scores are summed and normalized via an alpha-smoothed hyperbolic tangent function:
     $$\text{compound} = \frac{x}{\sqrt{x^2 + \alpha}}$$
     producing a continuous metric bounded within $[-1.0, 1.0]$.
4. **Categorical Label Assignment**:
   - $\text{compound} \ge 0.05 \implies \text{positive}$
   - $\text{compound} \le -0.05 \implies \text{negative}$
   - $-0.05 < \text{compound} < 0.05 \implies \text{neutral}$

---

## 3. Limitations of the Baseline Model

While VADER offers significant advantages (high throughput, zero cold-start training, zero inference cost, and 100% deterministic reproducibility), it possesses inherent structural limitations:

- **Lack of Deep Contextual Embeddings**: VADER relies on surface lexical matching. It cannot capture deep semantic nuance or polysemous words where meaning changes fundamentally depending on context.
- **Sarcasm and Irony**: Subtle expressions such as *"Oh great, another delayed delivery"* are frequently misclassified as positive due to the presence of positive tokens (*"great"*).
- **Domain-Specific Slang**: Specialized e-commerce, tech, or hardware terminology (e.g., *"bricked"*, *"bloatware"*, *"thermal throttling"*) may not be recognized as negative valences unless added to the lexicon.
- **Aspect-Level Blindness**: VADER provides document-level or sentence-level sentiment, but does not isolate aspect-based sentiments (e.g., *"The battery is great (+), but the camera is awful (-)"*).

---

## 4. Why a Validation Dataset is Required

A curated validation dataset (`data/validation/`) with human ground-truth labels is essential for production deployment:

1. **Quantifying Baseline Performance**: Establishes objective benchmark metrics:
   - **Precision**: Minimizing false alarms in complaint detection.
   - **Recall**: Ensuring negative customer sentiment is not missed.
   - **F1-Score / Macro F1**: Balanced evaluation across imbalanced sentiment classes.
2. **Data & Concept Drift Tracking**: As customer vocabulary evolves, comparing production inferences against the validation benchmark reveals performance degradation over time.
3. **Model Selection & Champion/Challenger Testing**: Provides an empirical evaluation suite to compare whether upgrading to fine-tuned transformer models or Azure AI Language delivers measurable business value over the local baseline.

---

## 5. Replacing the Local Model with Azure AI Language

The platform architecture decouples the pipeline from the model provider through `BaseSentimentEngine`:

```
               [BaseSentimentEngine (ABC)]
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
 [LocalSentimentModel (VADER)]    [AzureLanguageSentimentEngine]
```

### Transitioning to Azure AI Language

To transition from the local baseline to Azure AI Language:

1. **Install SDK**:
   ```bash
   pip install azure-ai-textanalytics
   ```

2. **Configure Environment Variables** in `.env`:
   ```env
   AZURE_LANGUAGE_ENDPOINT="https://<your-resource-name>.cognitiveservices.azure.com/"
   AZURE_LANGUAGE_KEY="<your-azure-api-key>"
   ```

3. **Implement Subclass**:
   ```python
   from azure.ai.textanalytics import TextAnalyticsClient
   from azure.core.credentials import AzureKeyCredential
   from src.sentiment.sentiment_engine import BaseSentimentEngine, SentimentResult

   class AzureLanguageSentimentEngine(BaseSentimentEngine):
       def __init__(self, endpoint: str, key: str):
           self.client = TextAnalyticsClient(endpoint, AzureKeyCredential(key))
           self._model_name = "Azure-AI-Language"
           self._model_version = "2023-04-01"

       def predict(self, text: str) -> SentimentResult:
           response = self.client.analyze_sentiment([text])[0]
           # Map Azure response (positive, neutral, negative) and confidence scores
           ...
           return SentimentResult(
               sentiment=response.sentiment,
               sentiment_score=compound_score,
               confidence=confidence,
               model_name=self.model_name,
               model_version=self.model_version
           )
   ```

4. **Zero Pipeline Disruption**:
   `scripts/run_sentiment.py` and downstream alert/drift engines consume `SentimentResult` uniformly, requiring no changes to data ingestion, schema validation, PII scrubbing, or Power BI datasets.

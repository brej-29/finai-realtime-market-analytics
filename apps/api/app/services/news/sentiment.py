from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.schemas.news import SentimentScore


@dataclass
class HeadlineSentimentAnalyzer:
    """Lightweight sentiment analyzer for news headlines using VADER."""

    analyzer: SentimentIntensityAnalyzer = SentimentIntensityAnalyzer()

    def score(self, text: str) -> SentimentScore:
        scores = self.analyzer.polarity_scores(text)
        compound = float(scores.get("compound", 0.0))

        label: str
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        positive_words, negative_words = self._top_polar_words(text)

        explanation_parts: List[str] = []
        if positive_words:
            explanation_parts.append("Positive: " + ", ".join(positive_words))
        if negative_words:
            explanation_parts.append("Negative: " + ", ".join(negative_words))
        if not explanation_parts:
            explanation_parts.append("Headline appears neutral based on VADER lexicon.")

        explanation = "; ".join(explanation_parts)

        return SentimentScore(
            score=compound,
            label=label,
            explanation=explanation,
        )

    def _top_polar_words(self, text: str, limit: int = 3) -> Tuple[list[str], list[str]]:
        """Return top positive and negative words based on VADER's lexicon."""
        words = [
            w.strip(".,!?;:\"'()").lower()
            for w in text.split()
            if w.strip(".,!?;:\"'()")
        ]
        lexicon = self.analyzer.lexicon

        positives: list[tuple[str, float]] = []
        negatives: list[tuple[str, float]] = []

        for word in words:
            if word not in lexicon:
                continue
            score = lexicon[word]
            if score > 0:
                positives.append((word, score))
            elif score < 0:
                negatives.append((word, score))

        positives_sorted = sorted(positives, key=lambda x: x[1], reverse=True)[:limit]
        negatives_sorted = sorted(negatives, key=lambda x: x[1])[:limit]

        pos_words = [w for w, _ in positives_sorted]
        neg_words = [w for w, _ in negatives_sorted]
        return pos_words, neg_words
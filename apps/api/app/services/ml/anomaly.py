from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np
from sklearn.ensemble import IsolationForest

from app.schemas.ai import AnomalyPoint
from app.schemas.common import HistoricalBar


@dataclass
class AnomalyDetectionResult:
    points: List[AnomalyPoint]


def detect_return_anomalies(
    bars: Sequence[HistoricalBar],
    contamination: float = 0.05,
) -> AnomalyDetectionResult:
    """Detect simple anomalies on returns (and volume if available).

    Uses IsolationForest which is lightweight and CPU-friendly for small series.
    """
    if len(bars) < 10:
        return AnomalyDetectionResult(points=[])

    returns: list[float] = []
    volumes: list[float] = []

    for i in range(1, len(bars)):
        prev = bars[i - 1]
        curr = bars[i]
        if prev.close <= 0:
            ret = 0.0
        else:
            ret = (curr.close / prev.close) - 1.0
        returns.append(ret)
        volumes.append(curr.volume or 0.0)

    X = np.column_stack([returns, volumes])
    iso = IsolationForest(
        contamination=contamination,
        random_state=42,
    )
    iso.fit(X)
    scores = iso.decision_function(X)
    labels = iso.predict(X)  # -1 = anomaly, 1 = normal

    points: list[AnomalyPoint] = []
    for i, bar in enumerate(bars[1:], start=1):
        is_anomaly = labels[i - 1] == -1
        points.append(
            AnomalyPoint(
                ts=bar.ts,
                value=bar.close,
                score=float(scores[i - 1]),
                is_anomaly=is_anomaly,
            )
        )

    return AnomalyDetectionResult(points=points)
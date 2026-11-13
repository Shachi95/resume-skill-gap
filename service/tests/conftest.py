"""Hypothesis profile configuration shared by all test trees."""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

settings.register_profile(
    "ci",
    derandomize=True,
    max_examples=200,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile("default", max_examples=100)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))

"""Deterministic scoring weights and version constants."""

from typing import Dict

# Score model version — bump when weights or component formulas change
SELLER_READINESS_VERSION = "sri-v1"
OPPORTUNITY_SCORE_VERSION = "opp-v1"
RECOMMENDATION_VERSION = "nba-v1"
BOOK_OF_WORK_VERSION = "bow-v1"

SELLER_READINESS_WEIGHTS: Dict[str, float] = {
    "exit_window": 0.25,
    "succession_vacuum": 0.25,
    "digital_decay": 0.20,
    "stagnation": 0.15,
    "recent_change": 0.15,
}

OPPORTUNITY_WEIGHTS: Dict[str, float] = {
    "thesis_fit": 0.30,
    "seller_readiness": 0.25,
    "timing": 0.20,
    "access": 0.15,
    "competition_advantage": 0.10,
}

TIMING_BUCKETS = ("ready_now", "warming_up", "watch", "not_actionable")

NBA_ACTIONS = (
    "CONTACT_NOW",
    "RELATIONSHIP_FIRST",
    "RESEARCH_MORE",
    "MONITOR",
    "DEPRIORITIZE",
)

# Recommendation window TTL by action (days from trigger / now)
NBA_WINDOW_DAYS: Dict[str, int] = {
    "CONTACT_NOW": 21,
    "RELATIONSHIP_FIRST": 45,
    "RESEARCH_MORE": 14,
    "MONITOR": 60,
    "DEPRIORITIZE": 90,
}
CONTACT_NOW_WINDOW_CAP_DAYS = 45

# Substitute clustering
SUBSTITUTE_RADIUS_MILES = 40.0
REVENUE_BAND_RATIO = 0.5  # same band if within 50% of each other

# Default weekly cadence (workspace settings / thesis strategy override)
DEFAULT_CADENCE: Dict[str, int] = {
    "max_outreach_per_week": 5,
    "max_research_slots": 4,
}

# Research gap estimates: hours to fill + typical opportunity/confidence lift
RESEARCH_GAP_HOURS: Dict[str, float] = {
    "contacts": 1.5,
    "founded_year": 0.5,
    "revenue_est": 1.0,
}

# Cap Places results per search job to control quota
MAX_PLACES_RESULTS_PER_JOB = 40

"""Shared constants for user-facing pipeline controls.

Keeping allowed values here lets the upload API, future preset system, and
frontend stay in sync without hardcoding magic numbers in multiple places.
"""

# Reel length options exposed in the upload UI (seconds).
ALLOWED_TARGET_DURATIONS = (30, 60, 90)
DEFAULT_TARGET_DURATION = 90

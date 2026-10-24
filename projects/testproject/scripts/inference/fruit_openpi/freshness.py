"""Fail-stop timing checks. Project policy, NOT LeRobot motor limits/defaults."""

import math
import time


def boottime():
    # Includes system suspend, unlike Linux CLOCK_MONOTONIC.
    return time.clock_gettime(time.CLOCK_BOOTTIME)


class StaleControlError(RuntimeError):
    pass


class FreshnessGuard:
    def __init__(self, max_gap_s=1.0, max_response_age_s=2.0, clock=boottime):
        if any(not math.isfinite(x) or x <= 0 for x in (max_gap_s, max_response_age_s)):
            raise ValueError("Positive finite timing budgets required")
        self.max_gap_s = max_gap_s
        self.max_response_age_s = max_response_age_s
        self.clock = clock
        self.last = None
        self.failed = None

    def arm(self):
        if self.failed:
            raise StaleControlError(self.failed)
        self.last = self.clock()

    def _fail(self, message):
        self.failed = message
        raise StaleControlError(message)

    def check(self, received_at=None):
        if self.failed:
            raise StaleControlError(self.failed)
        now = self.clock()
        if self.last is not None:
            gap = now - self.last
            if gap < 0 or gap > self.max_gap_s:
                self._fail(
                    f"Control interruption: {gap:.6f}s exceeds {self.max_gap_s}s; discard pending actions"
                )
        if received_at is not None:
            age = now - received_at
            if not math.isfinite(age) or age < 0 or age > self.max_response_age_s:
                self._fail(f"Stale response: age {age:.6f}s exceeds {self.max_response_age_s}s; no dispatch")
        if self.last is not None:
            self.last = now

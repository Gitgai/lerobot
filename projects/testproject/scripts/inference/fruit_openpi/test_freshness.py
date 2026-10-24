import unittest

from freshness import FreshnessGuard, StaleControlError


class FreshnessTests(unittest.TestCase):
    def make(self):
        now = [100.0]
        return now, FreshnessGuard(clock=lambda: now[0])

    def test_normal_thirty_rows(self):
        now, g = self.make()
        g.arm()
        received = now[0]
        for _ in range(30):
            g.check(received)
            now[0] += 1 / 30

    def test_recorded_pause_blocks_before_dispatch(self):
        now, g = self.make()
        g.arm()
        received = now[0]
        now[0] += 55.592499777
        with self.assertRaises(StaleControlError):
            g.check(received)

    def test_fault_latches(self):
        now, g = self.make()
        g.arm()
        now[0] += 2
        with self.assertRaises(StaleControlError):
            g.check()
        with self.assertRaises(StaleControlError):
            g.arm()
        with self.assertRaises(StaleControlError):
            g.check()

    def test_network_wait_with_active_polling(self):
        now, g = self.make()
        g.arm()
        for _ in range(100):
            now[0] += 0.1
            g.check()
        g.check(now[0])

    def test_old_worker_response_rejected(self):
        now, g = self.make()
        g.arm()
        received = now[0]
        for _ in range(25):
            now[0] += 0.1
            g.check()
        with self.assertRaises(StaleControlError):
            g.check(received)

    def test_pause_during_log_or_status_read(self):
        now, g = self.make()
        g.arm()
        g.check()
        now[0] += 1.01
        with self.assertRaises(StaleControlError):
            g.check()

    def test_invalid_timestamps(self):
        for value in (float("nan"), float("inf"), 101):
            now, g = self.make()
            g.arm()
            with self.assertRaises(StaleControlError):
                g.check(value)

    def test_invalid_budgets(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                FreshnessGuard(max_gap_s=value)


if __name__ == "__main__":
    unittest.main()

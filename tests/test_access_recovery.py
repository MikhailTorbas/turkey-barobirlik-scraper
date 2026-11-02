import json
import tempfile
import unittest
from pathlib import Path

from access_recovery import AccessRecovery


class AccessRecoveryTests(unittest.TestCase):
    def test_expired_sessions_back_off_and_limit_survives_restart(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'recovery.json'
            now = [1000.0]
            same = {'unique_listings': 10, 'completed_details': 4}
            for attempt, expected_wait in [(1, 60), (2, 120), (3, 240)]:
                guard = AccessRecovery(path, clock=lambda: now[0])
                guard.record('16', 'session_expired', 2, same, same)
                self.assertEqual(guard.wait_seconds(), expected_wait)
                self.assertEqual(guard.exhausted, attempt == 3)
                now[0] += expected_wait
            restarted = AccessRecovery(path, clock=lambda: now[0] + 10000)
            self.assertTrue(restarted.exhausted)
            self.assertIn('16', restarted.summary()['blocked_bars'])
            self.assertIn('Restarting does not reset', restarted.summary()['action_required'])

    def test_completed_profiles_reset_streak_and_duplicate_rows_do_not(self):
        with tempfile.TemporaryDirectory() as td:
            guard = AccessRecovery(Path(td) / 'recovery.json', clock=lambda: 1)
            before = {'unique_listings': 10, 'completed_details': 4}
            guard.record('16', 'access_blocked', 2, before, before)
            guard.record('34', 'session_expired', 2, before, before)
            self.assertEqual(guard.state['consecutive_no_progress'], 2)
            after = {**before, 'completed_details': 5}
            guard.record('6', 'session_expired', 2, before, after)
            self.assertEqual(guard.state['consecutive_no_progress'], 0)
            self.assertEqual(guard.wait_seconds(), 0)
            # Some progress does not pretend the session finished normally.
            self.assertIn('6', guard.summary()['blocked_bars'])

    def test_healthy_empty_search_clears_access_failure_but_interruption_does_not(self):
        with tempfile.TemporaryDirectory() as td:
            guard = AccessRecovery(Path(td) / 'recovery.json', clock=lambda: 1)
            guard.record('16', 'access_blocked', 2, {}, {})
            guard.record('16', 'interrupted', 130, {}, {})
            self.assertEqual(guard.state['consecutive_no_progress'], 1)
            guard.record('16', 'search_budget_paused', 2, {}, {})
            self.assertEqual(guard.state['consecutive_no_progress'], 0)
            self.assertNotIn('16', guard.summary()['blocked_bars'])

    def test_invalid_recovery_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'recovery.json'
            path.write_text('not json')
            with self.assertRaises(json.JSONDecodeError):
                AccessRecovery(path)

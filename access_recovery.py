"""Durable containment for serial workers that exhaust access/session retries.

This does not solve challenges. It bounds repeated paid attempts and preserves
the reason for stopping across supervisor restarts.
"""
import json
import time
from pathlib import Path


class AccessRecovery:
    LIMIT = 3
    BASE_COOLDOWN = 60
    ACCESS_FAILURES = {'access_blocked', 'session_expired'}
    HEALTHY = {'queue_finished', 'detail_queue_finished', 'detail_budget_paused',
               'search_budget_paused', 'coverage_unresolved'}

    def __init__(self, path, clock=time.time):
        self.path = Path(path)
        self.clock = clock
        self.state = (json.loads(self.path.read_text()) if self.path.exists() else
                      {'consecutive_no_progress': 0, 'retry_not_before': 0,
                       'blocked_bars': {}, 'total_access_failures': 0})

    @property
    def exhausted(self):
        return self.state['consecutive_no_progress'] >= self.LIMIT

    def wait_seconds(self):
        return max(0, self.state['retry_not_before'] - self.clock())

    def record(self, bar, worker_status, exit_code, before, after):
        # Only durable, useful output counts as progress: newly completed
        # profiles or newly discovered identities. Repeated listings do not.
        progress = any(after.get(k, 0) > before.get(k, 0)
                       for k in ('completed_details', 'unique_listings'))
        access_failure = worker_status in self.ACCESS_FAILURES
        if access_failure:
            self.state['total_access_failures'] += 1
            self.state['blocked_bars'][str(bar)] = {
                'worker_status': worker_status, 'last_failure_at': self.clock(),
                'progress_in_phase': progress}
        elif exit_code in (0, 2) and worker_status in self.HEALTHY:
            self.state['blocked_bars'].pop(str(bar), None)
        if progress or (exit_code in (0, 2) and worker_status in self.HEALTHY):
            self.state['consecutive_no_progress'] = 0
            self.state['retry_not_before'] = 0
        elif access_failure:
            self.state['consecutive_no_progress'] += 1
            self.state['retry_not_before'] = (
                self.clock() + self.BASE_COOLDOWN *
                2 ** (self.state['consecutive_no_progress'] - 1))
        self.state['last_worker_status'] = worker_status
        self.state['last_phase_made_progress'] = progress
        self.state['updated_at'] = self.clock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.state, indent=2))
        tmp.replace(self.path)

    def summary(self):
        return {**self.state, 'no_progress_limit': self.LIMIT,
                'retries_exhausted': self.exhausted,
                'retry_wait_seconds': round(self.wait_seconds(), 1),
                'action_required': (
                    'Access retries exhausted. Preserve checkpoint; inspect '
                    'diagnostics and resolve access before authorizing a new '
                    'bounded attempt. Restarting does not reset this limit.'
                    if self.exhausted else None)}

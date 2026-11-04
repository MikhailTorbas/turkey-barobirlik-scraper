import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from types import SimpleNamespace

import turnstile_solver as s
import turkey_scraper as t


class SolverTransportTests(unittest.TestCase):
    def test_poll_recovers_same_task_without_recreating_or_extra_reserved_charge(self):
        with tempfile.TemporaryDirectory() as td:
            calls=[];clock=[0]
            def transport(method,body,timeout):
                calls.append(method)
                if method=='createTask':return {'taskId':'task'}
                if calls.count('getTaskResult')<3:raise s.SolverTransportError('safe')
                return {'status':'ready','solution':{'token':'secret-token'}}
            solver=s.CapSolver('secret-key',Path(td)/'ledger.json',transport=transport,
                clock=lambda:clock[0],sleep=lambda n:clock.__setitem__(0,clock[0]+n))
            self.assertEqual(solver.solve({'sitekey':'public','url':'https://example.test'}),'secret-token')
            self.assertEqual(calls.count('createTask'),1)
            self.assertEqual(solver.state['attempts'],1)

    def test_uncertain_create_is_not_retried_and_reservation_survives(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(s,'urlopen',side_effect=TimeoutError('secret-key in URL')) as post:
                solver=s.CapSolver('secret-key',Path(td)/'ledger.json')
                with self.assertRaisesRegex(s.SolverTransportError,'^CapSolver transport or response failure$'):
                    solver.solve({'sitekey':'public','url':'https://example.test'})
            self.assertEqual(post.call_count,1);self.assertEqual(solver.state['attempts'],1)

    def test_provider_http_error_is_decoded_safely_and_expired_pending_cleared(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'ledger.json'
            def transport(method,body,timeout):
                if method=='createTask':return {'taskId':'expired'}
                error=HTTPError('https://secret-key.invalid',400,'secret-key',{},io.BytesIO(b'{"errorId":1,"errorCode":"ERROR_TASK_NOT_FOUND","errorDescription":"secret-key"}'))
                with patch.object(s,'urlopen',side_effect=error):return s.post_json(method,body,timeout)
            solver=s.CapSolver('secret-key',path,transport=transport)
            with self.assertRaisesRegex(s.SolverError,'^CapSolver ERROR_TASK_NOT_FOUND$'):
                solver.solve({'sitekey':'public','url':'https://example.test'})
            self.assertNotIn('pending',solver.state)
            self.assertNotIn('secret-key',path.read_text())

    def test_transient_solver_failure_can_use_bounded_access_recovery(self):
        args=SimpleNamespace()
        def evaluate(script,*unused):
            if script==s.DISCOVER_SCRIPT:return [{'sitekey':'public','url':'https://example.test'}]
            return True
        driver=t.DirectoryBrowser(SimpleNamespace(evaluate=evaluate),t.Config(),args)
        solver=SimpleNamespace(solve=lambda widget:(_ for _ in ()).throw(s.SolverTransportError('safe')))
        with self.assertRaises(t.VerificationRequired):driver.solve_turnstile(solver)
        self.assertFalse(getattr(args,'_solver_terminal',False))

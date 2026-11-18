import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from turkey_scraper import DirectoryBrowser, Config, VerificationRequired, SessionExpired, retry

from turnstile_solver import (CapSolver, SolverError, SolverBudgetExceeded,
    CAPTURE_SCRIPT, DISCOVER_SCRIPT, APPLY_SCRIPT)


class SolverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / 'usage.json'
        self.widget = {'url':'https://example.test/search', 'sitekey':'public-key',
                       'action':'search', 'cdata':'session-data'}

    def test_task_contract_and_no_secret_persistence(self):
        calls = []
        def transport(method, body, timeout):
            calls.append((method, body, timeout))
            return {'taskId':'task'} if method == 'createTask' else {'status':'ready','solution':{'token':'private-token'}}
        token = CapSolver('private-key', self.ledger, transport=transport).solve(self.widget)
        self.assertEqual(token, 'private-token')
        task = calls[0][1]['task']
        self.assertEqual(task['type'], 'AntiTurnstileTaskProxyLess')
        self.assertEqual(task['metadata'], {'action':'search','cdata':'session-data'})
        saved = self.ledger.read_text()
        self.assertNotIn('private-key', saved)
        self.assertNotIn('private-token', saved)
        self.assertEqual(self.ledger.stat().st_mode & 0o777, 0o600)

    def test_lost_create_response_reserves_budget_across_restart(self):
        def lost(*args):
            raise SolverError('transport failure')
        with self.assertRaises(SolverError):
            CapSolver('key', self.ledger, max_tasks=1, transport=lost).solve(self.widget)
        with self.assertRaises(SolverBudgetExceeded):
            CapSolver('key', self.ledger, max_tasks=1, transport=lost).solve(self.widget)

    def test_timeout_resumes_same_pending_task_without_second_charge(self):
        clock = [0]
        calls = []
        def transport(method, body, timeout):
            calls.append(method)
            return {'taskId':'pending'} if method == 'createTask' else {'status':'processing'}
        client = CapSolver('key', self.ledger, timeout=3, transport=transport,
                           clock=lambda:clock[0], sleep=lambda n:clock.__setitem__(0,clock[0]+n))
        with self.assertRaises(SolverError):
            client.solve(self.widget)
        def ready(method, body, timeout):
            calls.append(method)
            self.assertEqual(body['taskId'], 'pending')
            return {'status':'ready','solution':{'token':'ok'}}
        self.assertEqual(CapSolver('key', self.ledger, max_tasks=1, transport=ready).solve(self.widget), 'ok')
        self.assertEqual(calls.count('createTask'), 1)

    def test_provider_error_does_not_expose_description(self):
        def transport(*args):
            return {'errorId':1,'errorCode':'ERROR_ZERO_BALANCE','errorDescription':'secret key'}
        with self.assertRaisesRegex(SolverError, '^CapSolver ERROR_ZERO_BALANCE$'):
            CapSolver('key', self.ledger, transport=transport).solve(self.widget)

    def test_invalid_widget_never_creates_task(self):
        def unexpected(*args):
            self.fail('Invalid widget spent a task')
        with self.assertRaises(SolverError):
            CapSolver('key', self.ledger, transport=unexpected).solve({'url':'https://example.test'})
        self.assertFalse(self.ledger.exists())

    def test_ready_without_token_is_failure(self):
        def transport(method, *args):
            return {'taskId':'t'} if method == 'createTask' else {'status':'ready','solution':{}}
        with self.assertRaisesRegex(SolverError, 'empty Turnstile'):
            CapSolver('key', self.ledger, transport=transport).solve(self.widget)

    def test_managed_challenge_without_widget_never_spends(self):
        page = SimpleNamespace(evaluate=lambda script, *args: [])
        driver = DirectoryBrowser(page, Config(), SimpleNamespace())
        solver = SimpleNamespace(solve=lambda widget:self.fail('Unsupported challenge spent a task'))
        with self.assertRaisesRegex(VerificationRequired, 'observable Turnstile'):
            driver.solve_turnstile(solver)

    def test_solver_token_alone_does_not_establish_acceptance(self):
        evaluations = []
        def evaluate(script, payload=None):
            evaluations.append(payload)
            return [self.widget] if payload is None else True
        driver = DirectoryBrowser(SimpleNamespace(evaluate=evaluate), Config(),
                                  SimpleNamespace(auto_verification_timeout=0))
        driver.challenge_required = lambda: True
        with self.assertRaisesRegex(VerificationRequired, 'remained'):
            driver.solve_turnstile(SimpleNamespace(solve=lambda widget:'solved-token'))
        self.assertEqual(evaluations[-1]['token'], 'solved-token')

    def test_form_appearing_during_wait_gets_document_tracking_before_solve(self):
        state = {'tracked':False}
        def evaluate(script, payload=None):
            if script == CAPTURE_SCRIPT:
                state['tracked']=True
            elif script == DISCOVER_SCRIPT:
                self.assertTrue(state['tracked'])
                return [{**self.widget,'documentId':'document'}]
            elif script == APPLY_SCRIPT:
                self.assertTrue(state['tracked'])
                self.assertEqual(payload['widget']['documentId'],'document')
            return True
        driver=DirectoryBrowser(SimpleNamespace(evaluate=evaluate),Config(),
                                SimpleNamespace(auto_verification_timeout=1))
        driver.challenge_required=lambda:False
        driver.solve_turnstile(SimpleNamespace(solve=lambda widget:'valid-response'))

    def test_closed_session_does_not_spend_ordinary_retries(self):
        calls = []
        def operation():
            calls.append(1)
            raise SessionExpired('closed')
        with self.assertRaises(SessionExpired):
            retry(operation, SimpleNamespace(retries=5))
        self.assertEqual(len(calls), 1)

    def test_raw_browser_closed_error_is_promoted_before_retry(self):
        calls=[]
        def operation():
            calls.append(1)
            raise RuntimeError('Page.evaluate: Target page, context or browser has been closed')
        with self.assertRaises(SessionExpired):
            retry(operation,SimpleNamespace(retries=5))
        self.assertEqual(len(calls),1)

    @unittest.skipUnless(shutil.which('node'), 'Node required for JavaScript unit test')
    def test_live_widget_capture_callback_and_changed_document_guard(self):
        # Execute adapter JavaScript against an in-memory DOM model; no browser
        # connection, target-site request or paid solver call occurs here.
        script = r'''
const fs = require('fs');
const scripts = JSON.parse(fs.readFileSync(0,'utf8'));
global.window=global;
global.location={href:'https://example.test/search'};
global.addEventListener=()=>{};
global.setInterval=()=>1;
let callbackToken=null;
const field={name:'cf-turnstile-response',value:'',dispatchEvent:()=>{}};
global.document={querySelectorAll:selector=>selector==='input,textarea'?[field]:[]};
eval(scripts.capture);
window.turnstile={render:()=> 'widget-id'};
window.turnstile.render('#widget',{sitekey:'key',action:'search',cData:'data',callback:token=>{callbackToken=token;}});
const widgets=eval('('+scripts.discover+')')();
if (widgets.length!==1 || widgets[0].cdata!=='data') throw Error('Capture failed');
const apply=eval('('+scripts.apply+')');
apply({widget:widgets[0],token:'solution'});
if(field.value!=='solution'||callbackToken!=='solution') throw Error('Callback failed');
location.href='https://example.test/other';
let rejected=false;
try{apply({widget:widgets[0],token:'stale'});}catch(e){rejected=true;}
if(!rejected || field.value!=='solution') throw Error('Stale document accepted');
location.href='https://example.test/search';
let created=null;
document.querySelectorAll=selector=>selector==='input,textarea'?[]:
    selector==='.cf-turnstile[data-sitekey], #avTurnstile[data-sitekey]'?[{dataset:{sitekey:'key'},closest:()=>({appendChild:item=>{created=item;}})}]:[];
document.createElement=()=>({dispatchEvent:()=>{}});
apply({widget:{...widgets[0],index:-1},token:'new-solution'});
if(!created || created.name!=='cf-turnstile-response' || created.value!=='new-solution')
    throw Error('Missing response field was not attached to the observed widget form');
'''
        result = subprocess.run(['node','-e',script], input=json.dumps({
            'capture':CAPTURE_SCRIPT,'discover':DISCOVER_SCRIPT,'apply':APPLY_SCRIPT}),
            text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__ == '__main__':
    unittest.main()

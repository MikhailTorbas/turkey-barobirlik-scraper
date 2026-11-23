"""Execute the real browser request function against deterministic failures."""
import json,subprocess,unittest
from modern_transport import REQUEST

class ModernNetworkTests(unittest.TestCase):
    def check(self,mode):
        js=r'''
const spec=JSON.parse(require('fs').readFileSync(0,'utf8'));
const form={querySelector:()=>({value:'private-csrf'})};
global.document={querySelector:()=>form};global.location={href:'https://example.test/AvukatArama',origin:'https://example.test'};
Object.defineProperty(global,'navigator',{value:{onLine:true},configurable:true});
let calls=0;
global.fetch=async()=>{
 calls++;
 if(spec.mode==='disconnect'){document.querySelector=()=>null;throw new TypeError('private-endpoint');}
 if(spec.mode==='timeout'){const e=new Error('private-endpoint');e.name='AbortError';throw e;}
 if(spec.mode==='permanent'||(spec.mode==='transient'&&calls===1))throw new TypeError('private-endpoint');
 let status=200,text='{"kayitlar":[]}';
 if(spec.mode==='origin'&&calls===1){status=522;text='<html>origin timeout</html>';}
 if(spec.mode==='challenge'){status=403;text='<script>window._cf_chl_opt={};</script>';}
 if(spec.mode==='html200'){text='<script>window._cf_chl_opt={};</script>';}
 if(spec.mode==='limit'){status=429;text='{}';}
 if(spec.mode==='validation'){status=400;text='{"error":"invalid"}';}
 return {status,url:location.href,text:async()=>text};
};
(async()=>{const result=await eval('('+spec.script+')')({endpoint:'detay',body:{},timeout:2000});console.log(JSON.stringify({calls,result}));})();
'''
        p=subprocess.run(['node','-e',js],input=json.dumps({'mode':mode,'script':REQUEST}),text=True,capture_output=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr);self.assertNotIn('private-',p.stdout)
        return json.loads(p.stdout)
    def test_transient_network_reuses_document(self):
        r=self.check('transient');self.assertEqual(r['calls'],2);self.assertEqual(r['result']['status'],200)
    def test_origin_timeout_retries_once(self):
        r=self.check('origin');self.assertEqual(r['calls'],2);self.assertEqual(r['result']['status'],200)
    def test_persistent_network_failure_is_bounded(self):
        r=self.check('permanent');self.assertEqual(r['calls'],2);self.assertEqual(r['result']['error'],'TypeError')
    def test_disconnected_document_does_not_retry(self):self.assertEqual(self.check('disconnect')['calls'],1)
    def test_deadline_does_not_restart_timeout_budget(self):self.assertEqual(self.check('timeout')['calls'],1)
    def test_access_rejections_never_use_network_retry(self):
        for mode in ('challenge','html200','limit','validation'):
            with self.subTest(mode=mode):self.assertEqual(self.check(mode)['calls'],1)
    def test_http200_challenge_is_classified(self):
        r=self.check('html200')['result'];self.assertTrue(r['managed']);self.assertEqual(r['response_kind'],'html')

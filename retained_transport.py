"""Retained form transport; only compact public HTML crosses CDP.

The factory receives the executing scraper module so CLI and imported usage
share the same parser, exception classes and callback contracts.
"""
import json
import re
import time
import uuid
from bs4 import BeautifulSoup

PACK = r'''
 const pack=(html,status)=>{
  const d=new DOMParser().parseFromString(html,'text/html'),f=d.querySelector('#avForm');
  const managed=!!d.querySelector('#challenge-running,#challenge-stage,#cf-challenge-running') || /(?:window\.)?_cf_chl_opt\s*=/.test(html);
  const pagination=!!d.querySelector('.pagination,a[rel=next]');
  let compact='';
  if(f){const clone=f.cloneNode(true);clone.querySelectorAll('script,style,link,img,iframe,svg,picture,video,audio,source,object,embed,canvas,input,select,textarea').forEach(e=>e.remove());compact=clone.outerHTML;}
  return {status,html:compact,managed_challenge:managed,pagination,raw_html_bytes:new TextEncoder().encode(html).length,returned_html_bytes:new TextEncoder().encode(compact).length};
 };
'''
POST = r'''async ({bar,surname,name,registration='',category,timeout}) => {''' + PACK + r'''
 const f=document.querySelector('#avForm');
 if(!f || !f.querySelector('input[name=ad]'))return {needs_form:true};
 const action=new URL(f.action || location.href,document.baseURI);
 if(action.origin!==location.origin || f.method.toUpperCase()!=='POST')throw Error('Unexpected form destination');
 if(registration && !f.querySelector('input[name=barosicil]'))throw Error('Exact registration search control absent');
 const data=new FormData(f);data.set('baroId',bar);data.set('soyad',surname);data.set('ad',name);data.set('barosicil',registration);data.set('tip',category);data.delete('detay');
 const start=performance.now(),deadline=start+timeout,originalURL=location.href;
 for(let attempt=1;attempt<=2;attempt++){
  const c=new AbortController(),timer=setTimeout(()=>c.abort(),Math.max(1,deadline-performance.now()));
  let r,html;
  try{
   r=await fetch(action.href,{method:'POST',body:new URLSearchParams(data),credentials:'same-origin',signal:c.signal});
   html=await r.text();
  }catch(e){
   if(!['TypeError','NetworkError','AbortError'].includes(e.name))throw e;
   const healthy=location.href===originalURL && document.querySelector('#avForm')===f && navigator.onLine;
   const retry=attempt===1 && healthy && ['TypeError','NetworkError'].includes(e.name) && deadline-performance.now()>500;
   if(!retry)return {transport_error:e.name,attempts:attempt,post_ms:performance.now()-start};
   await new Promise(resolve=>setTimeout(resolve,250));continue;
  }finally{clearTimeout(timer);}
  if(new URL(r.url).origin!==location.origin)throw Error('Unexpected redirect');
  const packed=pack(html,r.status),d=new DOMParser().parseFromString(html,'text/html');
  if(r.status===200 && !packed.managed_challenge && d.querySelector('#avForm'))window.__retainedListing={form:d.querySelector('#avForm'),action:action.href};
  return {...packed,attempts:attempt,post_ms:performance.now()-start};
 }
}'''
DETAILS = r'''({id,requests,timeout}) => {''' + PACK + r'''
 if(window.__tbbDetailBatch)throw Error('Previous detail batch still active');
 const listing=window.__retainedListing;
 if(!listing?.form)return false;
 const clean=s=>s.replace(/\s+/g,' ').trim().toLocaleUpperCase('tr-TR');
 const jobs=requests.map(item=>{
  const rows=[...listing.form.querySelectorAll('tr')].filter(r=>r.querySelector('button[name=detay]'));
  const matches=rows.filter(r=>r.querySelectorAll('td')[2]?.textContent.trim()===item.reg && clean(r.querySelectorAll('td')[1]?.textContent || '')===clean(item.bar));
  if(matches.length!==1)throw Error('Detail identity absent or ambiguous');
  const data=new FormData(listing.form);data.set('detay',matches[0].querySelector('button[name=detay]').value);data.delete('tip');
  return {...item,body:new URLSearchParams(data)};
 });
 const state=window.__tbbDetailBatch={id,ready:[],controllers:[]},originalURL=location.href;
 const run=async job=>{
  const start=performance.now(),deadline=start+timeout;
  for(let attempt=1;attempt<=2;attempt++){
   const c=new AbortController();state.controllers.push(c);const timer=setTimeout(()=>c.abort(),Math.max(1,deadline-performance.now()));
   try{
    const r=await fetch(listing.action,{method:'POST',body:job.body,credentials:'same-origin',signal:c.signal});
    const html=await r.text();if(new URL(r.url).origin!==location.origin)throw Error('Unexpected redirect');
    if(window.__tbbDetailBatch===state)state.ready.push({reg:job.reg,...pack(html,r.status),post_ms:performance.now()-start,attempts:attempt});
    return;
   }catch(e){
    const healthy=window.__tbbDetailBatch===state && location.href===originalURL && !!document.querySelector('#avForm input[name=ad]') && navigator.onLine;
    const retry=attempt===1 && healthy && ['TypeError','NetworkError'].includes(e.name) && deadline-performance.now()>500;
    if(!retry){if(window.__tbbDetailBatch===state)state.ready.push({reg:job.reg,error:e.name,attempts:attempt});return;}
    await new Promise(resolve=>setTimeout(resolve,250));
   }finally{clearTimeout(timer);}
  }
 };
 jobs.forEach(job=>{void run(job);});return true;
}'''


def browser_class(t):
    class RejectedForm(t.VerificationRequired):
        pass

    class RetainedDirectoryBrowser(t.DirectoryBrowser):
        supports_form_recovery=True
        def __init__(self,page,cfg,args):
            super().__init__(page,cfg,args)
            self.stats={'search_post_attempts':0,'detail_post_attempts':0,'raw_html_bytes':0,
                        'returned_html_bytes':0,'form_refreshes':0}
            self.refresh_limit=getattr(args,'form_refreshes',1)
            self.on_transport_event=None

        def event(self,kind,message):
            t.LOG.info('%s: %s',kind,message)
            if self.on_transport_event:self.on_transport_event(kind,message)

        def account(self,reply,detail=False):
            for field in ('raw_html_bytes','returned_html_bytes'):
                self.stats[field]+=reply.get(field,0)
            if detail:self.stats['detail_post_attempts']+=max(0,reply.get('attempts',1)-1)
            else:self.stats['search_post_attempts']+=max(0,reply.get('attempts',1)-1)

        def validate(self,reply):
            if reply.get('managed_challenge') or reply['status'] in (403,429,503):
                raise RejectedForm('POST returned verification/availability response before HTML reduction')
            soup=BeautifulSoup(reply['html'],'html.parser')
            if reply['status']!=200 or not soup.select_one('#avForm'):
                raise RejectedForm('POST returned no usable directory form; status='+str(reply['status']))
            return soup

        def invalidate(self):
            self.last_query=None;self.last_result=None

        def refresh_form(self,reason):
            if self.stats['form_refreshes']>=self.refresh_limit:return False
            self.stats['form_refreshes']+=1;self.invalidate()
            self.event('retained_form_refresh',reason)
            self.navigate(self.args.url);self.form()
            return True

        def recover_form(self,query):
            if not self.refresh_form('Rejected detail; saved siblings retained'):return False
            self.fetch(*query)
            return True

        def submit(self,baro,surname,name,registration=''):
            if getattr(self,'modern',None):return self.modern.submit(baro,surname,name,registration)
            while True:
                try:
                    self.stats['search_post_attempts']+=1
                    reply=self.page.evaluate(POST,{'bar':str(baro),'surname':surname,'name':name,'registration':registration,
                        'category':'Stajyer' if getattr(self.args,'trainees',False) else 'Avukat',
                        'timeout':self.args.navigation_timeout*1000})
                    if reply.get('needs_form'):raise RejectedForm('Original verified form no longer present')
                    self.account(reply);self.search_reply=reply
                    if reply.get('transport_error'):
                        self.needs_session_renewal=True;self.invalidate()
                        raise t.SessionExpired('Retained search transport failed after bounded same-session recovery')
                    soup=self.validate(reply);form=soup.select_one('#avForm');text=form.get_text(' ',strip=True)
                    alerts=[x.get_text(' ',strip=True) for x in form.select('.alert-danger,[role=alert]')]
                    if alerts:
                        # Retain the source reason so verification, invalid input
                        # and availability failures can be distinguished in logs.
                        # An alert still cannot establish a successful empty result.
                        raise RejectedForm('Website rejected the search form: '+t.redact(' '.join(alerts))[:500])
                    rows=t.parse_html_records(str(form),self.page.url);total=t.count_hint(text)
                    if not rows and re.search(r'kay[iı]t\s*bulunamad[iı]|sonu[cç]\s*bulunamad[iı]',text,re.I):total=0
                    if total is None or len(rows)!=total:raise t.ExtractionError('Unconfirmed retained search result count')
                    if reply['pagination']:raise t.ExtractionError('Unexpected pagination; coverage not confirmed')
                    self.event('retained_search',f'bar={baro} rows={total}')
                    return rows,total,1
                except RejectedForm as error:
                    self.invalidate()
                    if not self.refresh_form(str(error)):raise
                except Exception as error:
                    if t.recoverable_browser_error(error):
                        self.invalidate();raise t.SessionExpired('Retained search document/connection interrupted') from error
                    raise

        def detail(self,record,query):
            return self.details([record],query)[0]

        def details(self,records,query):
            if getattr(self,'modern',None):return self.modern.details(records,query)
            if not records:return []
            if len(records)>2 or len({r['bar_registration_number'] for r in records})!=len(records):
                raise t.ExtractionError('Expected at most two distinct official detail identities')
            self.needs_session_renewal=False
            if self.last_query!=query:self.fetch(*query)
            missing=[]
            for record in records:
                matches=[r for r in self.last_result or [] if r['bar_registration_number']==record['bar_registration_number'] and t.turkish_upper(r['bar_association'])==t.turkish_upper(record['bar_association'])]
                if len(matches)!=1:missing.append(record['bar_registration_number'])
            if missing:raise t.ListingIdentityMissing(missing)
            batch_id=uuid.uuid4().hex;pending={r['bar_registration_number']:r for r in records};completed={};errors=[];transport_failed=[]
            self.detail_timings=[];self.detail_payloads=[]
            try:
                # Reserve logical attempts before the network operation so a
                # lost response cannot disappear from the transport counter.
                self.stats['detail_post_attempts']+=len(records)
                started=self.page.evaluate(DETAILS,{'id':batch_id,'requests':[{'reg':r['bar_registration_number'],'bar':r['bar_association']} for r in records],'timeout':self.args.navigation_timeout*1000})
                if not started:
                    self.invalidate();raise t.SessionExpired('Retained listing document disappeared; jobs remain pending')
                deadline=time.monotonic()+self.args.navigation_timeout+2
                while pending:
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise t.SessionExpired('Detail response deadline; saved siblings retained')
                    # Poll inside the browser, then transfer only ready compact
                    # responses. A fast sibling reaches SQLite before a slow
                    # response or a later connection loss.
                    self.page.wait_for_function('''id=>{const s=window.__tbbDetailBatch;return !s || s.id!==id || s.ready.length>0;}''',arg=batch_id,timeout=remaining*1000,polling=100)
                    replies=self.page.evaluate('''id=>{const s=window.__tbbDetailBatch;return !s || s.id!==id ? null : s.ready.splice(0);}''',batch_id)
                    if replies is None:raise t.SessionExpired('Retained document changed during detail batch')
                    for reply in replies:
                        reg=reply['reg']
                        if reg not in pending:raise t.ExtractionError('Unexpected or repeated detail response')
                        record=pending.pop(reg);self.account(reply,detail=True)
                        self.detail_payloads.append({k:reply.get(k) for k in ('reg','raw_html_bytes','returned_html_bytes','attempts')})
                        if reply.get('post_ms') is not None:self.detail_timings.append(reply['post_ms'])
                        try:
                            if reply.get('error'):
                                transport_failed.append(reg)
                                self.event('retained_detail_request_failed',json.dumps({'registration':reg,'error_type':reply['error'],'attempts':reply.get('attempts',1)}))
                                raise t.SessionExpired('Detail transport failed after bounded same-session recovery')
                            self.validate(reply);updated=t.parse_detail(reply['html'],record)
                        except (t.ExtractionError,t.VerificationRequired,t.SessionExpired) as error:
                            errors.append(error);continue
                        if self.on_detail_extracted:self.on_detail_extracted(updated)
                        completed[reg]=updated
                        self.event('retained_detail_saved','registration='+reg)
                if errors:
                    if completed and transport_failed and len(transport_failed)==len(errors) and self.page.evaluate(
                            "() => navigator.onLine && !!document.querySelector('#avForm input[name=ad]') && !!window.__retainedListing?.form"):
                        # Only the failed identity is deferred. Real disconnects,
                        # challenges and all-failed batches still escalate.
                        raise t.DetailRequestDeferred(transport_failed)
                    # Access failures take priority, preserving all good results
                    # before bounded refresh/reconnect or source-error retry.
                    raise next((e for e in errors if isinstance(e,t.VerificationRequired)),next((e for e in errors if isinstance(e,t.SessionExpired)),errors[0]))
                return [completed[r['bar_registration_number']] for r in records]
            except BaseException as error:
                if isinstance(error,(t.RuntimeBudgetExceeded,KeyboardInterrupt)):raise
                self.needs_session_renewal=t.recoverable_browser_error(error) or 'Timeout' in type(error).__name__
                if self.needs_session_renewal:
                    self.invalidate();raise t.SessionExpired('Compact detail batch interrupted; saved results retained') from error
                raise
            finally:
                try:
                    self.page.evaluate('''id=>{const s=window.__tbbDetailBatch;if(s && s.id===id){s.controllers.forEach(c=>c.abort());delete window.__tbbDetailBatch;}}''',batch_id)
                except Exception:self.invalidate()
    return RetainedDirectoryBrowser

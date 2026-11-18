"""Adapter for TBB's November 2026 JSON directory, inside the verified browser.

Uses the same endpoints and payloads as the public avukat-arama.js frontend.
Canonical numeric bar IDs remain the checkpoint identity; names are wire values.
"""
import json
import re
from html import escape
from pathlib import Path

REQUEST = r'''async ({endpoint,body,timeout}) => {
 const form=document.querySelector('#avSearch');
 const csrf=form?.querySelector('[name="__RequestVerificationToken"]')?.value;
 if(!csrf) return {status:0,error:'Directory CSRF token absent'};
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
 try {
  const response=await fetch('/AvukatArama/'+endpoint,{
   method:'POST',credentials:'same-origin',signal:controller.signal,
   headers:{'Content-Type':'application/json',RequestVerificationToken:csrf},
   body:JSON.stringify(body)});
  if(new URL(response.url).origin!==location.origin)return {status:0,error:'Unexpected redirect'};
  const data=await response.json().catch(()=>null);
  return {status:response.status,data};
 } catch(error) {return {status:0,error:error.name};}
 finally {clearTimeout(timer);}
}'''


def bar_key(value):
    value=str(value).strip().replace('İ','i').replace('I','ı').lower()
    value=re.sub(r'\s+barosu$', '', value)
    value=re.sub(r'\s+1\s*\.?\s*nolu$', '', value)
    value=' '.join(value.split())
    return {'hakkâri':'hakkari'}.get(value,value)


class ModernDirectory:
    def __init__(self, driver, t):
        self.driver,self.t=driver,t
        self.authorized=False
        self.rejected_token_recovered=False
        catalog=json.loads(Path(__file__).with_name('bar_catalog.json').read_text())['bars']
        self.catalog={bar_key(b['label']):b for b in catalog}
        self.wire={}

    def options(self):
        options=self.driver.loc('baro').locator('option').evaluate_all(
            'els=>els.map(e=>({label:e.textContent.trim(),value:e.value,disabled:e.disabled}))')
        result=[]
        seen=set()
        for option in options:
            if not option['value'] or option['disabled']:continue
            entry=self.catalog.get(bar_key(option['value']))
            if not entry or entry['id'] in seen:
                raise self.t.ExtractionError('Unmapped or duplicate modern bar option; checkpoint IDs unchanged')
            seen.add(entry['id']);self.wire[entry['id']]=option['value']
            result.append({'label':entry['label'],'value':entry['id'],'disabled':False})
        return result

    def service_bar(self, bar_id):
        if not self.wire:self.options()
        value=self.wire[str(bar_id)]
        if bar_key(value) in ('ankara','istanbul'):
            return value.removesuffix(' Barosu')+' 1 Nolu Barosu'
        return value

    def request(self, endpoint, body):
        d=self.driver
        if hasattr(d,'stats'):
            d.stats['detail_post_attempts' if endpoint=='detay' else 'search_post_attempts']+=1
        reply=d.page.evaluate(REQUEST,{'endpoint':endpoint,'body':body,'timeout':d.args.navigation_timeout*1000})
        if reply['status']==0:
            raise self.t.SessionExpired('Modern directory request failed; checkpoint retained')
        data=reply.get('data')
        if (endpoint=='sorgula' and reply['status']==400 and isinstance(data,dict)
                and 'Güvenlik doğrulaması başarısız' in str(data.get('error',''))
                and not self.authorized and not self.rejected_token_recovered
                and getattr(d.args,'_solver',None)):
            # A browser-produced token is not proof of server acceptance. Try
            # one ordinary-widget solve, charged to the existing solver ledger.
            self.rejected_token_recovered=True
            d.solve_turnstile(d.args._solver)
            body={**body,'turnstile':d.page.locator('[name="cf-turnstile-response"]').first.input_value()}
            return self.request(endpoint,body)
        if reply['status']!=200 or not isinstance(data,dict):
            # Never interpret rejection, HTML challenge or a malformed reply as zero results.
            reason=self.t.redact(str(data.get('error','')) if isinstance(data,dict) else '')[:300]
            raise self.t.VerificationRequired(f'Modern directory rejected {endpoint}: HTTP {reply["status"]} {reason}')
        self.authorized=True
        if hasattr(d,"event"):d.event("modern_directory_response",endpoint+" accepted")
        return data

    def listing(self, item, bar_id):
        t=self.t
        expected=self.catalog.get(bar_key(item.get('baro','')))
        if not expected or expected['id']!=str(bar_id):raise t.ExtractionError('Modern response bar identity mismatch')
        reg=str(item.get('baroSicil') or '')
        if not re.fullmatch(r'[0-9]{1,8}',reg) or int(reg)==0:raise t.ExtractionError('Modern response missing local registration')
        if not item.get('ad') or not item.get('soyad'):raise t.ExtractionError('Modern response missing name')
        rec={'bar_association_id':str(bar_id),'bar_association':expected['label'],
             'bar_registration_number':reg,'_detail_index':'json:'+reg,'first_name':t.clean(item['ad']),'last_name':t.clean(item['soyad']),
             'source_url':durl(self.driver),'profile_url':'','scraped_at':t.now(),'detail_status':'pending'}
        rec['full_name']=t.clean(rec['first_name']+' '+rec['last_name'])
        rec['_field_availability']={f:'present' if rec.get(f) else 'not_in_listing' for f in t.FIELDS if f not in ('source_queries','field_availability')}
        return rec

    def submit(self, baro, surname, name, registration=''):
        d=self.driver
        d.wait_for_turnstile()
        token=d.page.locator('[name="cf-turnstile-response"]').first.input_value() if d.page.locator('[name="cf-turnstile-response"]').count() else ''
        if self.authorized:token=''  # frontend consumes the token on the first accepted search
        body={'ad':name,'soyad':surname,'sicil':registration,'baro':self.service_bar(baro),
              'tip':'s' if getattr(d.args,'trainees',False) else 'a','sayfa':1,'sayfaBoyutu':20,'turnstile':token}
        records=[];seen=set();pages=0;known_total=None
        while True:
            data=self.request('sorgula',body)
            counts=[data.get(k) for k in ('toplamKayit','toplamSayfa','sayfa')]
            if any(type(n) is not int for n in counts):raise self.t.ExtractionError('Modern pagination metadata missing')
            count,page_count,page=counts
            if count<0 or page_count<0 or page!=body['sayfa']:
                raise self.t.ExtractionError('Invalid modern pagination metadata')
            items=data.get('kayitlar')
            if not isinstance(items,list) or len(items)>20 or count<len(items):
                raise self.t.ExtractionError('Modern listing missing or inconsistent')
            if page==1 and count>len(items):known_total=count
            if known_total is not None and count!=known_total:
                raise self.t.ExtractionError('Modern reported total changed during traversal')
            pages+=1
            if not items:
                # Observed service probes the next page and then revises its
                # page hint backwards (1/2 with one row -> empty 2/1).
                # An empty first page with a positive count is not evidence of
                # an empty query. Nor is an empty page with advertised successors.
                if (page==1 and count!=0) or page_count>=page and not (page==1 and count==0 and page_count<=1):
                    raise self.t.ExtractionError('Modern pagination ended without a terminal response')
                break
            if page_count<page:raise self.t.ExtractionError('Modern nonempty page beyond advertised end')
            for item in items:
                rec=self.listing(item,baro);key=rec['bar_registration_number']
                if key in seen:raise self.t.ExtractionError('Duplicate modern paginated identity')
                seen.add(key);records.append(rec)
            if page==page_count:
                if count>len(records):raise self.t.ExtractionError('Modern terminal page omits reported records')
                break
            body['sayfa']+=1;body['turnstile']=''
        # toplamKayit/page hints are revised by the live service; the verified
        # traversal, not the first hint, supplies the exact returned row count.
        if known_total is not None and len(records)!=known_total:
            raise self.t.ExtractionError('Modern traversal did not reach reported total')
        return records,len(records),pages

    def detail(self, record, query):
        d=self.driver
        if d.last_query!=query:d.fetch(*query)
        matches=[r for r in d.last_result or [] if r['bar_registration_number']==record['bar_registration_number'] and r['bar_association_id']==record['bar_association_id']]
        if len(matches)!=1:raise self.t.ListingIdentityMissing([record['bar_registration_number']])
        data=self.request('detay',{'tip':'s' if getattr(d.args,'trainees',False) else 'a',
             'baro':self.service_bar(record['bar_association_id']),'sicil':record['bar_registration_number'],'turnstile':''})
        item=data.get('kayit')
        if not isinstance(item,dict):raise self.t.ExtractionError('Modern detail missing')
        actual=self.listing(item,record['bar_association_id'])
        if any(actual[k]!=record[k] for k in ('bar_registration_number','first_name','last_name')):
            raise self.t.ExtractionError('Modern detail identity does not match listing')
        fields={'tbbSicil':'TBB Sicil No','baroSicil':'Baro Sicil No','cep':'Cep Telefonu',
                'is':'İş Telefonu','fax':'Fax','eposta':'E-Posta','kep':'KEP','adres':'Adres'}
        # Reuse the audited contact normalization/evidence parser. Only keys
        # actually returned by the service become fields; absence is not blank.
        if 'eposta' not in item:raise self.t.ExtractionError('Modern detail email field absent; not a checked blank')
        rows=''.join('<tr><td>'+label+'</td><td>'+escape(str(item[key] or ''))+'</td></tr>' for key,label in fields.items() if key in item)
        html='<form id="avForm"><h1>'+escape(actual['full_name'])+'<small>'+escape(actual['bar_association'])+'</small></h1><table>'+rows+'</table></form>'
        updated=self.t.parse_detail(html,record)
        updated['_detail_field_evidence']['source_format']='tbb_json_2026_11'
        if d.on_detail_extracted:d.on_detail_extracted(updated)
        return updated

    def details(self, records, query):
        if len(records)>2:raise self.t.ExtractionError('At most two details per batch')
        # Commit each detail through the existing callback before the next request.
        return [self.detail(record,query) for record in records]


def durl(driver):
    return driver.page.url

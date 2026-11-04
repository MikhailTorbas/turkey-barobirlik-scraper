#!/usr/bin/env python3
"""TBB lawyer directory scraper with optional bounded CapSolver verification.

The live directory was inspected on 2026-10-14: substring name matching,
83 bar associations, 1,000-row listing ceiling, POST-backed detail buttons.
See VALIDATION.md for what was and was not verified.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import re
import sqlite3
import signal
import sys
import time
import unicodedata
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import uuid

from bs4 import BeautifulSoup
from turnstile_solver import (CapSolver, SolverError, SolverBudgetExceeded, SolverTransportError,
    CAPTURE_SCRIPT, DISCOVER_SCRIPT, APPLY_SCRIPT)

URL = 'https://www.barobirlik.org.tr/AvukatArama'
ALPHABET = 'ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZQWX'
FIELDS = ['full_name', 'first_name', 'last_name', 'bar_association',
          'bar_association_id', 'bar_registration_number', 'tbb_registration_number', 'professional_status',
          'email', 'phone', 'mobile_phone', 'office_phone', 'fax', 'kep', 'address',
          'city', 'district', 'postal_code', 'website', 'profile_url', 'source_url',
          'scraped_at', 'detail_status', 'field_availability', 'source_queries']
CONTACT_FIELDS = ['email', 'phone', 'address', 'bar_registration_number',
                  'tbb_registration_number', 'profile_url', 'kep', 'website',
                  'professional_status', 'city', 'district', 'postal_code']
LOG = logging.getLogger('tbb')
SECRET_VALUES = []

def redact(message):
    message = str(message)
    for secret in sorted(SECRET_VALUES, key=len, reverse=True):
        if secret:
            message = message.replace(secret, '[redacted]')
    return re.sub(r'(?i)(apikey|api_key|token|password|authorization)([=:\s]+)([^\s&]+)', r'\1\2[redacted]', message)

class SecretFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def clean(v):
    return re.sub(r'\s+', ' ', str(v if v is not None else '')).strip()


def turkish_upper(v):
    return unicodedata.normalize('NFC', clean(v)).replace('i', 'İ').replace('ı', 'I').upper()


def label_key(v):
    s = ''.join(c for c in unicodedata.normalize('NFD', turkish_upper(v))
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^A-Z0-9]+', ' ', s).strip()


def prefix_pairs(alphabet=ALPHABET):
    # Kept name for compatibility; these are substrings, not prefixes.
    return [a + b for a in alphabet for b in alphabet]


def seed_filters(seed, primary_field):
    if primary_field == 'both':
        return [(seed, ''), ('', seed)]
    return [(seed, '')] if primary_field == 'surname' else [('', seed)]


def canonical_field(header):
    h = label_key(header)
    exact = {'AD': 'first_name', 'ADI': 'first_name', 'SOYAD': 'last_name',
             'SOYADI': 'last_name', 'BARO': 'bar_association',
             'AD SOYAD': 'full_name', 'ADI SOYADI': 'full_name',
             'TBB SICIL NO': 'tbb_registration_number',
             'CEP TELEFONU': 'mobile_phone', 'IS TELEFONU': 'office_phone',
             'FAX': 'fax', 'FAKS': 'fax', 'KEP': 'kep', 'ADRES': 'address',
             'IL': 'city', 'SEHIR': 'city', 'ILCE': 'district',
             'POSTA KODU': 'postal_code', 'WEB': 'website',
             'WEB SITESI': 'website', 'DURUM': 'professional_status'}
    if h in exact:
        return exact[h]
    if h.startswith('TBB') and 'SICIL' in h:
        return 'tbb_registration_number'
    if 'SICIL' in h or h == 'BARO NO':
        return 'bar_registration_number'
    if any(x in h for x in ('E POSTA', 'EPOSTA', 'EMAIL')):
        return 'email'
    if 'TELEFON' in h or h == 'GSM':
        return 'phone'
    return None


def parse_html_records(html, base_url=URL):
    """Parse the observed TBB result table; never infer names from page text."""
    soup = BeautifulSoup(html, 'html.parser')
    result = []
    for table in soup.select('table'):
        head = table.select_one('thead tr')
        if not head:
            continue
        fields = [canonical_field(e.get_text(' ', strip=True)) for e in head.select('th,td')]
        if not ('first_name' in fields and 'last_name' in fields):
            continue
        for tr in table.select('tbody > tr'):
            cells = tr.select(':scope > td')
            if len(cells) != len(fields):
                raise ExtractionError('Result row column count does not match its headings')
            rec = {f: clean(cells[i].get_text(' ', strip=True)) for i, f in enumerate(fields) if f}
            if not rec.get('first_name') or not rec.get('last_name'):
                raise ExtractionError('Result row has a missing name field')
            rec['full_name'] = clean(rec['first_name'] + ' ' + rec['last_name'])
            rec['source_url'] = base_url
            rec['scraped_at'] = now()
            rec['detail_status'] = 'pending'
            button = tr.select_one('button[name="detay"]')
            if button:
                rec['_detail_index'] = button.get('value', '')
            # Detail is a POST action at the same URL, not a stable profile link.
            rec['profile_url'] = ''
            rec['_field_availability'] = {f: 'present' if rec.get(f) else 'not_in_listing'
                                          for f in FIELDS if f not in ('source_queries', 'field_availability')}
            result.append(rec)
    return result


def contact_addresses(value):
    """Extract source-written addresses; never join fragments or invent domains."""
    pattern=r"(?<![\w@])[\w.!#$%&'*+/=?^`{|}~+-]+@(?:[\w](?:[\w-]*[\w])?\.)+[^\W\d_][\w-]{1,62}(?![\w@])"
    result=[]
    for match in re.finditer(pattern,value or '',re.UNICODE):
        address=match.group().strip('.')
        if address.casefold() not in {a.casefold() for a in result}:result.append(address)
    return result


def parse_detail(html, listing=None):
    soup = BeautifulSoup(html, 'html.parser')
    # Cloudflare renders these public addresses client-side in normal tabs.
    # Browser-session HTML requests retain the encoded span/link instead.
    for element in soup.select('[data-cfemail], a[href*="/cdn-cgi/l/email-protection#"]'):
        # Empty anchors can carry a contact href without displaying a KEP.
        # Match the rendered page: never turn an empty link into a value.
        if not element.has_attr('data-cfemail') and not element.get_text(strip=True):
            continue
        encoded = element.get('data-cfemail')
        if not encoded:
            encoded = element.get('href', '').partition('#')[2]
        try:
            payload = bytes.fromhex(encoded)
            if len(payload) < 2:
                raise ValueError('empty protected email')
            address = bytes(value ^ payload[0] for value in payload[1:]).decode('utf-8')
        except (ValueError, UnicodeDecodeError):
            raise ExtractionError('Cannot decode protected email; detail remains pending')
        element.string = address
    found, states, invalid_contacts,contact_evidence = {}, {}, {},{}
    for table in soup.select('table'):
        for tr in table.select('tr'):
            cells = tr.select(':scope > td')
            if len(cells) < 2:
                continue
            strong = cells[0].select_one('strong')
            field = canonical_field((strong or cells[0]).get_text(' ', strip=True))
            if field:
                value = clean(cells[-1].get_text(' ', strip=True))
                if field == 'address' and not re.search(r'\w', value, re.UNICODE):
                    value = ''
                addresses=contact_addresses(value) if field in ('email','kep') and value else []
                if field in ('email','kep') and addresses:
                    normalized='; '.join(addresses)
                    if normalized!=value:contact_evidence[field]={'raw':value,'addresses':addresses,'method':'source_address_tokens'}
                    found[field]=normalized;states[field]='present'
                elif field in ('email', 'kep') and value:
                    # Decoding and address validity are separate. Keep malformed
                    # source data auditable without inventing a missing domain.
                    invalid_contacts[field] = [value]
                    found[field] = ''
                    states[field] = 'invalid_on_site'
                else:
                    found[field] = value
                    states[field] = 'present' if value else 'blank_on_site'
    if not found.get('bar_registration_number'):
        raise ExtractionError('Detail view has no TBB/bar registration identifiers')
    listing = listing or {}
    if listing.get('bar_registration_number') and clean(listing['bar_registration_number']) != found['bar_registration_number']:
        raise ExtractionError('Detail registration number does not match listing')
    if not found.get('tbb_registration_number'):
        # Some genuine profiles have an explicitly empty TBB field. Accept
        # them only with the official bar number plus independently displayed
        # full name AND bar heading matching the selected listing record.
        heading = soup.select_one('#avForm h1')
        bar_heading = heading.select_one('small') if heading else None
        name_heading = BeautifulSoup(str(heading), 'html.parser') if heading else None
        if name_heading:
            for small in name_heading.select('small'): small.decompose()
        expected_name = listing.get('full_name') or clean(listing.get('first_name', '') + ' ' + listing.get('last_name', ''))
        corroborated = (listing.get('bar_registration_number') and expected_name and listing.get('bar_association')
                        and name_heading and bar_heading
                        and turkish_upper(clean(name_heading.get_text(' ', strip=True))) == turkish_upper(clean(expected_name))
                        and turkish_upper(clean(bar_heading.get_text(' ', strip=True))) == turkish_upper(clean(listing['bar_association'])))
        if not corroborated:
            raise ExtractionError('Missing TBB identifier without matching bar/name heading evidence')
        found['_identity_verification'] = {'basis':'bar_number_and_displayed_name_and_bar',
            'tbb_blank_on_site':states.get('tbb_registration_number')=='blank_on_site',
            'tbb_field_status':states.get('tbb_registration_number','not_displayed_on_detail')}
    # Name/status/bar are outside the contact table. Restrict to the actual form.
    form = soup.select_one('#avForm')
    if form:
        # Search controls include both lawyer and trainee labels on detail
        # pages. Only a dedicated heading identifies this record's category.
        categories = [turkish_upper(clean(h.get_text(' ', strip=True)))
                      for h in form.select('h1,h2,h3,h4,h5,h6')]
        found['professional_status'] = next((c for c in categories
            if c in ('AVUKAT', 'STAJYER AVUKAT')), '')
    phones = [found.get(f, '') for f in ('mobile_phone', 'office_phone', 'phone')]
    found['phone'] = '; '.join(dict.fromkeys(p for p in phones if p))
    states['phone'] = 'present' if found['phone'] else 'blank_on_site'
    found['detail_status'] = 'done'
    found['scraped_at'] = now()
    availability = dict(listing.get('_field_availability', {}))
    for f in CONTACT_FIELDS + ['mobile_phone', 'office_phone', 'fax']:
        availability[f] = states.get(f, 'present' if listing.get(f) else 'not_displayed_on_detail')
    found['_field_availability'] = availability
    if contact_evidence:found['_contact_value_evidence']=contact_evidence
    found['_detail_field_evidence'] = {'observed_at': found['scraped_at'],
                                       'states': dict(availability)}
    if invalid_contacts:
        found['_invalid_contact_values'] = invalid_contacts
    return merge_record(listing, found)


def count_hint(text):
    for pat in (r'([0-9][0-9.,]*)\s*kay[iı]t\s*listelendi',
                r'(?:toplam|total)\s*[:=]?\s*([0-9][0-9.,]*)\s*(?:adet\s*)?(?:kay[iı]t|sonu[cç]|results?|avukat)',
                r'(?:sonu[cç]|kay[iı]t)\s*say[iı]s[iı]\s*[:=]?\s*([0-9][0-9.,]*)'):
        m = re.search(pat, text, re.I)
        if m:
            return int(re.sub(r'[.,]', '', m.group(1)))
    return None


def record_key(rec):
    baro = clean(rec.get('bar_association_id')) or turkish_upper(rec.get('bar_association'))
    reg = clean(rec.get('bar_registration_number'))
    if baro and reg:
        raw = f'bar:{baro}|reg:{reg}'
    elif rec.get('tbb_registration_number'):
        raw = 'tbb:' + clean(rec['tbb_registration_number'])
    else:
        # Names/contact fields are not proof of identity. Keep unidentified
        # observations separate and expose them for review instead of merging.
        raw = 'observation:' + rec.get('_observation_id', str(uuid.uuid4()))
    return hashlib.sha256(raw.encode()).hexdigest()


def merge_record(old, new):
    merged = dict(old)
    conflicts = dict(old.get('_conflicts', {}))
    for k, v in new.items():
        if k.startswith('_'):
            continue
        value, before = clean(v), clean(old.get(k))
        if k not in merged or (value and not before):
            merged[k] = v
        elif k == 'detail_status' and value:
            merged[k] = 'done' if before == 'done' else value
        elif k == 'scraped_at' and value:
            # Rediscovery is not evidence that old contact details were rechecked.
            if new.get('detail_status')=='done' or old.get('detail_status')!='done':merged[k] = value
        elif before and value and before != value:
            if k in ('email', 'phone', 'office_phone', 'mobile_phone'):
                merged[k] = '; '.join(dict.fromkeys(before.split('; ') + value.split('; ')))
            else:
                conflicts[k] = sorted(set(conflicts.get(k, []) + [before, value]))
    invalid = {k:list(v) for k,v in old.get('_invalid_contact_values', {}).items()}
    for field, values in new.get('_invalid_contact_values', {}).items():
        invalid[field] = list(dict.fromkeys(invalid.get(field, []) + values))
    if invalid:
        merged['_invalid_contact_values'] = invalid
    merged['_origins'] = sorted(set(old.get('_origins', [])) | set(new.get('_origins', [])))
    availability = dict(old.get('_field_availability', {}))
    for field, state in new.get('_field_availability', {}).items():
        # A listing has no email/contact evidence. Rediscovery must not erase
        # an earlier detail-page observation, including an explicit blank.
        if state == 'not_in_listing' and availability.get(field) not in (None, 'not_in_listing', 'not_checked'):
            continue
        availability[field] = state
    merged['_field_availability'] = availability
    if new.get('_detail_field_evidence'):
        merged['_detail_field_evidence'] = new['_detail_field_evidence']
    if new.get('_contact_value_evidence'):
        merged['_contact_value_evidence']={**old.get('_contact_value_evidence',{}),**new['_contact_value_evidence']}
    merged['_last_seen_at']=new.get('scraped_at') or old.get('_last_seen_at')
    if new.get('_identity_verification'):
        merged['_identity_verification'] = new['_identity_verification']
    if new.get('_lookup_registration'):
        if clean(new['_lookup_registration']) != clean(merged.get('bar_registration_number')):
            raise ExtractionError('Exact lookup recovery identity differs from the record')
        merged['_lookup_registration'] = str(new['_lookup_registration'])
    # A previously observed value remains present when a later page leaves it blank.
    for k in merged['_field_availability']:
        if merged.get(k):
            merged['_field_availability'][k] = 'present'
    if conflicts:
        merged['_conflicts'] = conflicts
    for k in ('_detail_index', '_observation_id'):
        if k in new:
            merged[k] = new[k]
    return merged


class ExtractionError(RuntimeError):
    pass


class ListingIdentityMissing(ExtractionError):
    def __init__(self, registrations):
        self.registrations = set(registrations)
        super().__init__('Detail identity absent or ambiguous in current listing: ' + ', '.join(sorted(self.registrations)))


class DetailRequestDeferred(ExtractionError):
    """A failed individual request beside a successful sibling in a live form."""
    def __init__(self,registrations):
        self.registrations=set(registrations)
        super().__init__('Individual detail request deferred; verified browser retained')


class VerificationRequired(RuntimeError):
    pass

class SessionExpired(RuntimeError):
    pass


class RuntimeBudgetExceeded(KeyboardInterrupt):
    """Stop without treating an unfinished job as a failed extraction."""

def session_was_closed(error):
    if isinstance(error, SessionExpired):
        return True
    message = str(error).lower()
    return any(text in message for text in ('target page, context or browser has been closed', 'browser has been closed', 'connection closed', 'browser disconnected'))

def navigation_in_progress(error):
    message = str(error).lower()
    return any(text in message for text in ('execution context was destroyed', 'cannot find context with specified id',
                                            'execution context is not available in detached frame'))


def recoverable_browser_error(error):
    return (session_was_closed(error) or navigation_in_progress(error)
            or any(text in str(error).lower() for text in
                   ('net::err_timed_out', 'net::err_connection_closed', 'net::err_connection_reset', 'page.goto: timeout')))


def partition(surname, name, max_length=5, alphabet=ALPHABET):
    """Conditional substring cover, refining both fields independently.

    Cross-field grams alone lose short or foreign-character given names. Own
    field extensions rescue those records; refining both axes also avoids
    stopping at an exact short field while the other field can still split.
    Exact-filter names and characters outside the configured alphabet remain
    explicit gaps, so these partitions are never a national completeness proof.
    """
    children = set()
    if not name:
        children.update((surname, p) for p in prefix_pairs(alphabet))
    if not surname:
        children.update((p, name) for p in prefix_pairs(alphabet))
    for field, value in (('surname', surname), ('name', name)):
        if not value or len(value) >= max_length:
            continue
        extensions = {c + value for c in alphabet} | {value + c for c in alphabet}
        children.update((p, name) if field == 'surname' else (surname, p) for p in extensions)
    if not children:
        return [], 'both filters reached maximum length; cap unresolved'
    return sorted(children), ('exact-length names and substring boundaries outside the configured alphabet; '
                              'both-field extension and cross-field searches required')


def atomic_text(path, text):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    os.replace(tmp, path)


def population_comparison(baseline, bars, records):
    if not baseline:
        return {'status': 'no baseline supplied'}
    def association_key(value):
        return label_key(value).removesuffix(' BAROSU')
    official = {association_key(b['bar_association']): int(b['count']) for b in baseline['bars']}
    comparison = []
    for bar in bars:
        count = sum(r.get('bar_association_id') == bar['id'] for r in records)
        population = official.get(association_key(bar['label']))
        comparison.append({'bar_id':bar['id'], 'bar_association':bar['label'],
            'extracted':count, 'official_count':population,
            'extracted_to_dated_population_pct':round(100*count/population,2) if population else None})
    return {'as_of':baseline['as_of'], 'source_url':baseline['source_url'],
        'definition':baseline['definition'], 'official_national_total':sum(official.values()),
        'comparison':comparison,
        'limitations':'Historical population ratio, not a measured coverage rate. Directory date differs; transfers, new registrations, deregistrations, and category definitions can change counts.'}


class Database:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bars(id TEXT PRIMARY KEY,label TEXT NOT NULL,selected INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS queries(
          id INTEGER PRIMARY KEY,baro TEXT NOT NULL,surname TEXT NOT NULL,name TEXT NOT NULL,
          status TEXT DEFAULT 'pending',attempts INTEGER DEFAULT 0,seen INTEGER DEFAULT 0,
          total_hint INTEGER,pages INTEGER DEFAULT 0,capped INTEGER DEFAULT 0,error TEXT DEFAULT '',
          updated_at TEXT DEFAULT '',UNIQUE(baro,surname,name));
        CREATE TABLE IF NOT EXISTS edges(parent INTEGER,child INTEGER,PRIMARY KEY(parent,child));
        CREATE TABLE IF NOT EXISTS gaps(query_id INTEGER PRIMARY KEY,reason TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS lawyers(key TEXT PRIMARY KEY,json TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS details(key TEXT PRIMARY KEY,query_id INTEGER NOT NULL,
          status TEXT DEFAULT 'pending',attempts INTEGER DEFAULT 0,error TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS observations(query_id INTEGER,page INTEGER,position INTEGER,key TEXT,
          PRIMARY KEY(query_id,page,position));
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,at TEXT,kind TEXT,message TEXT);
        CREATE INDEX IF NOT EXISTS detail_status_index ON details(status,query_id);
        ''')
        # Old scaffold schema is incompatible; don't silently corrupt/reuse it.
        cols = {r['name'] for r in self.db.execute('PRAGMA table_info(queries)')}
        if 'id' not in cols:
            raise RuntimeError('Old preliminary checkpoint detected. Use a new output directory.')
        detail_cols = {r['name'] for r in self.db.execute('PRAGMA table_info(details)')}
        if 'failures' not in detail_cols:
            self.db.execute('ALTER TABLE details ADD COLUMN failures INTEGER DEFAULT 0')
        self.db.commit()

    def metadata(self, key, value=None):
        if value is not None:
            self.db.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                            (key, json.dumps(value, ensure_ascii=False)))
            self.db.commit()
        row = self.db.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def event(self, kind, message):
        self.db.execute('INSERT INTO events(at,kind,message) VALUES(?,?,?)', (now(), kind, redact(message)[:2000]))
        self.db.commit()

    def put_query(self, baro, surname, name='', parent=None, budget=250000):
        existing = self.db.execute('SELECT id FROM queries WHERE baro=? AND surname=? AND name=?', (baro, surname, name)).fetchone()
        if not existing:
            if self.db.execute('SELECT count(*) FROM queries').fetchone()[0] >= budget:
                raise ExtractionError('Query budget reached; remaining partitions require review')
            self.db.execute('INSERT INTO queries(baro,surname,name) VALUES(?,?,?)', (baro, surname, name))
            existing = self.db.execute('SELECT id FROM queries WHERE baro=? AND surname=? AND name=?', (baro, surname, name)).fetchone()
        if parent is not None:
            self.db.execute('INSERT OR IGNORE INTO edges VALUES(?,?)', (parent, existing[0]))
        self.db.commit()
        return existing[0]

    def take_query(self):
        # Breadth-first allows regions to make progress even if one is dense.
        row = self.db.execute("SELECT q.* FROM queries q JOIN bars b ON q.baro=b.id WHERE b.selected=1 AND q.status='pending' ORDER BY length(q.surname)+length(q.name), q.id LIMIT 1").fetchone()
        if row:
            self.db.execute("UPDATE queries SET status='running',attempts=attempts+1,updated_at=? WHERE id=?", (now(), row['id']))
            self.db.commit()
        return dict(row) if row else None

    def finish(self, qid, status, **values):
        allowed = {'seen', 'total_hint', 'pages', 'capped', 'error'}
        if not set(values) <= allowed:
            raise ValueError('Unknown query columns')
        if 'error' in values:
            values['error'] = redact(values['error'])
        assignments = ','.join(f'{k}=?' for k in values)
        sql = 'UPDATE queries SET status=?,updated_at=?' + (',' + assignments if assignments else '') + ' WHERE id=?'
        self.db.execute(sql, (status, now(), *values.values(), qid))
        self.db.commit()

    def recover(self, retry_failed=False, retry_review=False):
        self.db.execute("UPDATE queries SET status='pending' WHERE status IN ('running','verification')")
        self.db.execute("UPDATE details SET status='pending' WHERE status IN ('running','verification')")
        if retry_failed:
            self.db.execute("UPDATE queries SET status='pending' WHERE status='failed'")
            self.db.execute("UPDATE details SET status='pending' WHERE status='failed'")
        if retry_review:
            count = self.db.execute("SELECT count(*) FROM details WHERE status='needs_review'").fetchone()[0]
            self.db.execute("UPDATE details SET status='pending',failures=0 WHERE status='needs_review'")
            self.db.execute("INSERT INTO events(at,kind,message) VALUES(?,?,?)",
                            (now(), 'review_retries_authorized', f'{count} detail records released for another bounded attempt'))
        self.db.commit()

    def upsert(self, record, query_id=None, page=1, position=0, commit=True):
        # Stabilize unidentified row replay within the same query/page/position.
        record = dict(record)
        if query_id is not None:
            record.setdefault('_observation_id', f'{query_id}:{page}:{position}')
        key = record_key(record)
        row = self.db.execute('SELECT json FROM lawyers WHERE key=?', (key,)).fetchone()
        if row:
            record = merge_record(json.loads(row[0]), record)
        self.db.execute('INSERT INTO lawyers VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET json=excluded.json,updated_at=excluded.updated_at',
                        (key, json.dumps(record, ensure_ascii=False), now()))
        if query_id is not None:
            self.db.execute('INSERT OR REPLACE INTO observations VALUES(?,?,?,?)', (query_id, page, position, key))
            if record.get('_detail_index') and record.get('detail_status') != 'done':
                self.db.execute('INSERT OR IGNORE INTO details(key,query_id) VALUES(?,?)', (key, query_id))
        if commit:self.db.commit()
        return key

    def record(self, key):
        return json.loads(self.db.execute('SELECT json FROM lawyers WHERE key=?', (key,)).fetchone()[0])

    def detail_jobs(self, query_id):
        return [dict(r) for r in self.db.execute("SELECT * FROM details WHERE query_id=? AND status='pending'", (query_id,))]

    def detail_state(self, key, status, error='', failure_limit=3, commit=True):
        if status == 'failed':
            self.db.execute('UPDATE details SET failures=failures+1 WHERE key=?', (key,))
            failures = self.db.execute('SELECT failures FROM details WHERE key=?', (key,)).fetchone()[0]
            if failures >= failure_limit:
                status = 'needs_review'
        if status=='needs_review':
            record=self.record(key);record['detail_status']='needs_review';record['_detail_error']=redact(error)[:1500]
            self.upsert(record,commit=False)
        self.db.execute('UPDATE details SET status=?,attempts=attempts+?,error=? WHERE key=?', (status, int(status == 'running'), redact(error)[:1500], key))
        if commit:self.db.commit()
        return status

    def complete_detail(self, record):
        """Commit the profile and queue completion together, including on stop."""
        if record.get('detail_status')!='done':raise ExtractionError('Completed detail record required')
        key=record_key(record)
        if not self.db.execute('SELECT 1 FROM details WHERE key=?',(key,)).fetchone():
            raise ExtractionError('Completed detail has no queued identity')
        with self.db:
            self.upsert(record,commit=False)
            self.detail_state(key,'done',commit=False)
        return key

    def export(self, dest):
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        records = [json.loads(r[0]) for r in self.db.execute('SELECT json FROM lawyers ORDER BY key')]
        csv_tmp = dest / 'lawyers.csv.tmp'
        with csv_tmp.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, FIELDS)
            writer.writeheader()
            for r in records:
                row = {k: r.get(k, '') for k in FIELDS}
                row['source_queries'] = json.dumps(r.get('_origins', []), ensure_ascii=False)
                row['field_availability'] = json.dumps(r.get('_field_availability', {}), ensure_ascii=False)
                writer.writerow(row)
        os.replace(csv_tmp, dest / 'lawyers.csv')
        atomic_text(dest / 'lawyers.jsonl', ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
        queries = [dict(r) for r in self.db.execute('SELECT * FROM queries ORDER BY id')]
        with (dest / 'query_audit.csv.tmp').open('w', encoding='utf-8-sig', newline='') as f:
            cols = [r['name'] for r in self.db.execute('PRAGMA table_info(queries)')]
            writer = csv.DictWriter(f, cols)
            writer.writeheader()
            writer.writerows(queries)
        os.replace(dest / 'query_audit.csv.tmp', dest / 'query_audit.csv')
        bars = [dict(r) for r in self.db.execute('SELECT * FROM bars ORDER BY id')]
        groups = {'national': records}
        groups.update({b['label']: [r for r in records if r.get('bar_association_id') == b['id']] for b in bars})
        completeness = {}
        for label, group in groups.items():
            completeness[label] = {'unique_lawyers': len(group), 'fields': {}}
            for field in CONTACT_FIELDS:
                counts = Counter(r.get('_field_availability', {}).get(field, 'not_checked') for r in group)
                filled = sum(bool(r.get(field)) for r in group)
                completeness[label]['fields'][field] = {'filled': filled, 'percent': round(100*filled/len(group), 2) if group else 0, 'availability': dict(counts)}
        states = Counter(q['status'] for q in queries)
        dq = Counter(r['status'] for r in self.db.execute('SELECT status FROM details'))
        gaps = [dict(r) for r in self.db.execute('SELECT * FROM gaps')]
        edges = [tuple(r) for r in self.db.execute('SELECT parent,child FROM edges')]
        children = {}
        resolved_cache = {}
        for parent, child in edges:
            children.setdefault(parent, []).append(child)
        by_id = {q['id']: q for q in queries}
        def resolved(qid, visiting=None):
            visiting = set() if visiting is None else visiting
            if qid in visiting:
                return False
            if qid in resolved_cache:
                return resolved_cache[qid]
            q = by_id[qid]
            if q['status'] == 'done':
                return True
            answer = q['status'] == 'split' and bool(children.get(qid)) and all(resolved(c, visiting | {qid}) for c in children[qid])
            resolved_cache[qid] = answer
            return answer
        bar_status = []
        for b in bars:
            qs = [q for q in queries if q['baro'] == b['id']]
            bar_status.append({**b, 'queries': len(qs), 'query_states': dict(Counter(q['status'] for q in qs)),
                               'queue_processed': bool(qs) and all(q['status'] in ('done','split') for q in qs),
                               'has_failures': any(q['status'] == 'failed' for q in qs)})
        attempts = self.db.execute('SELECT count(*) FROM observations').fetchone()[0]
        completed = [r for r in records if r.get('detail_status') == 'done']
        completed_with_email = sum(bool(r.get('email')) for r in completed)
        completed_emails = {e.strip().casefold() for r in completed for e in r.get('email','').split(';') if e.strip()}
        email_summary = {'completed_profiles':len(completed), 'profiles_with_email':completed_with_email,
            'unique_email_addresses':len(completed_emails),
            'fill_percent':round(100*completed_with_email/len(completed),2) if completed else None,
            'empty_email_availability':dict(Counter(r.get('_field_availability',{}).get('email','not_checked')
                                                    for r in completed if not r.get('email'))),
            'denominator':'Completed profiles only; pending, failed and review jobs excluded.'}
        from roster_reconciliation import summary as roster_summary
        reconciliation = roster_summary(self, records)
        report = {'generated_at': now(), 'unique_lawyers': len(records), 'completeness': completeness,
                  'independent_roster_reconciliation': reconciliation,
                  'roster_candidates_unresolved': any(not s['all_source_candidates_observed'] for s in reconciliation['sources']),
                  'completed_profile_email_summary':email_summary,
                  'bars_discovered': len(bars), 'bars_selected': sum(b['selected'] for b in bars),
                  'bars_queue_processed': sum(b['queue_processed'] for b in bar_status),
                  'bars_with_failures': sum(b['has_failures'] for b in bar_status), 'bars': bar_status,
                  'queries_executed': sum(q['attempts'] for q in queries), 'query_states': dict(states),
                  'capped_queries': sum(q['capped'] for q in queries),
                  'capped_queries_with_completed_child_queues': sum(q['capped'] and resolved(q['id']) for q in queries),
                  'capped_queries_proven_exhaustive': 0,
                  'unresolved_queries': [q for q in queries if q['status'] in ('failed','unresolved','verification')],
                  'potential_partition_gaps': gaps, 'details': dict(dq),
                  'details_needing_review': [dict(r) for r in self.db.execute("SELECT key,query_id,attempts,failures,error FROM details WHERE status='needs_review'")],
                  'duplicate_observations_removed': max(0, attempts-len(records)),
                  'ambiguous_identity_records': sum(not (r.get('bar_registration_number') and r.get('bar_association_id')) and not r.get('tbb_registration_number') for r in records),
                  'invalid_source_contacts': [dict(key=record_key(r), values=r['_invalid_contact_values']) for r in records if r.get('_invalid_contact_values')],
                  'field_conflicts': [dict(key=record_key(r), conflicts=r['_conflicts']) for r in records if r.get('_conflicts')],
                  'run_configuration': self.metadata('run_configuration'),
                  'run_status': self.metadata('run_status'),
                  'transport_statistics': self.metadata('transport_statistics'),
                  'startup_statistics': self.metadata('startup_statistics'),
                  'transport_mode': self.metadata('transport_mode'),
                  'solver_usage': self.metadata('solver_usage'),
                  'seed_plan_history': self.metadata('seed_plan_history'),
                  'population_comparison': population_comparison(self.metadata('population_baseline'), bars, records),
                  'suspicious_searches': [q for q in queries if q['error']],
                  'coverage_claim': 'Observed directory subset; no national completeness guarantee.',
                  'warnings': ['Two-letter substring seeds cover names with at least one adjacent pair from the configured alphabet.',
                               'Very short names, punctuation-only boundaries, and foreign letters may be missed; expand --alphabet or supply explicit --prefix searches.',
                               'Substring cap subdivision has conditional coverage; review potential_partition_gaps even after all child queues finish.',
                               'AVUKAT labels a lawyer category; it is not proof of active/practising registration status.',
                               'Profile URLs are blank: observed details are POST views at a shared URL.',
                               'Pending/failed details mean contact availability is unknown, not absent.']}
        atomic_text(dest / 'quality_report.json', json.dumps(report, ensure_ascii=False, indent=2))
        atomic_text(dest / 'events.jsonl', ''.join(json.dumps(dict(r), ensure_ascii=False)+'\n' for r in self.db.execute('SELECT * FROM events')))
        return report


@dataclass
class Config:
    name: str = 'input[name="ad"]'
    surname: str = 'input[name="soyad"]'
    baro: str = 'select[name="baroId"]'
    search: str = 'button[name="tip"][value="Avukat"]'
    result_rows: str = '#avForm table:has(thead) tbody > tr'
    next_page: str = ''


class DirectoryBrowser:
    def __init__(self, page, cfg, args):
        self.page, self.cfg, self.args = page, cfg, args
        self.last_result = None
        self.last_query = None
        self.details_attempted = 0
        self.on_detail_extracted = None
        self.page_events = []
        self.needs_session_renewal = False
        self.startup_stats = {'navigation_attempts':0,'transient_navigation_retries':0,
                              'managed_observations':0,'form_wait_seconds':0}
        if getattr(args, 'capture_failures', False) and hasattr(page, 'on'):
            page.on('pageerror', lambda error: self.page_events.append({'type':'pageerror','message':redact(str(error))[:500]}))
            page.on('requestfailed', lambda request: self.page_events.append({'type':'requestfailed',
                'host':urlparse(request.url).hostname,'path':urlparse(request.url).path,
                'failure':redact(str(request.failure))[:500]}))

    def loc(self, purpose):
        return self.page.locator(getattr(self.cfg, purpose))

    def challenge_required(self):
        # Managed Cloudflare interstitial may have no Turnstile CSS or token.
        try:
            has_form = self.loc('name').count() > 0
            text = self.page.locator('body').inner_text(timeout=2000)
            managed = not has_form and bool(re.search(r'cloudflare|verify you are human|just a moment|security verification|проверки безопасности|один момент', text, re.I))
            if not has_form and hasattr(self.page, 'evaluate'):
                managed = managed or bool(self.page.evaluate('() => !!window._cf_chl_opt'))
            tokens = self.page.locator('[name="cf-turnstile-response"]')
            widget = self.page.locator('.cf-turnstile').count() > 0
            return managed or (widget and (tokens.count() == 0 or not tokens.first.input_value()))
        except Exception:
            return True

    def wait_for_turnstile(self):
        if getattr(self.args, '_solver', None):
            # Do not alter the managed challenge's browser environment before
            # it has loaded the directory. Instrument only the real form.
            try:
                if self.page.evaluate('selector => !!document.querySelector(selector)', self.cfg.name):
                    self.page.evaluate(CAPTURE_SCRIPT)
            except Exception as error:
                if navigation_in_progress(error):
                    return  # The view polling loop will inspect the next document.
                raise
        if not self.challenge_required():
            return
        if self.args.headless or getattr(self.args, 'unattended', True):
            # Let the official widget/browser finish automatic verification normally.
            grace = getattr(self.args, 'auto_verification_timeout', 10)
            # Give an observed form widget a short chance to finish itself;
            # keep the longer automatic wait for an outer managed challenge.
            if getattr(self.args, '_solver', None):
                observed = self.page.evaluate("() => !!document.querySelector('input[name=ad]') && !!document.querySelector('.cf-turnstile[data-sitekey]')")
                if observed:
                    grace = min(grace, getattr(self.args, 'widget_grace', 30))
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline:
                if not self.challenge_required():
                    return
                self.page.wait_for_timeout(500)
            solver = getattr(self.args, '_solver', None)
            if solver:
                self.solve_turnstile(solver)
                return
            raise VerificationRequired('Official automatic verification did not finish; unattended run checkpointed as access_blocked.')
        LOG.warning('Complete normal Cloudflare verification in the visible browser; waiting up to %ss', self.args.captcha_timeout)
        deadline = time.monotonic() + self.args.captcha_timeout
        while time.monotonic() < deadline:
            if not self.challenge_required():
                return
            self.page.wait_for_timeout(1000)
        raise VerificationRequired('Verification timed out. Progress saved; resume after verification.')

    def solve_turnstile(self, solver):
        # A managed interstitial is not assumed equivalent to an ordinary
        # Turnstile widget. Only use parameters actually observed in this page.
        if self.page.evaluate('selector => !!document.querySelector(selector)', self.cfg.name):
            # The real form may have appeared during the automatic wait, after
            # that wait's initial instrumentation check.
            self.page.evaluate(CAPTURE_SCRIPT)
        widgets = self.page.evaluate(DISCOVER_SCRIPT)
        if len(widgets) != 1:
            raise VerificationRequired('Expected one observable Turnstile widget; managed/ambiguous challenge needs a validated adapter')
        widget = widgets[0]
        try:
            LOG.info('Requesting bounded CapSolver Turnstile task')
            token = solver.solve(widget)
            self.page.evaluate(APPLY_SCRIPT, {'widget': widget, 'token': token})
        except SolverBudgetExceeded as error:
            self.args._solver_terminal = True
            raise VerificationRequired(str(error)) from None
        except SolverTransportError as error:
            # A transient provider outage can use the existing bounded access
            # cooldown/retry path. Pending tasks and reserved attempts persist.
            raise VerificationRequired(str(error)) from None
        except SolverError as error:
            self.args._solver_terminal = True
            raise VerificationRequired(str(error)) from None
        except Exception as error:
            if session_was_closed(error):
                raise SessionExpired('Browser closed during Turnstile solve') from None
            raise VerificationRequired('Turnstile response could not be applied to the original widget') from None
        deadline = time.monotonic() + self.args.auto_verification_timeout
        while time.monotonic() < deadline:
            if not self.challenge_required():
                LOG.info('Turnstile response applied; subsequent website response will confirm acceptance')
                return
            self.page.wait_for_timeout(500)
        raise VerificationRequired('Turnstile challenge remained after solver response')

    def directory_state(self):
        """Observe readiness without changing or exporting a managed challenge."""
        return self.page.evaluate('''selectors=>{
          const controls=selectors.map(s=>document.querySelector(s));
          const form=controls[0]?.closest('form');
          const ready=!!form && controls.every(e=>e && e.closest('form')===form)
            && document.readyState!=='loading';
          const text=document.body?.innerText||'';
          return {ready,managed:!ready && (!!window._cf_chl_opt ||
            /cloudflare|verify you are human|just a moment|security verification|проверки безопасности|один момент/i.test(text))};
        }''',[self.cfg.name,self.cfg.surname,self.cfg.baro])

    def wait_for_directory_form(self, deadline):
        started=time.monotonic()
        try:
            while time.monotonic()<deadline:
                try:
                    state=self.directory_state()
                    if state['ready']:
                        LOG.info('Directory search form ready after %.1fs automatic startup wait',time.monotonic()-started)
                        return
                    self.startup_stats['managed_observations']+=int(state['managed'])
                except Exception as error:
                    if session_was_closed(error):raise SessionExpired('Browser closed while waiting for directory form') from None
                    if not navigation_in_progress(error):raise
                self.page.wait_for_timeout(min(500,max(1,(deadline-time.monotonic())*1000)))
            # Never hand an outer managed challenge to the ordinary form solver.
            raise VerificationRequired('Startup deadline reached before a usable directory form; fresh-session access recovery required')
        finally:
            self.startup_stats['form_wait_seconds']+=round(time.monotonic()-started,3)

    def navigate(self, url):
        deadline=time.monotonic()+getattr(self.args,'startup_timeout',120)
        for attempt in range(2):
            self.startup_stats['navigation_attempts']+=1
            try:
                self.page.goto(url,wait_until='commit',
                               timeout=max(1,min(self.args.navigation_timeout,deadline-time.monotonic())*1000))
                break
            except Exception as error:
                if session_was_closed(error):raise SessionExpired('Browser closed during navigation') from None
                interrupted='interrupted by another navigation' in str(error)
                timeout='Timeout' in type(error).__name__ or recoverable_browser_error(error)
                if not (interrupted or timeout):raise
                try:
                    state=self.directory_state()
                except Exception as view_error:
                    if session_was_closed(view_error):raise SessionExpired('Browser closed during navigation') from None
                    if not navigation_in_progress(view_error):raise
                    state={'ready':False,'managed':False}
                # A usable form or live managed view takes priority over a
                # navigation error. Do not cancel an automatic challenge redirect.
                if state['ready'] or state['managed'] or interrupted or navigation_in_progress(error):break
                if attempt or time.monotonic()>=deadline:
                    raise SessionExpired('Initial directory navigation failed after bounded same-session retry') from None
                self.startup_stats['transient_navigation_retries']+=1
                LOG.warning('Initial navigation failed before usable content; retrying once in the same session')
                self.page.wait_for_timeout(500)
        self.wait_for_directory_form(deadline)
        self.wait_for_turnstile()

    def form(self):
        if not self.loc('name').count():
            self.navigate(self.args.url)
        self.wait_for_turnstile()
        if not self.loc('name').count():
            raise VerificationRequired('Directory search form unavailable after navigation; checkpoint retained')

    def baro_options(self):
        self.form()
        return self.loc('baro').locator('option').evaluate_all('els => els.map(e=>({label:e.textContent.trim(),value:e.value,disabled:e.disabled}))')

    def inspect(self, out):
        self.form()
        out.mkdir(parents=True, exist_ok=True)
        info = self.page.evaluate('''()=>({url:location.href, inputs:[...document.querySelectorAll('#avForm input')].map(e=>({name:e.name,type:e.type,placeholder:e.placeholder,maxlength:e.maxLength})),selects:[...document.querySelectorAll('#avForm select')].map(e=>({name:e.name,options:[...e.options].map(o=>({label:o.text,value:o.value}))})),buttons:[...document.querySelectorAll('#avForm button')].map(e=>({name:e.name,value:e.value,text:e.textContent.trim()}))})''')
        atomic_text(out / 'form.json', json.dumps(info, ensure_ascii=False, indent=2))
        self.page.screenshot(path=str(out / 'form.png'), full_page=True)

    def set_control(self, selector, value, select=False):
        # Native HTML control values and their normal input/change events.
        # CAPTCHA inputs are never read into this helper or modified.
        self.page.evaluate('''({selector,value,select}) => {
            const element = document.querySelector(selector);
            if (!element || element.disabled) throw new Error('Form control absent or disabled');
            if (select && ![...element.options].some(o=>o.value === value && !o.disabled))
                throw new Error('Requested bar association is not an available option');
            element.value = value;
            element.dispatchEvent(new Event('input',{bubbles:true}));
            element.dispatchEvent(new Event('change',{bubbles:true}));
            if (element.value !== value) throw new Error('Form value did not persist');
        }''', {'selector':selector,'value':value,'select':select})

    def click_control(self, selector):
        # Perform a normal browser mouse click after checking the live DOM.
        # Locator actions can wait indefinitely on a provider's pending POST
        # navigation even when its next view is already interactive.
        marker = uuid.uuid4().hex
        position = self.page.evaluate('''({selector,marker}) => {
            const element = document.querySelector(selector);
            if (!element || element.disabled) throw new Error('Control absent or disabled');
            element.scrollIntoView({block:'center',inline:'center'});
            const rect = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            if (!rect.width || !rect.height || style.visibility === 'hidden' || style.display === 'none')
                throw new Error('Control is not visible');
            const x = rect.left + rect.width/2, y = rect.top + rect.height/2;
            const target = document.elementFromPoint(x,y);
            if (!target || !element.contains(target)) throw new Error('Control is obscured');
            window.__tbbSubmittedDocument = marker;
            return {x,y};
        }''', {'selector':selector,'marker':marker})
        self._submitted_document = marker
        self.page.mouse.click(position['x'], position['y'])

    def submit(self, baro, surname, name, registration=''):
        self.form()
        self.set_control(self.cfg.baro, baro, select=True)
        self.set_control(self.cfg.surname, surname)
        self.set_control(self.cfg.name, name)
        number = self.page.locator('input[name="barosicil"]')
        if number.count():
            self.set_control('input[name="barosicil"]', registration)
        elif registration:
            raise ExtractionError('Exact registration search control absent')
        self.wait_for_turnstile()
        LOG.info('Submitting bar=%s surname=%s name=%s', baro, surname, name)
        self.click_control(self.cfg.search)
        self.wait_for_view('results')
        return self.result()

    def wait_for_view(self, kind):
        # Hosted browsers may finish a POST view without forwarding a matching
        # navigation event. Verify the actual result/detail DOM instead.
        deadline = time.monotonic() + self.args.navigation_timeout
        while time.monotonic() < deadline:
            try:
                marker = getattr(self, '_submitted_document', None)
                if marker and self.page.evaluate('() => window.__tbbSubmittedDocument || null') == marker:
                    self.page.wait_for_timeout(500)
                    continue
                self.wait_for_turnstile()
                form = self.page.locator('#avForm')
                if form.count():
                    if form.locator('.alert-danger,[role="alert"]').count():
                        return
                    if kind == 'results' and form.locator('table thead').count():
                        return
                    if kind == 'detail' and 'TBB Sicil No' in form.inner_text():
                        return
            except Exception as error:
                if session_was_closed(error):
                    raise SessionExpired('Browser closed while waiting for view') from None
                if not navigation_in_progress(error):
                    raise
            self.page.wait_for_timeout(500)
        raise ExtractionError(f'Expected {kind} view did not appear before timeout')

    def result(self):
        self.wait_for_turnstile()
        soup = BeautifulSoup(self.page.content(), 'html.parser')
        form = soup.select_one('#avForm')
        # The observed DOM is authoritative. Explicit selector waits can block
        # on a pending provider navigation even after the result DOM is ready.
        if form is None:
            raise ExtractionError('Search result form is absent')
        text = form.get_text(' ', strip=True)
        alerts = [x.get_text(' ', strip=True) for x in form.select('.alert-danger,[role="alert"]')]
        if alerts:
            raise ExtractionError('Website validation/error: ' + clean(' '.join(alerts)))
        total = count_hint(text)
        rows = parse_html_records(str(form), self.page.url)
        if not rows and total != 0:
            # Only verified explicit count=0 is a successful empty search.
            if re.search(r'kay[iı]t\s*bulunamad[iı]|sonu[cç]\s*bulunamad[iı]', text, re.I):
                total = 0
            else:
                raise ExtractionError('No recognized result table or explicit zero-result message')
        if total is None:
            raise ExtractionError('Result count not found; cannot confirm extraction completeness')
        if len(rows) != total:
            raise ExtractionError(f'Listing has {len(rows)} parsed rows but reports {total}')
        if soup.select('.pagination, a[rel="next"]'):
            raise ExtractionError('Unexpected pagination appeared; adapter needs validation before marking query complete')
        return rows, total, 1

    def fetch(self, baro, surname, name, registration=''):
        if registration and not re.fullmatch(r'[0-9]{1,7}', str(registration)):
            raise ValueError('Invalid exact registration criterion')
        rows, total, pages = (self.submit(baro, surname, name, str(registration)) if registration
                              else self.submit(baro, surname, name))
        self.last_query = (baro, surname, name, str(registration)) if registration else (baro, surname, name)
        self.last_result = rows
        for rec in rows:
            rec['bar_association_id'] = str(baro)
            rec['_origins'] = [json.dumps({'baro': baro, 'surname': surname, 'name': name}, ensure_ascii=False, sort_keys=True)]
            if registration:
                if rec.get('bar_registration_number') != str(registration):
                    raise ExtractionError('Exact registration search returned another identity')
                rec['_origins'] = [json.dumps({'baro':baro,'registration':str(registration)},sort_keys=True)]
            # Check observed substring semantics and bar identity as drift guard.
            if surname and label_key(surname) not in label_key(rec['last_name']):
                raise ExtractionError('Surname matching changed or unexpected result returned')
            if name and label_key(name) not in label_key(rec['first_name']):
                raise ExtractionError('Given-name matching changed or unexpected result returned')
        return rows, total, pages

    def fetch_registration(self, baro, registration):
        return self.fetch(str(baro), '', '', str(registration))

    def detail(self, rec, query):
        if self.last_query != query or not self.page.locator('button[name="detay"]').count():
            self.fetch(*query)
        # Locate by official registration + displayed bar, never stale row index.
        matches = []
        for item in self.last_result or []:
            if item.get('bar_registration_number') == rec.get('bar_registration_number') and turkish_upper(item.get('bar_association')) == turkish_upper(rec.get('bar_association')):
                matches.append(item)
        if len(matches) != 1:
            raise ListingIdentityMissing([rec['bar_registration_number']])
        index = matches[0]['_detail_index']
        selector = f'button[name="detay"][value="{index}"]'
        LOG.info('Opening detail for registration %s', rec.get('bar_registration_number'))
        # Submit the genuine POST form in a temporary tab. Keeping the listing
        # document alive avoids re-searching and re-solving after ERR_CACHE_MISS.
        listing = self.page
        prior_marker = getattr(self, '_submitted_document', None)
        original_target = listing.evaluate("""selector => {
            const button = document.querySelector(selector);
            if (!button || !button.form) throw new Error('Detail submitter has no form');
            const original = button.getAttribute('formtarget');
            button.setAttribute('formtarget', '_blank');
            return original;
        }""", selector)
        popup = None
        try:
            with listing.expect_popup(timeout=self.args.navigation_timeout * 1000) as opened:
                self.click_control(selector)
            popup = opened.value
            self.page = popup
            self._submitted_document = None
            # The popup event can precede its POST response. Do not mistake its
            # initial blank document for a Cloudflare challenge.
            deadline = time.monotonic() + self.args.navigation_timeout
            while time.monotonic() < deadline:
                try:
                    ready = popup.evaluate("() => location.href !== 'about:blank' && !!document.body && document.readyState !== 'loading'")
                    if ready:
                        break
                except Exception as error:
                    if session_was_closed(error):
                        raise SessionExpired('Browser closed while opening detail') from None
                    if not navigation_in_progress(error):
                        raise
                popup.wait_for_timeout(250)
            else:
                raise ExtractionError('Detail POST did not load before timeout')
            self.wait_for_view('detail')
            updated = parse_detail(popup.content(), rec)
            if self.on_detail_extracted:
                self.on_detail_extracted(updated)
            LOG.info('Detail extracted; listing preserved for registration %s', rec.get('bar_registration_number'))
            return updated
        finally:
            self.page = listing
            self._submitted_document = prior_marker
            if popup is not None:
                try:
                    popup.close()
                except Exception:
                    pass  # A saved detail remains durable if the session expires.
            try:
                listing.evaluate("""({selector, original}) => {
                    const button = document.querySelector(selector);
                    if (!button) return;
                    if (original === null) button.removeAttribute('formtarget');
                    else button.setAttribute('formtarget', original);
                }""", {'selector': selector, 'original': original_target})
            except Exception:
                self.last_query = None

    def details(self, records, query):
        """Overlap up to two observed form POSTs inside the verified browser."""
        if not records:
            return []
        if len(records) > 2 or len({r['bar_registration_number'] for r in records}) != len(records):
            raise ExtractionError('A batch must contain at most two distinct detail identities')
        if self.last_query != query or not self.page.locator('button[name="detay"]').count():
            self.fetch(*query)
        requests = []
        missing = []
        pending = {r['bar_registration_number']: r for r in records}
        for record in records:
            matches = [row for row in self.last_result
                       if row['bar_registration_number'] == record['bar_registration_number']
                       and turkish_upper(row['bar_association']) == turkish_upper(record['bar_association'])]
            if len(matches) != 1:
                missing.append(record['bar_registration_number'])
                continue
            requests.append({'reg': record['bar_registration_number'],
                             'selector': f'button[name="detay"][value="{matches[0]["_detail_index"]}"]'})
        if missing:
            raise ListingIdentityMissing(missing)
        batch_id = uuid.uuid4().hex
        completed, parse_errors, network_errors = {}, {}, {}
        self.needs_session_renewal = False
        try:
            # Submit the site's current form fields and selected submitter.
            # Cookies, proxy route and user agent stay in this browser session.
            # Only response HTML is read: profile images/scripts are not loaded.
            self.page.evaluate('''({id,requests,timeout}) => {
                if (window.__tbbDetailBatch) throw Error('Previous detail batch was not released');
                const state = window.__tbbDetailBatch = {id,ready:[],reports:[],controllers:[]};
                const jobs = requests.map(item => {
                    const button = document.querySelector(item.selector);
                    if (!button || !button.form || button.disabled) throw Error('Detail submitter is absent');
                    const form = button.form;
                    if (!form.noValidate && !button.formNoValidate && !form.checkValidity()) throw Error('Detail form is invalid');
                    const method = (button.getAttribute('formmethod') || form.method || 'GET').toUpperCase();
                    const action = new URL(button.hasAttribute('formaction') ? button.formAction : form.action, document.baseURI);
                    if (method !== 'POST' || action.origin !== location.origin) throw Error('Unexpected detail form method/origin');
                    const data = new FormData(form, button);
                    const encoding = button.getAttribute('formenctype') || form.enctype;
                    let body = data;
                    if (encoding === 'application/x-www-form-urlencoded') {
                        body = new URLSearchParams();
                        for (const [key,value] of data) {
                            if (typeof value !== 'string') throw Error('Unexpected file in detail form');
                            body.append(key,value);
                        }
                    } else if (encoding !== 'multipart/form-data') throw Error('Unsupported detail form encoding');
                    return {...item,action:action.href,body};
                });
                const originalURL=location.href;
                const runJob=async job => {
                    const started=performance.now(), deadline=started+timeout;
                    for (let attempt=1;attempt<=2;attempt++) {
                        const controller=new AbortController();state.controllers.push(controller);
                        const timer=setTimeout(()=>controller.abort(),Math.max(1,deadline-performance.now()));
                        try {
                            const response=await fetch(job.action,{method:'POST',body:job.body,credentials:'same-origin',signal:controller.signal});
                            const html=await response.text();
                            if (window.__tbbDetailBatch===state) state.ready.push({reg:job.reg,status:response.status,html});
                            return;
                        } catch(error) {
                            if (window.__tbbDetailBatch!==state) return;
                            const button=document.querySelector(job.selector);
                            const healthy=location.href===originalURL && !!button?.isConnected && !!button.form && navigator.onLine;
                            const name=error.name || 'NetworkError';
                            const retry=attempt===1 && healthy && ['TypeError','NetworkError'].includes(name) && deadline-performance.now()>500;
                            state.reports.push({reg:job.reg,error:name,attempt,online:navigator.onLine,listingHealthy:healthy,
                                sameSessionRetry:retry,elapsedMs:Math.round(performance.now()-started),host:new URL(job.action).hostname,path:new URL(job.action).pathname});
                            if (!retry) {state.ready.push({reg:job.reg,error:name,attempts:attempt});return;}
                            await new Promise(resolve=>setTimeout(resolve,250));
                            if (window.__tbbDetailBatch!==state) return;
                        } finally {clearTimeout(timer);}
                    }
                };
                jobs.forEach(job=>{void runJob(job);});
            }''', {'id': batch_id, 'requests': requests, 'timeout': self.args.navigation_timeout*1000})
            deadline = time.monotonic() + self.args.navigation_timeout + 2
            while pending and time.monotonic() < deadline:
                self.page.wait_for_timeout(100)
                response = self.page.evaluate('''id => {
                    const state = window.__tbbDetailBatch;
                    return !state || state.id !== id ? null : {ready:state.ready.splice(0),reports:state.reports.splice(0)};
                }''', batch_id)
                if response is None:
                    raise SessionExpired('Listing document changed during detail requests')
                for info in response['reports']:
                    info['recent_request_failures']=[e for e in self.page_events[-10:] if e.get('type')=='requestfailed'][-3:]
                    LOG.warning('Detail request network failure: %s', redact(json.dumps(info,ensure_ascii=False)))
                for item in response['ready']:
                    reg = item['reg']
                    if reg not in pending:
                        raise ExtractionError('Unexpected or repeated detail response')
                    if item.get('error'):
                        pending.pop(reg)
                        network_errors[reg]=f"{item['error']} after {item['attempts']} attempt(s)"
                        continue
                    html = item['html']
                    soup = BeautifulSoup(html, 'html.parser')
                    form = soup.select_one('#avForm')
                    if item['status'] in (403,429,503) or (form is None and re.search(r'cloudflare|just a moment|bir dakika', html, re.I)):
                        raise VerificationRequired('Detail POST returned a verification/availability response; completed records retained')
                    if item['status'] != 200 or form is None:
                        raise ExtractionError('Detail POST did not return the expected profile form')
                    record = pending.pop(reg)
                    try:
                        updated = parse_detail(str(form), record)
                    except ExtractionError as error:
                        # Drain the other response and persist it before the
                        # bounded same-session retry of this failed profile.
                        parse_errors[reg] = str(error)
                        continue
                    if self.on_detail_extracted:
                        self.on_detail_extracted(updated)
                    completed[reg] = updated
                    LOG.info('Detail extracted; listing preserved for registration %s', reg)
            if pending:
                raise SessionExpired('Detail response timeout; completed records retained')
            if network_errors:
                raise SessionExpired('Detail request failed after bounded same-session recovery: '+ '; '.join(
                    f'registration {reg}: {message}' for reg,message in network_errors.items()))
            if parse_errors:
                raise ExtractionError('Profile parsing failed: ' + '; '.join(
                    f'registration {reg}: {message}' for reg, message in parse_errors.items()))
            return [completed[row['bar_registration_number']] for row in records]
        except BaseException as error:
            # An invalid profile is not evidence that its browser expired.
            self.needs_session_renewal = not isinstance(error, ExtractionError)
            raise
        finally:
            try:
                self.page.evaluate('''id => {
                    const state=window.__tbbDetailBatch;
                    if (state && state.id === id) {
                        state.controllers.forEach(controller => controller.abort());
                        delete window.__tbbDetailBatch;
                    }
                }''', batch_id)
            except Exception:
                self.last_query = None

    def capture_failure(self, dest, label):
        dest.mkdir(parents=True, exist_ok=True)
        try:
            atomic_text(dest / (label + '.html'), redact(self.page.content()))
            info = self.page.evaluate('''() => ({url:location.href,title:document.title,
                readyState:document.readyState,hasTurnstile:!!window.turnstile,
                capturedWidgets:window.__tbbTurnstile ? window.__tbbTurnstile.widgets.length : null,
                scripts:[...document.scripts].map(s=>s.src).filter(Boolean),
                iframes:[...document.querySelectorAll('iframe')].map(f=>f.src),
                widgetAttributes:[...document.querySelectorAll('.cf-turnstile,[data-sitekey]')].map(e=>({sitekey:e.dataset.sitekey,action:e.dataset.action})),
                responseFields:[...document.querySelectorAll('input,textarea')].filter(e=>/turnstile|captcha/.test(e.name)).map(e=>({name:e.name,hasValue:!!e.value}))})''')
            info['events'] = self.page_events[-50:]
            atomic_text(dest / (label + '.json'), redact(json.dumps(info, ensure_ascii=False, indent=2)))
            atomic_text(dest / (label + '.txt'), self.page.locator('body').inner_text()[:20000])
            self.page.screenshot(path=str(dest / (label + '.png')), full_page=True)
        except Exception:
            pass


def retry(operation, args, on_retry=None):
    for attempt in range(args.retries + 1):
        try:
            return operation()
        except (VerificationRequired, SessionExpired, ListingIdentityMissing, KeyboardInterrupt):
            raise
        except Exception as e:
            if recoverable_browser_error(e):
                raise SessionExpired('Browser session closed during operation') from None
            if attempt == args.retries:
                raise
            if on_retry:
                on_retry(attempt, str(e))
            delay = min(args.max_backoff, args.retry_backoff * 2**attempt)
            LOG.warning('Retry %d/%d in %.1fs: %s', attempt+1, args.retries, delay, e)
            time.sleep(delay)


def export_summary(db, dest):
    report = db.export(dest)
    LOG.info('Saved %d unique lawyers; query states=%s; detail states=%s', report['unique_lawyers'], report['query_states'], report['details'])
    return report


def redirect_missing_detail(db, key, query, query_budget=250000):
    """Queue a narrower search; names select candidates, IDs still verify them."""
    record = db.record(key)
    surname = clean(record.get('last_name'))
    name = clean(record.get('first_name'))
    surname = surname if len(surname) >= 2 else ''
    name = name if len(name) >= 2 else ''
    target = (str(record.get('bar_association_id') or query[0]), surname, name)
    if len(query)==4 or (not surname and not name) or target == tuple(query):
        if len(query)==4 or record.get('_lookup_registration'):
            db.detail_state(key, 'needs_review', 'Official identity absent from exact-registration lookup')
            db.event('detail_exact_lookup_not_found',key)
        else:
            record['_lookup_registration']=record['bar_registration_number'];db.upsert(record)
            db.detail_state(key,'pending','Queued bounded exact-registration recovery')
            db.event('detail_exact_lookup_queued',key)
        return
    try:
        qid = db.put_query(*target, budget=query_budget)
    except ExtractionError:
        db.detail_state(key, 'needs_review', 'Query budget prevents narrower identity lookup')
        db.event('detail_lookup_needs_review', key)
        return
    db.db.execute('UPDATE details SET query_id=? WHERE key=?', (qid, key))
    db.db.commit()
    db.detail_state(key, 'pending', f'Identity lookup deferred to narrower query {qid}')
    db.event('detail_lookup_redirected', f'{key}: query {qid}')


def process_details(driver, db, q, args, dest):
    name_query = (q['baro'], q['surname'], q['name'])
    width = getattr(args, 'detail_concurrency', 1)
    jobs = db.detail_jobs(q['id'])
    batches=[]
    for job in jobs:
        exact=db.record(job['key']).get('_lookup_registration')
        if exact:
            batches.append(([job],(q['baro'],'','',str(exact))))
        elif batches and batches[-1][1]==name_query and len(batches[-1][0])<width:
            batches[-1][0].append(job)
        else:
            batches.append(([job],name_query))
    for candidates,query in batches:
        budget = len(jobs) if args.max_details is None else args.max_details-driver.details_attempted
        if budget <= 0:return
        candidates=candidates[:budget]
        if len(query)==4:
            allowed=[]
            for job in candidates:
                counter='detail_exact_attempts:'+job['key'];attempts=db.metadata(counter) or 0
                if attempts>=3:db.detail_state(job['key'],'needs_review','Exact-registration recovery allowance exhausted')
                else:db.metadata(counter,attempts+1);allowed.append(job)
            candidates=allowed
            if not candidates:continue
        batch = candidates[:budget]
        driver.details_attempted += len(batch)
        pending = {job['key']: job for job in batch}
        for key in pending:
            db.detail_state(key, 'running')
        def save(updated):
            key = record_key(updated)
            if key not in pending:
                raise ExtractionError('Completed detail does not belong to its batch')
            db.complete_detail(updated)
            pending.pop(key)
            if updated.get('_invalid_contact_values'):
                LOG.warning('Registration %s has invalid source contact fields %s; raw values retained in JSON audit',
                            updated.get('bar_registration_number'), ','.join(updated['_invalid_contact_values']))
        driver.on_detail_extracted = save
        def extract_remaining():
            records = [db.record(key) for key in pending]
            if not records:
                return
            try:
                if width == 1:
                    updated = driver.detail(records[0], query)
                    if pending:
                        save(updated)
                else:
                    updated_records = driver.details(records, query)
                    for updated in updated_records:
                        if record_key(updated) in pending:
                            save(updated)
            except ListingIdentityMissing as error:
                missing = [key for key in pending if db.record(key)['bar_registration_number'] in error.registrations]
                if not missing:
                    raise ExtractionError('Missing-identity error did not identify a pending job') from error
                for key in missing:
                    redirect_missing_detail(db, key, query, getattr(args, 'max_queries', 250000))
                    pending.pop(key)
                # A valid sibling was never submitted; process it now rather
                # than incorrectly failing both records or retrying stale data.
                return extract_remaining()
            except DetailRequestDeferred as error:
                # A good sibling and live original form establish a request-
                # specific failure. Do not repeatedly poison otherwise good
                # batches or pretend the entire browser has expired.
                if not pending or {db.record(k)['bar_registration_number'] for k in pending}!=error.registrations:
                    raise ExtractionError('Deferred request did not identify remaining batch jobs') from error
                for key in list(pending):
                    record=db.record(key)
                    record['_lookup_registration']=record['bar_registration_number']
                    record['_individual_transport_deferrals']=(record.get('_individual_transport_deferrals') or 0)+1
                    db.upsert(record)
                    db.detail_state(key,'pending','Individual request interrupted; queued bounded exact-registration recovery')
                    db.event('detail_transport_deferred',key)
                    pending.pop(key)
                return
            except VerificationRequired:
                if pending and getattr(driver, 'supports_form_recovery', False) is True and driver.recover_form(query):
                    return extract_remaining()
                raise
            except Exception as error:
                LOG.warning('Detail batch interrupted: %s', redact(str(error)))
                if getattr(driver, 'needs_session_renewal', False):
                    raise SessionExpired('Interrupted detail batch; saved records retained, renewing session') from error
                raise
        try:
            retry(extract_remaining, args)
        except VerificationRequired as error:
            for key in pending:
                db.detail_state(key, 'verification', str(error))
            raise
        except KeyboardInterrupt:
            for key in pending:
                db.db.execute("UPDATE details SET status='pending',error=? WHERE key=? AND status='running'",
                              ('Detail interrupted by stop/time limit; safe to resume',key))
            db.db.commit()
            raise
        except Exception as error:
            if recoverable_browser_error(error):
                for key in pending:
                    db.detail_state(key, 'pending', str(error))
                raise SessionExpired(str(error)) from error
            for key in pending:
                record = db.record(key)
                record['detail_status'] = 'failed'
                record['_detail_error'] = str(error)
                db.upsert(record)
                state = db.detail_state(key, 'failed', str(error), getattr(args, 'max_detail_failures', 3))
                if state == 'needs_review':
                    record['detail_status'] = 'needs_review'
                    db.upsert(record)
                    LOG.warning('Profile %s needs review after repeated extraction failures; automatic retries stopped', record.get('bar_registration_number'))
                db.event('detail_failed', f'{key}: {error}')
            if args.fail_fast:
                raise
        time.sleep(random.uniform(args.min_delay, args.max_delay))
        done = db.db.execute("SELECT count(*) FROM details WHERE status='done'").fetchone()[0]
        if done % args.export_every < len(batch):
            export_summary(db, dest)


def close_dedicated_browser(browser):
    """Ask the owned remote Chromium to terminate before disconnecting CDP."""
    try:
        browser.new_browser_cdp_session().send('Browser.close')
    except Exception as error:
        # A successful remote close may drop the connection before its reply.
        LOG.debug('Dedicated remote close request ended: %s', redact(str(error)))
    finally:
        try:
            browser.close()
        except Exception:
            pass


def cached_work_status(db,args):
    """No browser needed for a known seed plan with no runnable saved work.

    Unknown bars/seeds still require normal discovery. Inspection and bar
    refresh explicitly use the website. Failed/review jobs require their
    existing explicit retry options; no paid session is bought just to find
    the same non-runnable queue again.
    """
    if args.inspect or args.list_baros:return None
    bars=list(db.db.execute('SELECT id,label FROM bars'))
    if not bars:return None
    if args.all_baros:
        selected={r['id'] for r in bars}
    else:
        selected=set()
        for requested in args.baro or []:
            matches=[r['id'] for r in bars if r['id']==requested or turkish_upper(r['label'])==turkish_upper(requested)]
            if len(matches)!=1:return None
            selected.add(matches[0])
    if not selected:return None
    seeds=[turkish_upper(p) for p in args.prefix] if args.prefix else prefix_pairs(args.alphabet)
    for bar in selected:
        for seed in seeds:
            for surname,name in seed_filters(seed,args.primary_field):
                if not db.db.execute('SELECT 1 FROM queries WHERE baro=? AND surname=? AND name=?',(bar,surname,name)).fetchone():return None
        if db.db.execute("SELECT 1 FROM queries WHERE baro=? AND status IN ('pending','running','verification')",(bar,)).fetchone():return None
        if not args.no_details and db.db.execute("SELECT 1 FROM details d JOIN queries q ON q.id=d.query_id WHERE q.baro=? AND d.status IN ('pending','running','verification')",(bar,)).fetchone():return None
    report=db.export(Path(args.output))
    if not args.no_details and report['details'].get('needs_review'):return 'review_required',2
    if not args.no_details and any(report['details'].get(k) for k in ('failed','pending','running','verification')):return 'detail_budget_paused',2
    if any(report['query_states'].get(k) for k in ('failed','pending','running','verification')):return 'search_budget_paused',2
    if report['potential_partition_gaps'] or report['capped_queries'] or report['query_states'].get('unresolved') or report['roster_candidates_unresolved']:return 'coverage_unresolved',2
    return 'queue_finished',0


def run(args):
    started=time.monotonic()
    dest = Path(args.output).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    # A portable advisory process lock; one process per checkpoint/profile.
    lock = (dest / 'run.lock').open('a+')
    if os.name == 'nt':
        import msvcrt
        lock.seek(0); lock.write('0'); lock.flush(); lock.seek(0)
        try: msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError: raise RuntimeError('Another scraper owns this output directory')
    else:
        import fcntl
        try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Another scraper owns this output directory')
    db = Database(dest / 'checkpoint.sqlite3')
    if getattr(args, 'capsolver', False):
        args._solver = CapSolver(args.capsolver_key, Path(args.solver_ledger) if getattr(args, 'solver_ledger', '') else dest / 'solver_usage.json',
                                args.max_captcha_tasks, args.solver_timeout)
    db.recover(args.retry_failed, getattr(args, 'retry_review', False))
    file_log = logging.FileHandler(dest / 'progress.log', encoding='utf-8')
    file_log.addFilter(SecretFilter())
    file_log.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    LOG.addHandler(file_log)
    from playwright.sync_api import sync_playwright
    cfg = Config()
    if args.trainees:
        cfg.search = 'button[name="tip"][value="Stajyer"]'
    config = {'schema_version': 2, 'url': args.url, 'matching': 'substring',
              'primary_field': args.primary_field, 'alphabet': args.alphabet, 'trainees': args.trainees,
              'result_cap': args.result_cap, 'max_length': args.max_prefix_length}
    if getattr(args,'roster_only',False):config['lookup_mode']='roster_only'
    before = db.metadata('run_configuration')
    if before and before != config:
        raise RuntimeError('Checkpoint configuration differs. Use another output directory.')
    db.metadata('run_configuration', config)
    db.metadata('run_status', 'running')
    if args.population_file:
        baseline = json.loads(Path(args.population_file).read_text(encoding='utf-8'))
        if not baseline.get('as_of') or not baseline.get('source_url') or not baseline.get('definition') or not isinstance(baseline.get('bars'), list):
            raise ValueError('Population baseline needs as_of, source_url, definition, and bars')
        db.metadata('population_baseline', baseline)
    ctx, page, attached, pw, browser = None, None, False, None, None
    try:
        if args.resume_details_only and not db.db.execute("SELECT 1 FROM details WHERE status='pending' LIMIT 1").fetchone():
            review = db.db.execute("SELECT 1 FROM details WHERE status='needs_review' LIMIT 1").fetchone()
            incomplete = db.db.execute("SELECT 1 FROM details WHERE status!='done' LIMIT 1").fetchone()
            db.metadata('run_status', 'review_required' if review else 'detail_budget_paused' if incomplete else 'detail_queue_finished')
            LOG.info('No automatically retryable detail work; no browser session opened')
            return 2 if incomplete else 0
        cached = cached_work_status(db,args) if not args.resume_details_only and not getattr(args,'max_roster_lookups',0) else None
        if cached:
            db.metadata('run_status', cached[0])
            db.event('paid_session_skipped', cached[0])
            LOG.info('Known seed plan has no automatically runnable work; no browser session opened')
            return cached[1]
        if getattr(args, 'provider_credit_cap', None) is not None:
            from provider_budget import check_zenrows_cap
            check_zenrows_cap(args.cdp_endpoint, args.provider_credit_cap)
        pw = sync_playwright().start()
        if args.cdp_endpoint:
            LOG.info('Connecting to hosted browser')
            browser = pw.chromium.connect_over_cdp(args.cdp_endpoint, timeout=30000)
            attached = True
            ctx = browser.contexts[0] if browser.contexts else browser.new_context(locale='tr-TR')
            page = ctx.new_page()
        else:
            ctx = pw.chromium.launch_persistent_context(str(dest / 'browser_profile'),
                  headless=args.headless, locale='tr-TR', viewport={'width':1350,'height':900},
                  executable_path=args.browser_executable or None)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(15000)
        page.set_default_navigation_timeout(args.navigation_timeout*1000)
        LOG.info('Browser connected; loading directory')
        mode = getattr(args, 'search_mode', 'retained')
        if mode == 'retained':
            from retained_transport import browser_class
            driver = browser_class(sys.modules[__name__])(page, cfg, args)
            previous_stats = db.metadata('transport_statistics') or {}
            def transport_event(kind, message):
                db.metadata('transport_statistics', {k:previous_stats.get(k,0)+v for k,v in driver.stats.items()})
                db.event(kind, message)
            driver.on_transport_event = transport_event
        else:
            driver = DirectoryBrowser(page, cfg, args)
        db.metadata('transport_mode', mode)
        db.event('transport_selected', mode)
        driver.navigate(args.url)
        LOG.info('Directory loaded; checking search form')
        driver.form()
        if args.inspect:
            driver.inspect(dest / 'diagnostics')
            return 0
        options = [x for x in driver.baro_options() if x['value'] not in ('', '0', '-1') and x['label'] and not x['disabled']]
        atomic_text(dest / 'bar_associations.json', json.dumps(options, ensure_ascii=False, indent=2))
        if args.list_baros:
            for o in options: print(f'{o["value"]}\t{o["label"]}')
            return 0
        selected = set()
        if args.all_baros:
            selected = {o['value'] for o in options}
        else:
            for requested in args.baro or []:
                found = [o['value'] for o in options if o['value'] == requested or turkish_upper(o['label']) == turkish_upper(requested)]
                if len(found) != 1: raise ValueError(f'Unknown/ambiguous bar association: {requested!r}; use --list-baros')
                selected.add(found[0])
            if not selected: raise ValueError('Choose --baro or --all-baros')
        db.db.execute('UPDATE bars SET selected=0')
        for o in options:
            db.db.execute('INSERT INTO bars VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET label=excluded.label,selected=excluded.selected', (o['value'], o['label'], int(o['value'] in selected)))
        db.db.commit()
        if getattr(args,'max_roster_lookups',0):
            import roster_reconciliation as reconciliation
            reconciliation.t=sys.modules[__name__]
            if not hasattr(args,'_roster_budget'):
                args._roster_budget={'remaining':args.max_roster_lookups}
            def reserve_roster_lookup():
                args._roster_budget['remaining']-=1
            def roster_listing(qid):
                if not args.no_details:
                    row=db.db.execute('SELECT * FROM queries WHERE id=?',(qid,)).fetchone()
                    process_details(driver,db,dict(row),args,dest)
            receipt=reconciliation.verify_candidates(driver,db,selected,args._roster_budget['remaining'],
                        deadline=started+args.max_runtime if args.max_runtime else None,
                        on_listing=roster_listing,on_reserve=reserve_roster_lookup)
            db.event('roster_exact_lookups',json.dumps(receipt,sort_keys=True))
        seeds = ([] if getattr(args,'roster_only',False) else
                 [turkish_upper(p) for p in args.prefix] if args.prefix else prefix_pairs(args.alphabet))
        history = db.metadata('seed_plan_history') or []
        plan = {'bars': sorted(selected), 'explicit_substrings': seeds if args.prefix else None, 'all_alphabet_pairs': not bool(args.prefix), 'primary_field':args.primary_field}
        if plan not in history and not getattr(args,'roster_only',False):
            db.metadata('seed_plan_history', history + [plan])
        if not args.resume_details_only:
            for bar in sorted(selected):
                for seed in seeds:
                    for surname,name in seed_filters(seed,args.primary_field):
                        db.put_query(bar, surname, name, budget=args.max_queries)
        # Resume detail jobs even when discovery queries already finished.
        if not args.no_details:
            qs = db.db.execute("SELECT DISTINCT q.* FROM queries q JOIN details d ON q.id=d.query_id JOIN bars b ON b.id=q.baro WHERE d.status='pending' AND b.selected=1 AND q.status IN ('done','split','unresolved','pending') ORDER BY q.id").fetchall()
            for q in qs:
                process_details(driver, db, dict(q), args, dest)
        processed = 0
        while not args.resume_details_only and not getattr(args,'roster_only',False) and (args.max_searches is None or processed < args.max_searches):
            if not args.no_details and args.max_details is not None and driver.details_attempted >= args.max_details:
                LOG.info('Detail budget reached; leaving unused searches queued without submitting them')
                break
            q = db.take_query()
            if not q: break
            LOG.info('Query %d bar=%s surname=%s name=%s', q['id'], q['baro'], q['surname'] or '-', q['name'] or '-')
            try:
                def note_retry(attempt, error):
                    db.db.execute('UPDATE queries SET attempts=attempts+1 WHERE id=?', (q['id'],))
                    db.event('query_retry', f'{q["id"]}: {error}')
                rows, total, pages = retry(lambda: driver.fetch(q['baro'], q['surname'], q['name']), args, note_retry)
                for i, rec in enumerate(rows):
                    db.upsert(rec, q['id'], 1, i)
                capped = total >= args.result_cap or len(rows) >= args.result_cap
                db.finish(q['id'], 'unresolved' if capped else 'done', seen=len(rows), total_hint=total, pages=pages, capped=int(capped))
                status = 'done'
                if capped:
                    children, gap = partition(q['surname'], q['name'], args.max_prefix_length, args.alphabet)
                    db.db.execute('INSERT OR REPLACE INTO gaps VALUES(?,?)', (q['id'], gap))
                    db.db.commit()
                    status = 'split' if children else 'unresolved'
                    for s, n in children:
                        db.put_query(q['baro'], s, n, q['id'], args.max_queries)
                db.finish(q['id'], status, seen=len(rows), total_hint=total, pages=pages, capped=int(capped))
                if not args.no_details:
                    process_details(driver, db, q, args, dest)
            except VerificationRequired as e:
                db.finish(q['id'], 'verification', error=str(e))
                db.metadata('run_status', 'access_blocked')
                db.event('verification_required', str(e))
                LOG.warning('%s', e)
                return 2
            except (KeyboardInterrupt, SessionExpired):
                raise
            except Exception as e:
                if session_was_closed(e):
                    db.finish(q['id'], 'pending', error=str(e))
                    raise SessionExpired(str(e)) from e
                db.finish(q['id'], 'failed', error=str(e))
                db.event('query_failed', f'{q["id"]}: {e}')
                LOG.error('Query %d failed: %s', q['id'], e)
                if args.capture_failures: driver.capture_failure(dest / 'diagnostics', f'query_{q["id"]}')
                if args.fail_fast: raise
            finally:
                processed += 1
                if processed % args.export_every == 0: export_summary(db, dest)
            time.sleep(random.uniform(args.min_delay, args.max_delay))
        report = export_summary(db, dest)
        incomplete = any(report['query_states'].get(s,0) for s in ('failed','pending','running','verification','unresolved'))
        details_incomplete = not args.no_details and any(report['details'].get(s,0) for s in ('failed','pending','running','verification','needs_review'))
        coverage_unresolved = bool(report['potential_partition_gaps'] or report['capped_queries'] or report['roster_candidates_unresolved'])
        if getattr(args,'roster_only',False):
            import roster_reconciliation as reconciliation
            work=reconciliation.lookup_status(db,selected)
            db.metadata('roster_audit_work',work)
            status='roster_budget_paused' if work['ready'] else 'review_required' if work['exhausted'] or details_incomplete else 'roster_audit_finished'
            db.metadata('run_status',status)
            return 2 if status!='roster_audit_finished' else 0
        if args.resume_details_only:
            db.metadata('run_status', 'detail_budget_paused' if details_incomplete else 'detail_queue_finished')
            return 2 if details_incomplete else 0
        status = ('detail_budget_paused' if details_incomplete else 'search_budget_paused' if incomplete
                  else 'coverage_unresolved' if coverage_unresolved else 'queue_finished')
        db.metadata('run_status', status)
        return 2 if incomplete or details_incomplete or coverage_unresolved else 0
    except SessionExpired as e:
        db.metadata('run_status', 'session_expired')
        db.event('session_expired', str(e))
        LOG.warning('Hosted browser session expired; unfinished jobs remain pending')
        return 2
    except VerificationRequired as e:
        db.metadata('run_status', 'access_blocked')
        db.event('verification_required', str(e))
        if args.capture_failures and page:
            driver.capture_failure(dest / 'diagnostics', 'access_blocked')
        LOG.warning('%s', e)
        return 2
    except RuntimeBudgetExceeded:
        db.metadata('run_status', 'runtime_limit')
        LOG.warning('Runtime budget exhausted; checkpoint preserved')
        return 2
    except KeyboardInterrupt:
        db.metadata('run_status', 'interrupted')
        raise
    except Exception as error:
        if recoverable_browser_error(error):
            db.metadata('run_status', 'session_expired')
            db.event('session_expired', type(error).__name__ + ': ' + str(error))
            LOG.warning('Browser transport/document changed; unfinished work retained for bounded reconnection')
            return 2
        db.metadata('run_status', 'failed')
        if args.capture_failures and page and 'driver' in locals():
            driver.capture_failure(dest / 'diagnostics', 'fatal')
        raise
    finally:
        # Do not let a phase deadline interrupt its own checkpoint/export/CDP
        # cleanup. Restore only the unspent outer CLI allowance afterwards.
        cleanup_started=time.monotonic();cleanup_alarm,_=signal.getitimer(signal.ITIMER_REAL)
        if cleanup_alarm:signal.setitimer(signal.ITIMER_REAL,0)
        requeued=db.db.execute("UPDATE details SET status='pending' WHERE status='running'").rowcount
        if requeued:
            db.db.commit();db.event('interrupted_details_requeued',str(requeued))
        if 'driver' in locals() and getattr(driver, 'on_transport_event', None):
            driver.on_transport_event('transport_checkpoint', 'Connection ending; counters retained')
        if 'driver' in locals() and isinstance(getattr(driver,'startup_stats',None),dict):
            prior=db.metadata('startup_statistics') or {}
            db.metadata('startup_statistics',{k:prior.get(k,0)+v for k,v in driver.startup_stats.items()})
            db.event('startup_checkpoint',json.dumps(driver.startup_stats,sort_keys=True))
        if getattr(args, '_solver', None):
            db.metadata('solver_usage', {'task_creations_reserved': args._solver.state['attempts'],
                'task_limit': args.max_captcha_tasks, 'pending_task': bool(args._solver.state.get('pending')),
                'note':'Task count, not verified currency spend. Includes uncertain create requests.'})
        export_summary(db, dest)
        db.db.close()
        # Closing our tab leaves the user's attached browser and other tabs alone.
        try:
            if attached and args.close_cdp_browser and browser: close_dedicated_browser(browser)
            elif attached and page: page.close()
            elif ctx: ctx.close()
        except Exception: pass
        if pw:
            try: pw.stop()
            except Exception: pass
        LOG.removeHandler(file_log)
        file_log.close()
        lock.close()
        if cleanup_alarm:signal.setitimer(signal.ITIMER_REAL,max(.05,cleanup_alarm-(time.monotonic()-cleanup_started)))


def cli(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', default=URL)
    p.add_argument('--output', default='turkey_output')
    p.add_argument('--baro', action='append')
    p.add_argument('--all-baros', action='store_true')
    p.add_argument('--list-baros', action='store_true')
    p.add_argument('--inspect', action='store_true')
    p.add_argument('--primary-field', choices=['surname','given','both'], default='surname',
                   help='Use both for coverage discovery: given-name seeds also find short/nonstandard surnames; adds searches')
    p.add_argument('--prefix', action='append', default=[], help='Explicit substring seeds; a partial pilot')
    p.add_argument('--alphabet', default=ALPHABET, help='Seed/split alphabet; can include foreign letters')
    p.add_argument('--trainees', action='store_true', help='Separate trainee-only output directory required')
    p.add_argument('--no-details', action='store_true', help='Listing-only; contact availability stays unknown')
    p.add_argument('--resume-details-only', action='store_true', help='Process saved profile jobs without starting new discovery queries')
    p.add_argument('--population-file', default=str(Path(__file__).with_name('population_2025.json')), help='Official dated population baseline JSON; empty string disables')
    p.add_argument('--headless', action='store_true', default=True)
    p.add_argument('--headed', action='store_false', dest='headless', help='Show the browser while keeping autonomous verification behavior')
    p.add_argument('--interactive', action='store_false', dest='unattended', default=True, help='Optional manual verification mode; default is unattended')
    p.add_argument('--session-restarts', type=int, default=2, help='Bounded reconnects after hosted browser expiry, respecting remaining job limits')
    p.add_argument('--access-retries', type=int, default=2, help='Additional automatic-verification runs after cooldown')
    p.add_argument('--access-cooldown', type=float, default=60)
    p.add_argument('--browser-executable', default='')
    p.add_argument('--cdp-endpoint', default=os.getenv('TBB_CDP_ENDPOINT',''))
    p.add_argument('--connection-file', default=os.getenv('TBB_CONNECTION_FILE',''), help='Private JSON file containing cdp_endpoint')
    p.add_argument('--provider-credit-cap', type=int, help='Verify this existing ZenRows billing-period key cap before opening a browser; never changes the provider cap')
    p.add_argument('--close-cdp-browser', action='store_true', help='Release a dedicated hosted browser session on exit; leave off for a shared personal browser')
    p.add_argument('--session-ttl', type=int, default=900, help='ZenRows lifetime in seconds (60..900); reconnects remain bounded')
    p.add_argument('--capsolver', action='store_true', help='Enable paid Turnstile solving; requires CAPSOLVER_API_KEY or private solver file')
    p.add_argument('--solver-file', default=os.getenv('TBB_SOLVER_FILE',''), help='Private JSON containing capsolver_api_key')
    p.add_argument('--solver-ledger', default='', help='Optional shared task ledger for serial jobs; preserves a global task budget')
    p.add_argument('--max-captcha-tasks', type=int, default=10, help='Maximum task creations across this output checkpoint, including interrupted attempts')
    p.add_argument('--solver-timeout', type=int, default=90)
    p.add_argument('--max-runtime', type=int, default=1800, help='Wall-clock ceiling in seconds for this invocation, including reconnects and cooldowns')
    p.add_argument('--max-searches', type=int)
    p.add_argument('--max-roster-lookups',type=int,default=0,
                   help='Additional bounded exact-registration lookups of missing imported roster IDs (0 disables)')
    p.add_argument('--roster-only',action='store_true',help='Check saved roster IDs only; preserve ordinary discovery queries without submitting or completing them')
    p.add_argument('--max-details', type=int, help='Per-run limit on detail jobs, including failures; leaves the remaining queue pending')
    p.add_argument('--max-queries', type=int, default=250000)
    p.add_argument('--result-cap', type=int, default=1000)
    p.add_argument('--max-prefix-length', type=int, default=5)
    p.add_argument('--retries', type=int, default=2)
    p.add_argument('--retry-backoff', type=float, default=2)
    p.add_argument('--max-backoff', type=float, default=30)
    p.add_argument('--retry-failed', action='store_true')
    p.add_argument('--retry-review', action='store_true', help='Explicitly release needs_review jobs for a new bounded attempt; keeps prior attempt history')
    p.add_argument('--max-detail-failures', type=int, default=3, help='Persistent extraction-failure ceiling per profile; access/session failures do not increment it')
    p.add_argument('--search-mode', choices=('retained','navigation'), default='retained', help='Retained compact POST transport (default), or legacy navigation rollback')
    p.add_argument('--form-refreshes', type=int, default=1, help='Maximum normal form reloads after rejected POSTs per browser connection')
    p.add_argument('--detail-concurrency', type=int, choices=(1,2), default=2, help='Concurrent native detail POSTs within one retained listing; default 2')
    p.add_argument('--widget-grace', type=float, default=5, help='Automatic grace for an observed form widget before paid solving; outer challenges retain their longer timeout')
    p.add_argument('--min-delay', type=float, default=0.5)
    p.add_argument('--max-delay', type=float, default=1)
    p.add_argument('--captcha-timeout', type=int, default=180)
    p.add_argument('--auto-verification-timeout', type=int, default=30)
    p.add_argument('--navigation-timeout', type=int, default=60)
    p.add_argument('--startup-timeout',type=int,default=120,
                   help='Per-navigation ceiling for a usable search form while hosted automatic verification runs; ordinary solver is used only after form readiness')
    p.add_argument('--export-every', type=int, default=50)
    p.add_argument('--fail-fast', action='store_true')
    p.add_argument('--capture-failures', action='store_true')
    p.add_argument('--verbose', action='store_true')
    args = p.parse_args(argv)
    if not 1<=args.startup_timeout<=600:
        p.error('--startup-timeout must be 1..600 seconds')
    if args.resume_details_only and args.no_details:
        p.error('--resume-details-only cannot be combined with --no-details')
    args.capsolver_key = os.getenv('CAPSOLVER_API_KEY','').strip()
    if args.solver_file:
        try:
            args.capsolver_key = json.loads(Path(args.solver_file).read_text())['capsolver_api_key']
        except (OSError, ValueError, KeyError):
            p.error('Cannot read solver file; expected private JSON containing capsolver_api_key')
    if args.capsolver and (not isinstance(args.capsolver_key, str) or not args.capsolver_key.strip()):
        p.error('--capsolver requires a CapSolver key')
    if args.capsolver and not args.unattended:
        p.error('--capsolver uses unattended mode; remove --interactive')
    if not 60 <= args.session_ttl <= 900 or args.session_ttl % 60 or args.max_captcha_tasks < 1 or args.solver_timeout < 1 or args.max_runtime < 1:
        p.error('Invalid session TTL or solver budget/timeout')
    if args.capsolver_key:
        SECRET_VALUES.append(args.capsolver_key)
    if args.connection_file and not args.cdp_endpoint:
        try:
            connection = json.loads(Path(args.connection_file).read_text(encoding='utf-8'))
            args.cdp_endpoint = connection['cdp_endpoint']
            if not isinstance(args.cdp_endpoint,str) or urlparse(args.cdp_endpoint).scheme not in ('ws','wss','http','https'):
                p.error('Connection file has an invalid cdp_endpoint')
        except (OSError,ValueError,KeyError):
            p.error('Cannot read connection file; expected private JSON containing cdp_endpoint')
    if args.cdp_endpoint:
        endpoint = urlparse(args.cdp_endpoint)
        if endpoint.hostname == 'browser.zenrows.com':
            parameters = dict(parse_qsl(endpoint.query))
            parameters['session_ttl'] = f'{args.session_ttl // 60}m'
            args.cdp_endpoint = urlunparse(endpoint._replace(query=urlencode(parameters)))
        SECRET_VALUES.append(args.cdp_endpoint)
        SECRET_VALUES.extend(v for k,v in parse_qsl(urlparse(args.cdp_endpoint).query) if any(x in k.lower() for x in ('key','token','password')))
    args.alphabet = ''.join(dict.fromkeys(turkish_upper(args.alphabet)))
    if not 0 <= args.max_roster_lookups <= 100 or (args.max_roster_lookups and args.resume_details_only):
        p.error('--max-roster-lookups must be 0..100 and cannot accompany --resume-details-only')
    if args.roster_only and (not args.max_roster_lookups or args.resume_details_only or args.all_baros or not args.baro):
        p.error('--roster-only requires --baro and --max-roster-lookups; cannot accompany all-bars/detail-only mode')
    if (args.form_refreshes < 0 or (args.provider_credit_cap is not None and args.provider_credit_cap < 1) or args.max_detail_failures < 1 or args.widget_grace < 0 or args.min_delay < 0 or args.max_delay < args.min_delay or args.retries < 0 or args.access_retries < 0 or args.session_restarts < 0 or args.access_cooldown < 1 or args.export_every < 1 or args.result_cap < 1 or args.max_prefix_length < 2 or args.max_queries < 1 or args.captcha_timeout < 1 or args.auto_verification_timeout < 1 or args.navigation_timeout < 1 or len(args.alphabet) < 2 or (args.max_searches is not None and args.max_searches < 1) or (args.max_details is not None and args.max_details < 1) or args.retry_backoff < 0 or args.max_backoff < 0):
        p.error('Invalid delay/budget/timeout/cap arguments')
    if any(len(clean(s)) < 2 for s in args.prefix): p.error('--prefix needs at least two characters')
    if args.url != URL and urlparse(args.url).scheme not in ('http','https'): p.error('--url must use HTTP(S)')
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    for handler in logging.getLogger().handlers:
        handler.addFilter(SecretFilter())
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    previous_alarm = signal.getsignal(signal.SIGALRM)
    def runtime_exhausted(signum, frame):
        raise RuntimeBudgetExceeded
    signal.signal(signal.SIGALRM, runtime_exhausted)
    signal.setitimer(signal.ITIMER_REAL, args.max_runtime)
    try:
        if args.provider_credit_cap is not None:
            from provider_budget import check_zenrows_cap
            receipt = check_zenrows_cap(args.cdp_endpoint, args.provider_credit_cap)
            LOG.info('Provider cap verified: %s credits remain of %s; cap unchanged', receipt['remaining_credits'], receipt['credits'])
        access_attempt = 0
        session_attempt = 0
        checkpoint = Path(args.output) / 'checkpoint.sqlite3'
        def totals():
            if not checkpoint.exists():
                return (0, 0)
            with sqlite3.connect(checkpoint) as state:
                queries = state.execute('SELECT coalesce(sum(attempts),0) FROM queries').fetchone()[0]
                details = state.execute('SELECT coalesce(sum(attempts),0) FROM details').fetchone()[0]
            return queries, details
        while True:
            before_queries, before_details = totals()
            result = run(args)
            after_queries, after_details = totals()
            with sqlite3.connect(checkpoint) as state:
                row = state.execute("SELECT value FROM metadata WHERE key='run_status'").fetchone()
            status = json.loads(row[0]) if row else None
            if args.max_searches is not None:
                args.max_searches = max(0, args.max_searches - (after_queries-before_queries))
            if args.max_details is not None:
                args.max_details = max(0, args.max_details - (after_details-before_details))
            if result != 2 or not args.unattended or getattr(args, '_solver_terminal', False):
                return result
            if not args.no_details and args.max_details == 0:
                LOG.info('Detail budget reached; not opening another browser session')
                return result
            if status == 'session_expired' and session_attempt < args.session_restarts:
                # Resume remaining details even when discovery's search budget
                # is exhausted; neither budget resets on reconnect.
                if args.max_details == 0 and args.max_searches == 0:
                    return result
                session_attempt += 1
                LOG.warning('Reconnecting hosted browser (%d/%d); checkpoint retained',session_attempt,args.session_restarts)
                continue
            if status == 'access_blocked' and access_attempt < args.access_retries:
                cooldown = args.access_cooldown * 2**access_attempt
                access_attempt += 1
                LOG.warning('Website access blocked; autonomous retry %d/%d after %.1fs cooldown', access_attempt, args.access_retries, cooldown)
                time.sleep(cooldown)
                continue
            return result
    except RuntimeBudgetExceeded:
        LOG.warning('Runtime budget exhausted; resume with the same output directory')
        return 2
    except KeyboardInterrupt:
        LOG.warning('Interrupted; checkpoint preserved. Repeat the command to resume.')
        return 130
    except Exception as e:
        LOG.error('Fatal: %s', e)
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_alarm)


if __name__ == '__main__':
    sys.exit(cli())

"""Bounded CapSolver Turnstile client. Never logs credentials or solved tokens."""
import hashlib
import json
import os
import re
from pathlib import Path
import time
from urllib.request import Request, urlopen


class SolverError(RuntimeError):
    pass


class SolverBudgetExceeded(SolverError):
    pass


def post_json(method, body, timeout):
    request = Request('https://api.capsolver.com/' + method,
                      data=json.dumps(body).encode(),
                      headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except Exception:
        # Provider responses / transport errors may contain submitted secrets.
        raise SolverError('CapSolver transport or response failure') from None


class CapSolver:
    def __init__(self, key, ledger, max_tasks=10, timeout=90,
                 transport=post_json, clock=time.monotonic, sleep=time.sleep):
        self.key, self.path = key, Path(ledger)
        self.max_tasks, self.timeout = max_tasks, timeout
        self.transport, self.clock, self.sleep = transport, clock, sleep
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {'attempts': 0}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(self.state, stream)
        os.replace(temp, self.path)

    def call(self, method, payload, deadline):
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise SolverError('CapSolver deadline exceeded')
        response = self.transport(method, {'clientKey': self.key, **payload}, min(20, remaining))
        if not isinstance(response, dict):
            raise SolverError('Malformed CapSolver response')
        if response.get('errorId') or response.get('status') == 'failed':
            # Restrict errors to a safe code, not arbitrary provider descriptions.
            code = str(response.get('errorCode') or 'TASK_FAILED')
            code = code if re.fullmatch(r'ERROR_[A-Z0-9_]{1,64}', code) and self.key not in code else 'TASK_FAILED'
            if method == 'getTaskResult':
                self.state.pop('pending', None)
                self.save()
            raise SolverError('CapSolver ' + code)
        return response

    def solve(self, widget):
        if not self.key:
            raise SolverError('CapSolver key missing')
        if not widget.get('sitekey') or not widget.get('url'):
            raise SolverError('Turnstile widget parameters unavailable')
        task = {'type': 'AntiTurnstileTaskProxyLess', 'websiteURL': widget['url'],
                'websiteKey': widget['sitekey']}
        metadata = {key: widget[key] for key in ('action', 'cdata') if widget.get(key)}
        if metadata:
            task['metadata'] = metadata
        signature = hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()
        deadline = self.clock() + self.timeout
        pending = self.state.get('pending', {})
        if pending.get('signature') == signature and pending.get('task_id'):
            task_id = pending['task_id']
        else:
            if self.state['attempts'] >= self.max_tasks:
                raise SolverBudgetExceeded('CapSolver task budget exhausted; checkpoint retained')
            # Reserve BEFORE the network call: a lost create response must not
            # cause unlimited duplicate charges after process/session restart.
            self.state['attempts'] += 1
            self.state.pop('pending', None)
            self.save()
            created = self.call('createTask', {'task': task}, deadline)
            task_id = created.get('taskId')
            if not task_id:
                raise SolverError('CapSolver returned no task ID')
            self.state['pending'] = {'signature': signature, 'task_id': task_id}
            self.save()
        while self.clock() < deadline:
            result = self.call('getTaskResult', {'taskId': task_id}, deadline)
            if result.get('status') == 'ready':
                token = result.get('solution', {}).get('token')
                if not isinstance(token, str) or not token:
                    self.state.pop('pending', None)
                    self.save()
                    raise SolverError('CapSolver returned an empty Turnstile solution')
                self.state.pop('pending', None)
                self.save()
                return token
            if result.get('status') not in ('processing', 'idle'):
                raise SolverError('Unexpected CapSolver task status')
            self.sleep(min(2, max(0, deadline - self.clock())))
        raise SolverError('CapSolver deadline exceeded; pending task retained')


# Instrument the real directory form after the managed challenge has cleared.
# Future explicit renders are captured; existing implicit widgets use DOM
# attributes. Keep callbacks in the page; only task inputs leave it.
CAPTURE_SCRIPT = r"""(() => {
    if (window.__tbbTurnstile) return;
    const state = window.__tbbTurnstile = {widgets: [], documentId: Math.random().toString(36)};
    const instrument = api => {
        if (!api || typeof api.render !== 'function' || api.render.__tbbWrapped) return;
        const original = api.render;
        function render(container, options) {
            const item = {container, options: options || {}};
            const id = original.apply(this, arguments);
            item.id = id; state.widgets.push(item);
            return id;
        }
        render.__tbbWrapped = true;
        api.render = render;
    };
    let current = window.turnstile;
    const descriptor = Object.getOwnPropertyDescriptor(window, 'turnstile');
    if (!descriptor || descriptor.configurable) {
        Object.defineProperty(window, 'turnstile', {configurable:true,
            get:()=>current, set:value=>{current=value; instrument(value);}});
    }
    instrument(current);
    const timer = setInterval(()=>instrument(window.turnstile), 50);
    addEventListener('pagehide',()=>clearInterval(timer),{once:true});
})();"""

DISCOVER_SCRIPT = r"""() => {
    const state = window.__tbbTurnstile;
    const captured = state ? state.widgets : [];
    const found = captured.map((item,index)=>({
        index, sitekey:item.options.sitekey, action:item.options.action,
        cdata:item.options.cData, responseField:item.options['response-field-name'] || 'cf-turnstile-response',
        callback:typeof item.options.callback === 'function' ? true : false
    }));
    for (const element of document.querySelectorAll('.cf-turnstile[data-sitekey]')) {
        if (found.some(item=>item.sitekey === element.dataset.sitekey)) continue;
        found.push({index:-1, sitekey:element.dataset.sitekey, action:element.dataset.action,
            cdata:element.dataset.cdata, callbackName:element.dataset.callback,
            responseField:element.dataset.responseFieldName || 'cf-turnstile-response'});
    }
    return found.filter(item=>item.sitekey).map(item=>({...item, url:location.href,
        documentId:state ? state.documentId : null}));
}"""

APPLY_SCRIPT = r"""({widget,token}) => {
    const state = window.__tbbTurnstile;
    if (location.href !== widget.url || !state || state.documentId !== widget.documentId)
        throw new Error('Turnstile document changed during solve');
    let callback = null;
    if (widget.index >= 0) {
        const item = state.widgets[widget.index];
        if (!item || item.options.sitekey !== widget.sitekey) throw new Error('Turnstile widget changed');
        callback = item.options.callback;
    } else if (widget.callbackName) {
        callback = window[widget.callbackName];
    }
    if (typeof callback === 'string') callback = window[callback];
    const fields = [...document.querySelectorAll('input,textarea')]
        .filter(element=>element.name === widget.responseField);
    if (!fields.length && widget.index === -1) {
        // If the widget's script failed to load, its hidden input may never
        // have been created. Attach the genuine solver response to the form
        // containing the observed sitekey, rather than to an arbitrary form.
        const containers = [...document.querySelectorAll('.cf-turnstile[data-sitekey]')]
            .filter(element=>element.dataset.sitekey === widget.sitekey);
        const form = containers.length === 1 ? containers[0].closest('form') : null;
        if (form) {
            const field = document.createElement('input');
            field.type = 'hidden'; field.name = widget.responseField;
            form.appendChild(field); fields.push(field);
        }
    }
    if (!fields.length && typeof callback !== 'function') throw new Error('No Turnstile response destination');
    for (const field of fields) {
        field.value = token;
        field.dispatchEvent(new Event('input',{bubbles:true}));
        field.dispatchEvent(new Event('change',{bubbles:true}));
    }
    if (typeof callback === 'function') callback(token);
    return true;
}"""

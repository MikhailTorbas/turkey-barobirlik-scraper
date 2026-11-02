"""Read-only ZenRows key-cap preflight; never creates or modifies caps."""
import json
from urllib.parse import parse_qsl, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError


class BudgetError(RuntimeError):
    pass


class ProviderAuthorizationError(BudgetError):
    """Non-transient authentication/permission/funding rejection."""
    pass


def validate_cap(payload, expected):
    caps = payload.get('api_key', {}).get('caps', [])
    matches = [c for c in caps if c.get('window') == 'billing_period'
               and c.get('credits') == expected]
    if len(matches) != 1:
        raise BudgetError('API key must already have the requested billing-period cap; no settings were changed')
    cap = matches[0]
    if not isinstance(cap.get('remaining_credits'), (int, float)) or cap['remaining_credits'] <= 0:
        raise BudgetError('Provider key cap is exhausted or remaining usage is unavailable')
    return {k: cap[k] for k in ('window','credits','used_credits','remaining_credits','resets_at') if k in cap}


def read_zenrows_account(endpoint, timeout=20):
    parsed = urlparse(endpoint)
    if parsed.scheme != 'wss' or parsed.hostname != 'browser.zenrows.com':
        raise ProviderAuthorizationError('Usage check requires the official secure ZenRows browser endpoint')
    params = dict(parse_qsl(parsed.query))
    key = params.get('apikey')
    if not key:
        raise ProviderAuthorizationError('ZenRows connection file has no API key for read-only usage validation')
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    request = Request('https://api.zenrows.com/v1/subscriptions/self/details',
                      headers={'X-API-Key': key, 'Accept': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code in (400,401,402,403):
            raise ProviderAuthorizationError('Provider account rejected usage authentication or funding (HTTP '+str(error.code)+')') from None
        raise BudgetError('Provider usage temporarily unreadable (HTTP '+str(error.code)+')') from None
    except Exception:
        raise BudgetError('Unable to verify provider cap; browser was not opened') from None
    if not isinstance(payload,dict):raise BudgetError('Malformed provider usage response')
    return payload


def check_zenrows_cap(endpoint, expected, timeout=20):
    payload=read_zenrows_account(endpoint,timeout)
    return validate_cap(payload, expected)


def read_zenrows_usage(endpoint, timeout=20):
    """Uncapped local mode: observe account-wide usage, never alter key caps."""
    payload=read_zenrows_account(endpoint,timeout)
    used=payload.get('usage_credits')
    if isinstance(used,bool) or not isinstance(used,(int,float)):
        raise BudgetError('Account usage counter unavailable')
    limit=payload.get('credit_limit')
    return {'mode':'uncapped','counter_scope':'account','used_credits':used,
            'account_credit_limit':limit,'provider_caps':payload.get('api_key',{}).get('caps',[]),
            'resets_at':payload.get('period_ends_at'),
            'note':'No local spending ceiling. Existing provider caps and account limits still apply.'}

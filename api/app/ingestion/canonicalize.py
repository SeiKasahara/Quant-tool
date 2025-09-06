from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from datetime import datetime
import re
import trafilatura
from bs4 import BeautifulSoup

TRACKING_PARAMS = ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','fbclid']

def canonicalize_url(url: str) -> str:
    try:
        p = urlparse(url)
        qs = dict(parse_qsl(p.query))
        qs = {k:v for k,v in qs.items() if k not in TRACKING_PARAMS}
        new_q = urlencode(qs)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, p.fragment))
    except Exception:
        return url

def extract_text(html: str) -> str:
    if not html:
        return ''
    text = trafilatura.extract(html) or ''
    if not text:
        # fallback to bs4
        soup = BeautifulSoup(html, 'html.parser')
        for s in soup(['script','style','header','footer','nav','aside']):
            s.decompose()
        text = soup.get_text(separator='\n')
    # basic cleanup
    text = re.sub(r'\n{2,}', '\n\n', text).strip()
    return text

def parse_date(value) -> str:
    if not value:
        return None
    if isinstance(value, str):
        try:
            # try iso
            return datetime.fromisoformat(value).astimezone().isoformat()
        except Exception:
            pass
    if isinstance(value, datetime):
        return value.astimezone().isoformat()
    return None

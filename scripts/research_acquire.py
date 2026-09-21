#!/usr/bin/env python3
"""Acquire public research sources. HTML: defuddle first; PDF: httpx/PyMuPDF.
No credentials, scripts from sources, alternate-origin bypass, or model calls.
Usage: research_acquire.py COLLECTION ID URL [pdf|html|json] [--name BASENAME]
The named receipt records failures as well as actual downloaded bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
import httpx
import pymupdf
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def acquire(collection: str, sid: str, url: str, kind: str = 'html', name: str = 'source') -> dict:
    if collection not in {'B', 'D', 'E', 'F'} or not sid.replace('-', '').isalnum() or not name.replace('-', '').isalnum():
        raise ValueError('Out-of-scope collection, ID or name')
    out = ROOT / 'corpus' / 'raw' / collection / sid
    out.mkdir(parents=True, exist_ok=True)
    receipt = {'source_id': sid, 'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'kind': kind, 'attempts': []}
    if kind == 'html':
        try:
            p = subprocess.run(['defuddle', 'parse', url, '--md'], capture_output=True, text=True, timeout=60)
            text = p.stdout
            receipt['attempts'].append({'method': 'defuddle', 'returncode': p.returncode, 'stderr': p.stderr[:2000]})
            if p.returncode == 0 and len(text.strip()) > 100 and not any(x in text[:1000].lower() for x in ('access denied', 'just a moment...', 'pardon our interruption', 'a required part of this site couldn’t load', 'a required part of this site could not load')):
                (out / f'{name}.md').write_text(text)
                receipt['text_path'] = str((out / f'{name}.md').relative_to(ROOT))
                receipt['text_sha256'] = digest(text.encode())
                receipt['status'] = 'extracted'
        except (OSError, subprocess.TimeoutExpired) as exc:
            receipt['attempts'].append({'method': 'defuddle', 'error': str(exc)})
    try:
        with httpx.Client(follow_redirects=True, timeout=75) as client:
            r = client.get(url)
        receipt['attempts'].append({'method': 'httpx', 'http_status': r.status_code, 'final_url': str(r.url), 'content_type': r.headers.get('content-type'), 'bytes': len(r.content)})
        if r.status_code == 200:
            suffix = {'pdf': '.pdf', 'html': '.html', 'json': '.json'}[kind]
            if kind == 'pdf' and not r.content.startswith(b'%PDF'):
                raise ValueError('200 response is not a PDF')
            path = out / (name + suffix)
            path.write_bytes(r.content)
            receipt.update({'raw_path': str(path.relative_to(ROOT)), 'sha256': digest(r.content), 'final_url': str(r.url)})
            if kind == 'pdf':
                with pymupdf.open(path) as doc:
                    pages = []
                    for i, page in enumerate(doc, 1):
                        # Preserve PDF content-stream reading order: sorting interleaves two-column papers.
                        blocks = [b[4].strip() for b in page.get_text('blocks', sort=False) if b[6] == 0 and b[4].strip()]
                        pages.append({'page': i, 'text': '\n\n'.join(blocks)})
                    receipt['pdf_metadata'] = doc.metadata
                    receipt['pages'] = len(pages)
                    receipt['empty_pages'] = [p['page'] for p in pages if not p['text'].strip()]
                (out / f'{name}.pages.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2))
                text = '\n\n'.join(f'===== PAGE {p["page"]} =====\n\n{p["text"]}' for p in pages)
                (out / f'{name}.txt').write_text(text)
                receipt.update({'text_path': str((out / f'{name}.txt').relative_to(ROOT)), 'text_sha256': digest(text.encode()), 'status': 'extracted'})
            elif kind == 'html' and receipt.get('status') != 'extracted':
                soup = BeautifulSoup(r.text, 'html.parser')
                for el in soup(['script', 'style', 'nav', 'header', 'footer']):
                    el.decompose()
                text = (soup.find('main') or soup.find('article') or soup.body or soup).get_text('\n', strip=True)
                if len(text) < 100 or any(x in text[:1000].lower() for x in ('access denied', 'just a moment...', 'pardon our interruption', 'a required part of this site couldn’t load', 'a required part of this site could not load')):
                    raise ValueError('No accessible substantive HTML content')
                (out / f'{name}.md').write_text(text)
                receipt.update({'text_path': str((out / f'{name}.md').relative_to(ROOT)), 'text_sha256': digest(text.encode()), 'status': 'extracted', 'fallback': 'BeautifulSoup'})
            elif kind == 'json':
                r.json()
                receipt['status'] = 'downloaded'
        elif receipt.get('status') != 'extracted':
            receipt['status'] = 'blocked' if r.status_code in (401, 403, 429) else 'failed'
    except Exception as exc:
        receipt['attempts'].append({'method': 'httpx/extraction', 'error': f'{type(exc).__name__}: {exc}'})
        if receipt.get('status') != 'extracted':
            receipt['status'] = 'failed'
    receipt.setdefault('status', 'failed')
    # A defuddle-only success can still be traced to the saved extraction bytes.
    receipt.setdefault('sha256', receipt.get('text_sha256'))
    (out / f'{name}.receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collection', choices=['B', 'D', 'E', 'F'])
    parser.add_argument('source_id')
    parser.add_argument('url')
    parser.add_argument('kind', choices=['pdf', 'html', 'json'], nargs='?', default='html')
    parser.add_argument('--name', default='source')
    a = parser.parse_args()
    print(json.dumps(acquire(a.collection, a.source_id, a.url, a.kind, a.name), ensure_ascii=False, indent=2))

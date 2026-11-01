#!/usr/bin/env python3
"""Inventário e espelho retomável do acervo público do Inep (sem URLs inventadas)."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ssl
import time
import unicodedata
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / 'data/sources'
CATALOG = SOURCE_ROOT / 'catalogo/acervo.json'
INDEX = 'https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos'
HOSTS = {'www.gov.br', 'download.inep.gov.br', 'download.inep.gov.br:443'}
TLS_CONTEXT = None


def slug(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + '.tmp')
    part.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    part.replace(path)


def fetch(url):
    if urlparse(url).netloc not in HOSTS or urlparse(url).scheme != 'https':
        raise ValueError(f'URL fora dos domínios oficiais autorizados: {url}')
    request = Request(url, headers={'User-Agent': 'EnemFlow/1.0 (acervo educacional; download publico)'} )
    return urlopen(request, timeout=60, context=TLS_CONTEXT)


class ContentParser(HTMLParser):
    """Lê apenas o corpo editorial; mantém o contexto original de cada link."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []; self.events = []; self.capture = None; self.level = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id') == 'parent-fieldname-text': self.level = len(self.stack)
        if self.level is not None and tag in ('h2', 'h3', 'h4', 'p', 'a'):
            self.capture = (tag, attrs, [])
        if tag not in ('br','img','hr','input','meta','link','source','wbr'): self.stack.append(tag)

    def handle_data(self, data):
        if self.capture: self.capture[2].append(data)

    def handle_endtag(self, tag):
        if self.capture and tag == self.capture[0]:
            t,a,text = self.capture; self.events.append((t,a,' '.join(''.join(text).split())))
            self.capture = None
        if tag in self.stack:
            pos = len(self.stack)-1-self.stack[::-1].index(tag)
            self.stack = self.stack[:pos]
        if self.level is not None and len(self.stack) <= self.level: self.level = None


def metadata(year, heading, title, label):
    text = slug(title); h = slug(heading); full = f'{text}-{slug(label)}'
    if 'belem' in h: application = 'belem-ananindeua-marituba'
    elif 'reaplicacao-ppl' in text or ('reaplicacao' in h and 'ppl' in h): application = 'reaplicacao-ppl'
    elif 'reaplicacao' in h or 'reaplicacao' in text: application = 'reaplicacao'
    elif 'ppl' in h or 'ppl' in text: application = 'ppl'
    elif h in ('2a-aplicacao','segunda-aplicacao'): application = 'segunda-aplicacao'
    elif 'digital' in h or 'digital' in text: application = 'digital'
    elif not heading or 'regular' in h: application = 'regular'
    else: application = h  # Preserve any future, unknown official application.
    modality = 'digital' if 'digital' in h or 'digital' in text else 'impresso'
    day_match = re.search(r'(?:\b([12])(?:o|a)?-dia|\bdia-([12])\b)', text)
    day = int(next(v for v in day_match.groups() if v)) if day_match else None
    cm = re.search(r'caderno-(\d+)', text)
    color = next((c for c in ('azul','amarelo','amarela','branco','branca','cinza','rosa','verde','laranja','roxo') if c in text.split('-')), 'sem-cor')
    color = {'amarela':'amarelo','branca':'branco'}.get(color,color)
    booklet = f'caderno-{cm[1]}-{color}' if cm else f'caderno-{color}'
    language = 'ingles' if 'ingles' in text else 'espanhol' if 'espanhol' in text else None
    if language: booklet += '-' + language
    # These are distinct files, even when they share a booklet number and key.
    if 'dosvox' in full: variant = 'dosvox'
    elif 'nvda' in full: variant = 'nvda'
    elif 'superampliad' in full: variant = 'superampliada'
    elif 'ampliad' in full: variant = 'ampliada'
    elif 'atendimento-especializado' in full: variant = 'atendimento-especializado'
    elif 'ledor' in text and 'braile' not in text: variant = 'ledor'
    elif 'ledor' in slug(label): variant = 'ledor'
    elif 'libras' in full: variant = 'libras'
    elif 'braile' in full: variant = 'braile-ledor'
    else: variant = 'padrao'
    return dict(year=year, application=application, modality=modality, day=day,
                booklet=booklet, variant=variant, language=language,
                official_heading=heading, official_title=title)


def parse_year(html, year, page_url):
    parser = ContentParser(); parser.feed(html)
    heading, title = '', ''; records = []
    for tag, attrs, text in parser.events:
        if tag in ('h2','h3','h4'): heading = text
        elif tag == 'p' and ('callout' in attrs.get('class','') or 'caderno' in text.casefold()): title = text
        elif tag == 'a' and attrs.get('href'):
            url = urljoin(page_url, attrs['href']).replace('http://download.inep.gov.br/', 'https://download.inep.gov.br/')
            if not re.search(r'\.(pdf|zip|txt|docx?)(?:\?|$)', url, re.I): continue
            info = metadata(year, heading, title, text)
            role = 'gabarito' if 'gabarito' in text.casefold() else 'prova' if ('prova' in text.casefold() or 'leitor de tela' in text.casefold()) else 'anexo'
            # A name such as LC_CH or CH_CN denotes a combined booklet. Only a
            # single area code can identify a file split by area.
            section_codes=re.findall(r'_(CH|LC|CN|MT)(?=[_.])',url)
            section={'CH':'ciencias-humanas','LC':'linguagens','CN':'ciencias-da-natureza','MT':'matematica'}.get(section_codes[0]) if len(section_codes)==1 else None
            info['section']=section
            if 'redação' in text.casefold():info.update(day=None,booklet='proposta-de-redacao',section='redacao')
            extension = Path(unquote(urlparse(url).path)).suffix.lower()
            variant = info['variant']
            name = role + (f'-{variant}' if variant != 'padrao' else '') + extension
            rel = Path('enem') / str(year) / info['application'] / info['modality'] / (f'dia-{info["day"]}' if info['day'] else 'dia-unico' if year<2009 else 'sem-dia-informado') / info['booklet']
            if section:rel/=section
            rel/=name
            identity = hashlib.sha256(f'{year}|{heading}|{title}|{text}|{url}'.encode()).hexdigest()[:24]
            records.append(dict(id=identity, **info, role=role, label=text, url=url,
                                index_url=page_url, path=rel.as_posix(), status='pending'))
    # Never merge links just because their display title is the same.
    occupied = {}
    for record in records:
        path = record['path']
        if path in occupied and occupied[path] != record['url']:
            p = Path(path); record['path'] = str(p.with_stem(p.stem + '-' + record['id'][:8]))
        occupied[record['path']] = record['url']
    return records


def inventory(refresh=False):
    pages = SOURCE_ROOT / 'catalogo/paginas'; pages.mkdir(parents=True, exist_ok=True)
    index = pages / 'indice.html'
    if refresh or not index.exists():
        with fetch(INDEX) as response: index.write_bytes(response.read())
    years = re.findall(r'data-id="(\d{4})" data-url="([^"]+)"', index.read_text())
    if not years: raise ValueError('O índice não contém abas anuais; revise o parser.')
    old = json.loads(CATALOG.read_text()) if CATALOG.exists() else {}
    previous = {r['id']:r for r in old.get('files', [])}
    records, snapshots = [], []
    for year, url in sorted(years):
        page = pages / f'{year}.html'
        if refresh or not page.exists():
            with fetch(url) as response: page.write_bytes(response.read())
        parsed = parse_year(page.read_text(), int(year), url)
        if not parsed: raise ValueError(f'Nenhum arquivo em {year}; não declarar cobertura vazia como sucesso.')
        for record in parsed:
            prev = previous.get(record['id'], {})
            if prev:
                if prev.get('path')!=record['path'] and prev.get('sha256'):
                    origin=SOURCE_ROOT/prev['path'];target=SOURCE_ROOT/record['path']
                    if origin.exists():
                        if sha(origin)!=prev['sha256']:raise ValueError('Original modificado; reorganização recusada.')
                        if target.exists() and sha(target)!=prev['sha256']:raise ValueError('Destino diferente; reorganização recusada.')
                        target.parent.mkdir(parents=True,exist_ok=True)
                        if not target.exists():origin.rename(target)
                        else:origin.unlink()
                record.update({k:prev[k] for k in ('status','sha256','bytes','error') if k in prev})
        records.extend(parsed)
        snapshots.append(dict(year=int(year), url=url, path=f'catalogo/paginas/{year}.html', sha256=sha(page)))
    result = dict(schema_version='1.0', publisher='Inep', index_url=INDEX,
                  snapshot_created_at=old.get('snapshot_created_at') or datetime.now(timezone.utc).isoformat(),
                  index_sha256=sha(index),
                  scope='Todas as aplicações e formatos com arquivo vinculados no acervo oficial; ausência de link não é ausência de aplicação.',
                  pages=snapshots, files=records)
    write_json(CATALOG, result)
    return result


def validate_file(path):
    with path.open('rb') as f: head = f.read(1024)
    if path.suffix == '.pdf' and b'%PDF-' not in head: raise ValueError('Resposta não é PDF; arquivo recusado.')
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            if archive.testzip(): raise ValueError('ZIP corrompido.')


def download(record, existing):
    record = dict(record); path = SOURCE_ROOT / record['path']; path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        actual = sha(path)
        if record.get('sha256') and actual != record['sha256']:
            return {**record, 'status':'error', 'error':'Hash local divergente; original não sobrescrito.'}
        try: validate_file(path)
        except Exception as e: return {**record, 'status':'error', 'error':str(e)}
        record.update(status='downloaded',sha256=actual,bytes=path.stat().st_size); record.pop('error',None)
        return record
    # Identical URLs can occur in several booklets (a key may cover all colors).
    part = path.with_name(path.name+'.part')
    for attempt in range(3):
        try:
            origin = existing.get(record['url'])
            if origin and origin.is_file():
                import shutil
                shutil.copyfile(origin, part)
            else:
                with fetch(record['url']) as response, part.open('wb') as f:
                    while chunk := response.read(1024*1024): f.write(chunk)
            # Check with the actual extension, before making the file authoritative.
            if path.suffix == '.pdf' and b'%PDF-' not in part.read_bytes()[:1024]: raise ValueError('Resposta não é PDF.')
            if path.suffix == '.zip':
                with zipfile.ZipFile(part) as z:
                    if z.testzip(): raise ValueError('ZIP corrompido.')
            actual = sha(part)
            if record.get('sha256') and actual != record['sha256']: raise ValueError('A fonte remota mudou; versão recusada para revisão.')
            part.replace(path)
            record.update(status='downloaded',sha256=actual,bytes=path.stat().st_size);record.pop('error',None)
            return record
        except Exception as e:
            part.unlink(missing_ok=True)
            if attempt < 2: time.sleep(attempt+1)
            else: return {**record,'status':'error','error':f'{type(e).__name__}: {e}'}


def sync(catalog, workers=4, years=None):
    by_id = {r['id']:r for r in catalog['files']}
    existing = {r['url']:SOURCE_ROOT/r['path'] for r in catalog['files'] if (SOURCE_ROOT/r['path']).is_file()}
    # One task per path prevents two references from writing the same .part file.
    groups = {}
    for r in catalog['files']:
        if not years or r['year'] in years: groups.setdefault(r['path'], []).append(r)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download, values[0], existing):values for values in groups.values()}
        for future in as_completed(futures):
            result = future.result(); done += 1
            for record in futures[future]:
                for key in ('status','sha256','bytes','error'):
                    if key in result: by_id[record['id']][key] = result[key]
                    else: by_id[record['id']].pop(key, None)
            if done % 20 == 0 or result['status'] == 'error':
                write_json(CATALOG,catalog)
                print(f'{done}/{len(groups)} {result["status"]} {result["path"]}',flush=True)
    write_json(CATALOG,catalog)
    print(json.dumps(summary(catalog),ensure_ascii=False),flush=True)


def summary(catalog):
    files = catalog['files']
    return dict(years=sorted({r['year'] for r in files}), references=len(files),
                urls=len({r['url'] for r in files}), downloaded=sum(r['status']=='downloaded' for r in files),
                errors=[{'url':r['url'],'error':r.get('error')} for r in files if r['status']=='error'],
                bytes=sum(r.get('bytes',0) for r in {r['path']:r for r in files}.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['inventory','sync','audit','reference'])
    parser.add_argument('--refresh',action='store_true',help='Reconsultar páginas; nunca sobrescrever PDFs divergentes.')
    parser.add_argument('--workers',type=int,choices=range(1,9),default=4)
    parser.add_argument('--years',type=int,nargs='+')
    parser.add_argument('--ca-file',type=Path,help='Intermediário TLS validado; mantém os certificados de confiança do sistema.')
    args=parser.parse_args()
    if args.ca_file:
        global TLS_CONTEXT
        TLS_CONTEXT=ssl.create_default_context();TLS_CONTEXT.load_verify_locations(cafile=str(args.ca_file))
    catalog = inventory(args.refresh) if args.command=='inventory' else json.loads(CATALOG.read_text())
    if args.command=='reference':
        # The official matrix is a local, recoverable original; its immutable
        # manifest and structured definitions remain versioned.
        source=json.loads((SOURCE_ROOT/'referencias/manifesto.json').read_text())
        result=download(source,{})
        print(json.dumps({key:result.get(key) for key in ('path','status','sha256','bytes','error')},ensure_ascii=False))
        if result['status']!='downloaded':raise SystemExit(2)
    elif args.command=='sync':
        sync(catalog,args.workers,args.years)
        if any(r['status']=='error' for r in catalog['files'] if not args.years or r['year'] in args.years):raise SystemExit(2)
    elif args.command=='audit':
        problems=[]
        for r in catalog['files']:
            p=SOURCE_ROOT/r['path']
            if r['status']!='downloaded' or not p.is_file() or sha(p)!=r.get('sha256'): problems.append(r['path'])
        print(json.dumps({'summary':summary(catalog),'problems':problems},ensure_ascii=False,indent=2))
        if problems: raise SystemExit(2)
    else: print(json.dumps(summary(catalog),ensure_ascii=False,indent=2))


if __name__=='__main__': main()

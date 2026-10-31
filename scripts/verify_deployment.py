"""Exercise a disposable deployment and verify its state after service replacement."""
import argparse
import hashlib
import http.cookiejar
import json
import secrets
import urllib.request
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['create','check'])
    parser.add_argument('--url',required=True)
    parser.add_argument('--state',type=Path,required=True)
    args=parser.parse_args()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(path,data=None,method=None):
        body=json.dumps(data).encode() if data is not None else None
        req=urllib.request.Request(args.url.rstrip('/')+'/api'+path,data=body,headers={'Content-Type':'application/json'},method=method)
        with opener.open(req,timeout=30) as response:
            content=response.read()
            return json.loads(content) if response.headers.get_content_type()=='application/json' else content
    def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if args.phase=='create':
        if args.state.exists(): raise SystemExit('Estado já existe; preserve o ensaio anterior e escolha outro arquivo.')
        credentials={'email':'deploy-'+secrets.token_hex(6)+'@invalid.local','password':secrets.token_urlsafe(24)}
        request('/auth/register',{'name':'Validação descartável',**credentials})
        run=request('/exam-runs',{'exam_id':'enem-2024-dia2-azul','idempotency_key':secrets.token_hex(12)})
        first=run['items'][0]
        request(f"/exam-runs/{run['id']}/answers/{first['id']}",{'choice':'B'},'PUT')
        finished=request(f"/exam-runs/{run['id']}/finish",{},'POST')
        assert finished['result']['correct']==1 and finished['result']['total']==89
        asset=next(b['asset']['path'] for b in first['blocks'] if b['type']=='image')
        state={'credentials':credentials,'run_id':run['id'],'first_id':first['id'],'result':finished['result'],
               'items_sha256':digest(finished['items']),'asset':asset,'asset_sha256':hashlib.sha256(request(asset)).hexdigest()}
        args.state.parent.mkdir(parents=True,exist_ok=True)
        with args.state.open('x') as stream: json.dump(state,stream)
        args.state.chmod(0o600)
        print('Conta descartável, 90 itens, resposta B e resultado 1/89 persistidos para o ensaio.')
    else:
        state=json.loads(args.state.read_text())
        request('/auth/login',state['credentials'])
        run=request('/exam-runs/'+state['run_id'])
        assert run['answers'][state['first_id']]=='B'
        assert run['result']==state['result'] and digest(run['items'])==state['items_sha256']
        assert hashlib.sha256(request(state['asset'])).hexdigest()==state['asset_sha256']
        assert any(r['id']==run['id'] for r in request('/me/history'))
        repeated=request('/exam-runs/'+state['run_id']+'/finish',{},'POST')
        assert repeated['result']==state['result']
        print('Após recriação: login, histórico, resposta, resultado, 90 snapshots, figura e finalização idempotente preservados.')


if __name__=='__main__': main()

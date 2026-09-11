"""Phase 3 TEST-only orchestrator. python -m news.phase3 [--send-test]."""
import argparse
import contextlib
import io
import json
import hashlib
import re
import unittest
from pathlib import Path
from datetime import datetime,timezone
from news import daily
from news.phase3_briefing import load, build, quality, GateError, digest
from news.phase3_kakao import send

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/phase3'
EXISTING=['news.test_daily','news.test_phase1','news.test_phase2','news.test_phase21','news.test_phase22','news.test_phase23']


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def tests(names,path):
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.loadTestsFromNames(names)
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    path.write_text(stream.getvalue(),encoding='utf-8')
    return {'count':result.testsRun,'passed':result.wasSuccessful(),'log_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def unchanged():
    baseline=json.loads((OUT/'quality/baseline.json').read_text(encoding='utf-8'))
    # Handoff is the sole intentional existing documentation change.
    return all((ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in baseline['hashes'].items() if p!='SESSION_HANDOFF.md')


def run(send_test=False):
    rows=load(ROOT)
    artifact=build(rows)
    cfg=daily.config()
    secrets=[v for k,v in cfg.items() if re.search('KEY|TOKEN|SECRET',k)]
    evidence={'existing':tests(EXISTING,OUT/'logs/tests_existing.txt'),'new':tests(['news.test_phase3'],OUT/'logs/tests_phase3.txt'),'unchanged':unchanged()}
    (OUT/'logs/tests.txt').write_text((OUT/'logs/tests_existing.txt').read_text(encoding='utf-8')+'\n'+(OUT/'logs/tests_phase3.txt').read_text(encoding='utf-8'),encoding='utf-8')
    gate=quality(rows,artifact,**dict(existing=evidence['existing'],new=evidence['new'],unchanged=evidence['unchanged'],secrets=secrets))
    (OUT/'briefing/detailed_briefing.md').write_text(artifact['detailed'],encoding='utf-8')
    write(OUT/'briefing/weekly_overview.json',artifact['overview'])
    write(OUT/'kakao/mobile_messages.json',artifact['messages'])
    (OUT/'kakao/mobile_preview.md').write_text('\n\n---\n\n'.join(m['text'] for m in artifact['messages']),encoding='utf-8')
    write(OUT/'quality/artifact.json',artifact)
    write(OUT/'quality/test_evidence.json',evidence)
    write(OUT/'quality/quality_gate.json',gate)
    receipt={'status':'NOT_SENT_GATE_HOLD','messages_sent':0,'live':0}
    if gate['status']=='PASS':
        load(ROOT)  # Revalidate pinned source immediately before delivery.
        receipt=send(ROOT,rows,artifact,evidence,secrets,dry_run=not send_test)
    write(OUT/'kakao/test_receipt.json',receipt)
    write(OUT/'logs/run.json',{'time':datetime.now(timezone.utc).isoformat(),'gate':gate['status'],'receipt_status':receipt['status'],'tavily_calls':0,'gemini_calls':0,'live':0,'input_sha256':artifact['input_sha256'],'post_settings_unchanged':unchanged()})
    print(json.dumps({'gate':gate['status'],'existing':evidence['existing'],'new':evidence['new'],'receipt':receipt['status'],'messages_planned':len(artifact['messages']),'messages_sent':receipt['messages_sent'],'live':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--send-test',action='store_true')
    args=parser.parse_args()
    try: run(args.send_test)
    except Exception as error:
        # Never echo credentials or arbitrary exception bodies.
        print(json.dumps({'status':'HOLD','error_type':type(error).__name__,'live':0}))
        raise SystemExit(1)

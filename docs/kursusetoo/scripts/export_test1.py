"""Export the frozen Test1 cohort; Oracle and automatic artifacts are read-only."""
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from export_dataset_b import ROOT, REMOTE, B, NEW, geometry


def main():
    cohort = set()
    for line in (ROOT / 'docs/evaluation_data.md').read_text().splitlines():
        m = re.match(r'\| (\d+) \| `([^`]+)` \| Jah \|', line)
        if m and 14 <= int(m[1]) <= 29:
            for part in m[2].split(','):
                ends = list(map(int, part.strip().split('–')))
                cohort.update((int(m[1]), cid) for cid in range(ends[0], ends[-1]+1))
    assert len(cohort) == 488
    training = ROOT / 'log/training_data_b.csv'
    assert hashlib.sha256(training.read_bytes()).hexdigest() == '4a7e4dbbbf8c760e10ae49f9cc2b0d77de96fa0ee517731053486d64328c9095'
    train = list(csv.DictReader(io.StringIO(training.read_text())))
    assert not {int(r['process']) for r in train} & {p for p, _ in cohort}
    snapshot = json.loads(subprocess.run(
        ['docker','compose','exec','-T','api','python','-c',REMOTE],
        input=json.dumps(sorted({p for p, _ in cohort})), text=True,
        capture_output=True, check=True, cwd=ROOT).stdout)
    records = {(int(r[0]), int(r[1])): r for r in snapshot['candidates']}
    assert len(records) == len(snapshot['candidates'])
    rows = []
    manifest = {'cohort_date': '2026-10-19', 'features': B, 'artifacts': {}}
    for pid, cid in sorted(cohort):
        r = records[pid, cid]
        assert r[8] == r[9] and r[9] in ('ACCEPTED','MODIFIED','REJECTED') and r[10]
        artifacts = snapshot['artifacts'][str(pid)]
        spans = sorted(artifacts['DIARIZATION_JSON']['data']['segments'],
                       key=lambda x: (float(x['start']),float(x['end'])))
        assert all(float(a['end']) <= float(b['start'])+1e-9 or a['speaker_id']==b['speaker_id']
                   for a,b in zip(spans,spans[1:])), pid
        s = artifacts['AUTOMATIC_TRANSCRIPT_JSON']['data']['segments'][int(r[3])-1]
        start,end = float(s['start']),float(s['end'])
        assert abs(start-float(r[4])) <= .00051 and abs(end-float(r[5])) <= .00051
        assert s['text'] == r[6]
        row = dict(process=pid,candidate=cid,segment=r[2],no=r[3],
                   duration_s=round(float(r[5])-float(r[4]),3),words=len(s['text'].split()),
                   show_speaker_count=len({x['speaker_id'] for x in spans}),
                   candidate_type=r[7],decision=r[9])
        row.update(zip(NEW,geometry(start,end,spans)))
        assert all(row[n] != '' for n in B), (pid,cid,'Missing feature')
        rows.append(row)
        manifest['artifacts'][str(pid)] = {k:{f:v[f] for f in ('path','sha256')} for k,v in artifacts.items()}
    assert Counter(r['decision'] for r in rows) == {'ACCEPTED':290,'MODIFIED':107,'REJECTED':91}
    # Verify shared observations against the historical B export, feature by feature.
    old = {int(r['candidate']):r for r in csv.DictReader((ROOT/'log/test_data_b.csv').open())}
    for r in rows:
        if r['candidate'] in old:
            for name in B:
                a,b = r[name],old[r['candidate']][name]
                assert (str(a)==b if name=='candidate_type' else abs(float(a)-float(b))<1e-8), (r['candidate'],name,a,b)
    dest = ROOT/'log/test1_data_b.csv'
    with dest.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['process','candidate','segment','no',*B,'decision'])
        w.writeheader();w.writerows(rows)
    manifest.update(rows=len(rows),processes=sorted({p for p,_ in cohort}),
                    labels=dict(Counter(r['decision'] for r in rows)),
                    sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                    training_sha256=hashlib.sha256(training.read_bytes()).hexdigest())
    with (ROOT/'docs'/'kursusetoo'/'manifestid'/'test1_manifest.json').open('x') as f:
        json.dump(manifest,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='artifacts'},indent=2))


if __name__ == '__main__':
    main()

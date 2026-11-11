"""Enrich the frozen course CSVs using read-only Oracle and automatic artifacts."""
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCES = {
    'training_data_b.csv': ('test_data_process_30_to_end_with_show_speaker_count.csv', 1006),
    'test_data_b.csv': ('test_data_external_processes_14_to_29.csv', 341),
}
NEW = ['internal_speaker_change_count', 'distinct_speaker_count',
       'dominant_speaker_coverage', 'nearest_change_edge_ratio']
B = ['duration_s', 'words', 'show_speaker_count', 'candidate_type', *NEW]

REMOTE = r"""
import json, sys
from app.database.oracle import connection
ids = json.load(sys.stdin)
binds = {"p"+str(i): p for i,p in enumerate(ids)}
clause = ','.join(':'+k for k in binds)
result = {"candidates": [], "artifacts": {}}
with connection() as conn:
    with conn.cursor() as cur:
        cur.execute('SET TRANSACTION READ ONLY')
        cur.execute('''SELECT tv.process_id, rc.id, s.id, s.segment_number,
            s.start_second, s.end_second, s.text, rc.candidate_type,
            rc.status, rc.decision, rc.decision_at
            FROM review_candidates rc JOIN transcript_segments s
            ON s.id=rc.transcript_segment_id JOIN transcript_versions tv
            ON tv.id=s.transcript_version_id
            WHERE tv.version_type='AUTOMATIC_DRAFT' AND tv.end_date IS NULL
            AND s.end_date IS NULL AND rc.end_date IS NULL
            AND tv.process_id IN (''' + clause + ')', binds)
        result['candidates'] = cur.fetchall()
        cur.execute('''SELECT tv.process_id, a.artifact_type, a.path
            FROM transcript_versions tv JOIN transcript_artifacts ta
            ON ta.transcript_version_id=tv.id JOIN artifacts a ON a.id=ta.artifact_id
            WHERE tv.version_type='AUTOMATIC_DRAFT' AND tv.end_date IS NULL
            AND ta.end_date IS NULL AND a.end_date IS NULL
            AND a.artifact_type IN ('DIARIZATION_JSON','AUTOMATIC_TRANSCRIPT_JSON')
            AND tv.process_id IN (''' + clause + ')', binds)
        for pid, typ, path in cur.fetchall():
            import hashlib
            from pathlib import Path
            data = Path(path).read_bytes()
            entry = result['artifacts'].setdefault(str(pid), {})
            assert typ not in entry, (pid, typ)
            entry[typ] = {'path': path, 'sha256': hashlib.sha256(data).hexdigest(),
                          'data': json.loads(data)}
print(json.dumps(result, default=str))
"""


def geometry(start, end, spans):
    assert end > start
    clipped = defaultdict(list)
    changes = []
    current = None
    for span in spans:
        a, b, label = float(span['start']), float(span['end']), span['speaker_id']
        assert b > a
        if a >= end:
            break
        if a > start and current is not None and label != current:
            changes.append(a)
        current = label
        if b > start:
            clipped[label].append((max(start, a), min(end, b)))
    lengths = []
    for intervals in clipped.values():
        total, left, right = 0., *intervals[0]
        for a, b in intervals[1:]:
            if a > right:
                total += right-left
                left, right = a, b
            else:
                right = max(right, b)
        lengths.append(total + right-left)
    assert lengths
    coverage = max(lengths)/(end-start)
    assert 0 <= coverage <= 1.000000001
    edge = min(min(t-start, end-t)/(end-start) for t in changes) if changes else None
    assert edge is None or 0 < edge <= .5
    return [len(changes), len(clipped), f'{coverage:.8f}',
            '' if edge is None else f'{edge:.8f}']


def main():
    if '--training-only' in sys.argv:
        SOURCES.pop('test_data_b.csv')
    if '--test-only' in sys.argv:
        SOURCES.pop('training_data_b.csv')
    datasets = {}
    allowed = set()
    for line in (ROOT/'docs/evaluation_data.md').read_text().splitlines():
        match = re.match(r'\| (\d+) \| `([^`]+)` \| Jah \|', line)
        if match:
            for part in match[2].split(','):
                ends = [int(x) for x in part.strip().split('–')]
                allowed.update((int(match[1]), n) for n in range(ends[0], ends[-1]+1))
    for output, (source, expected) in SOURCES.items():
        path = ROOT/'log'/source
        reader = csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig')))
        rows = list(reader)
        assert len(rows) == expected
        assert len({r['candidate'] for r in rows}) == expected
        missing = [(r['process'], r['candidate']) for r in rows
                   if (int(r['process']), int(r['candidate'])) not in allowed]
        # User-approved 2026-10-17: preserve the historical test cohort,
        # including these eight known unreliable labels, for comparison.
        if output == 'test_data_b.csv':
            missing = [(p, c) for p, c in missing
                       if not (int(p) == 15 and 171 <= int(c) <= 178)]
        assert not missing, (source, missing)
        datasets[output] = (reader.fieldnames, rows)
    processes = [{int(r['process']) for r in rows} for _, rows in datasets.values()]
    assert len(processes) < 2 or not processes[0] & processes[1]
    snapshot = json.loads(subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'api', 'python', '-c', REMOTE],
        input=json.dumps(sorted(set.union(*processes))), text=True,
        capture_output=True, check=True, cwd=ROOT).stdout)
    records = {int(r[1]): r for r in snapshot['candidates']}
    assert len(records) == len(snapshot['candidates'])
    manifest = {'features_b': B, 'datasets': {}, 'artifacts': {}}
    manifest_path = ROOT/'docs'/'kursusetoo'/'manifestid'/'dataset_b_manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        assert manifest['features_b'] == B
    prepared = {}
    for output, (fields, rows) in datasets.items():
        enriched = []
        for row in rows:
            pid, cid = int(row['process']), int(row['candidate'])
            rec = records[cid]
            assert rec[0] == pid and rec[2] == int(row['segment'])
            assert rec[7] == row['candidate_type']
            assert rec[8] == rec[9] == row['decision'] and rec[10]
            assert int(row['human_action_required']) == int(row['decision']=='MODIFIED')
            artifacts = snapshot['artifacts'][str(pid)]
            raw = artifacts['DIARIZATION_JSON']['data']['segments']
            spans = sorted(raw, key=lambda x:(float(x['start']), float(x['end'])))
            # Exclusive diarization is required: do not invent a change order for overlapping speakers.
            assert all(float(a['end']) <= float(b['start']) + 1e-9
                       or a['speaker_id'] == b['speaker_id'] for a,b in zip(spans,spans[1:])), pid
            segment = artifacts['AUTOMATIC_TRANSCRIPT_JSON']['data']['segments'][int(rec[3])-1]
            start, end = float(segment['start']), float(segment['end'])
            assert abs(start-float(rec[4])) <= .00051 and abs(end-float(rec[5])) <= .00051
            assert segment['text'] == rec[6]
            assert abs((end-start)-float(row['duration_s'])) < .011
            assert int(row['show_speaker_count']) == len({s['speaker_id'] for s in spans})
            values = geometry(start, end, spans)
            enriched.append(dict(row, **dict(zip(NEW, values))))
            manifest['artifacts'][str(pid)] = {k:{f:v[f] for f in ('path','sha256')} for k,v in artifacts.items()}
        prepared[output] = (fields+NEW, enriched)
        source = ROOT/'log'/SOURCES[output][0]
        manifest['datasets'][output] = {'rows':len(rows), 'source':source.name,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'labels':dict(Counter(r['decision'] for r in rows)),
            'missing_edge_ratio':sum(r[NEW[-1]]=='' for r in enriched)}
        if output == 'test_data_b.csv':
            manifest['datasets'][output]['known_label_issue'] = {
                'process': 15, 'candidates': list(range(171, 179)),
                'reason': 'Historical UI stored decisions as MODIFIED; actual decision types cannot be recovered.',
                'authorization': 'User explicitly requested identical historical test cohort on 2026-10-17.'}
    # Write new deliverables only after every source row has passed validation.
    for output,(fields,rows) in prepared.items():
        path = ROOT/'log'/output
        with path.open('x', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        with path.open(newline='', encoding='utf-8') as handle:
            actual = list(csv.DictReader(handle))
        originals = datasets[output][1]
        assert all(all(row[k]==original[k] for k in original) for row,original in zip(actual,originals))
        assert len(actual) == len(originals)
        manifest['datasets'][output]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest['datasets'], indent=2))


if __name__ == '__main__':
    main()

"""Export the frozen Test2 cohort; Oracle and automatic artifacts are read-only."""
import csv
import hashlib
import json
import subprocess
from collections import Counter

from export_dataset_b import ROOT, REMOTE, B, NEW, geometry


PROCESSES = [33, 43, 79, 80, 83, 89, 91, 94, 102, 103, 104, 105, 107, 108]
EXPECTED_LABELS = {'ACCEPTED': 62, 'MODIFIED': 151, 'REJECTED': 124}


def main():
    training = ROOT / 'log/training_data_b.csv'
    assert hashlib.sha256(training.read_bytes()).hexdigest() == (
        '4a7e4dbbbf8c760e10ae49f9cc2b0d77de96fa0ee517731053486d64328c9095')
    train_processes = {int(row['process']) for row in csv.DictReader(training.open())}
    assert not train_processes & set(PROCESSES)
    snapshot = json.loads(subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'api', 'python', '-c', REMOTE],
        input=json.dumps(PROCESSES), text=True, capture_output=True, check=True,
        cwd=ROOT).stdout)
    records = {(int(row[0]), int(row[1])): row for row in snapshot['candidates']}
    assert len(records) == len(snapshot['candidates'])
    rows, manifest_artifacts = [], {}
    for pid in PROCESSES:
        process_records = sorted((row for (process, _), row in records.items() if process == pid),
                                 key=lambda row: int(row[1]))
        assert process_records, pid
        assert all(row[8] == row[9] and row[9] in EXPECTED_LABELS and row[10]
                   for row in process_records), pid
        artifacts = snapshot['artifacts'][str(pid)]
        spans = sorted(artifacts['DIARIZATION_JSON']['data']['segments'],
                       key=lambda span: (float(span['start']), float(span['end'])))
        assert all(float(a['end']) <= float(b['start']) + 1e-9
                   or a['speaker_id'] == b['speaker_id'] for a, b in zip(spans, spans[1:])), pid
        for row in process_records:
            segment = artifacts['AUTOMATIC_TRANSCRIPT_JSON']['data']['segments'][int(row[3]) - 1]
            start, end = float(segment['start']), float(segment['end'])
            assert abs(start - float(row[4])) <= .00051 and abs(end - float(row[5])) <= .00051
            assert segment['text'] == row[6]
            output = dict(process=pid, candidate=int(row[1]), segment=int(row[2]), no=int(row[3]),
                          duration_s=round(end - start, 3), words=len(segment['text'].split()),
                          show_speaker_count=len({span['speaker_id'] for span in spans}),
                          candidate_type=row[7], decision=row[9])
            output.update(zip(NEW, geometry(start, end, spans)))
            assert all(output[name] != '' for name in B), (pid, row[1], 'missing feature')
            rows.append(output)
        manifest_artifacts[str(pid)] = {
            name: {field: value[field] for field in ('path', 'sha256')}
            for name, value in artifacts.items()}
    assert len(rows) == 337
    assert Counter(row['decision'] for row in rows) == EXPECTED_LABELS
    destination = ROOT / 'log' / 'test2_data_b.csv'
    with destination.open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['process', 'candidate', 'segment', 'no', *B, 'decision'])
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        'cohort_date': '2026-10-20', 'features': B, 'rows': len(rows),
        'processes': PROCESSES, 'labels': EXPECTED_LABELS,
        'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'training_sha256': hashlib.sha256(training.read_bytes()).hexdigest(),
        'artifacts': manifest_artifacts,
    }
    manifest_path = ROOT / 'docs' / 'kursusetoo' / 'manifestid' / 'test2_manifest.json'
    with manifest_path.open('x', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=2)
        handle.write('\n')
    print(json.dumps({key: value for key, value in manifest.items() if key != 'artifacts'}, indent=2))


if __name__ == '__main__':
    main()

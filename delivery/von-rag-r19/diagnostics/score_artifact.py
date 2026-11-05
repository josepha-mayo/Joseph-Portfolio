"""Audit recorded neural diagnostics; failed empty output is not model abstention.

This reads already-produced result archives, never runs inference or edits them.
Reported string matching is retained separately from completed-model accuracy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def score_result(expected: dict, result: dict) -> dict:
    prediction = result.get('prediction')
    prediction = prediction if isinstance(prediction, dict) else {}
    citations = prediction.get('citations')
    schema_ok = (isinstance(prediction.get('answer'), str)
                 and isinstance(citations, list)
                 and all(isinstance(x, str) for x in citations))
    literal_match = bool(schema_ok and prediction['answer'] == expected['answer']
                         and set(citations) == set(expected['citations']))
    audit = result.get('audit')
    audit = audit if isinstance(audit, dict) else {}
    proof = audit.get('proof')
    # A mechanical failure has a reason/error and no returned validated proof.
    # A successful retry may retain audit.errors; do not reject recovery merely
    # because an earlier attempt failed.
    completed = bool(not result.get('error') and not audit.get('reason')
                     and schema_ok and isinstance(proof, dict)
                     and proof.get('answer') == prediction['answer']
                     and isinstance(proof.get('evidence'), list)
                     and (bool(proof['evidence']) if prediction['answer'] else not proof['evidence']))
    return {'id': expected['id'], 'literal_output_match': literal_match,
            'completed_validated_model_response': completed,
            'completed_model_exact': completed and literal_match,
            'failure_reason': None if completed else result.get('error', audit.get('reason', 'no_validated_model_proof'))}


def audit_archive(path: Path, expected_sha256: str | None = None) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError('Artifact hash mismatch')
    with zipfile.ZipFile(path) as archive:
        if sum(x.file_size for x in archive.infolist()) > 20_000_000:
            raise ValueError('Unexpected artifact size')
        labels = json.loads(archive.read('labels.json'))
        results = json.loads(archive.read('results.json'))
        traces = json.loads(archive.read('traces.json'))
        receipt = json.loads(archive.read('RECEIPT.json'))
    if len({x['id'] for x in labels}) != len(labels):
        raise ValueError('Duplicate expected query IDs')
    if len({x['id'] for x in results}) != len(results):
        raise ValueError('Duplicate result query IDs')
    indexed = {x['id']: x for x in results}
    if set(indexed) != {x['id'] for x in labels}:
        raise ValueError('Missing or unexpected queries')
    rows = [score_result(label, indexed[label['id']]) for label in labels]
    return {'schema': 'von-rag-completion-aware-model-audit-1', 'artifact_sha256': digest,
            'model': receipt['model'], 'revision': receipt['revision'], 'device': receipt['device'],
            'total': len(rows), 'literal_output_matches': sum(x['literal_output_match'] for x in rows),
            'completed_model_responses': sum(x['completed_validated_model_response'] for x in rows),
            'completed_model_exact': sum(x['completed_model_exact'] for x in rows),
            'generations_reaching_eos': sum(t.get('ended_eos') is True for t in traces),
            'total_generation_calls': len(traces), 'cases': rows,
            'new_inference': False, 'private_grader': False, 'amd_qualification': False,
            'note': 'Audit of recorded authored diagnostics. An empty output after failure is not a successful model refusal.'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit_archive(args.artifact, args.sha256)
    with args.output.open('x') as destination:
        json.dump(report, destination, indent=2)
        destination.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

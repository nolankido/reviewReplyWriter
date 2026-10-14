"""Compare retained fictional-case runs. No customer or statistical quality claims."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_reply as rr
from rrw_evaluate import load_report, summarize, source_snapshot


def compare(before, after):
    if before['cases'] != after['cases']:
        raise ValueError('Case inputs changed; this is not a matched-corpus comparison.')
    if before['execution'] != 'templates' or after['execution'] != 'templates':
        raise ValueError('Use template runs for this deterministic comparison.')
    if not summarize(before)['complete'] or not summarize(after)['complete']:
        raise ValueError('Both selected protocols must be complete.')
    cases = []
    for case, old, new in zip(after['cases'], before['results'], after['results']):
        findings = []
        if old.get('reply'):
            i = case['input']
            body = rr.without_authorized_statements(rr._body(old['reply'], i.get('signoff')), i.get('offer'), i.get('approved_actions'))
            findings = rr.quality.detail_gaps(body, i['review'], i.get('stars'))
        cases.append(dict(id=case['id'], before_status=old['status'], after_status=new['status'],
            before_reply=old.get('reply'), after_reply=new.get('reply'),
            before_original_probe=old.get('rubric_findings', []), after_original_probe=new.get('rubric_findings', []),
            baseline_replayed_detail_findings=findings))
    return dict(kind='deterministic matched-corpus comparison',
        limitation='Developer-written fixtures used during development, not a holdout, unbiased benchmark or human assessment. Replaying old text is not new model inference.',
        before_run=before['id'], after_run=after['id'], before_sources=before['sources'], after_sources=after['sources'],
        before_evidence_sha256=before['sha256'], after_evidence_sha256=after['sha256'],
        before_summary=summarize(before), after_summary=summarize(after), cases=cases)


def replay_historical():
    path = Path(__file__).resolve().parents[1] / 'examples/evaluation/live-smoke-2026-10-13.json'
    report = load_report(path)
    rows = []
    for case, row in zip(report['cases'], report['results']):
        for attempt in row['attempts']:
            draft = dict(case['input'], reply=attempt['candidate'])
            rows.append(dict(case_id=case['id'], attempt=attempt['attempt'],
                candidate=attempt['candidate'], recorded_findings=attempt['findings'],
                current_findings=rr.draft_findings(draft)))
    return dict(kind='historical text replay, NOT fresh Gemma inference',
                historical_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                sources=source_snapshot(), attempts=rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before', required=True, type=Path)
    ap.add_argument('--after', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args=ap.parse_args()
    result=compare(load_report(args.before), load_report(args.after))
    result['historical_replay']=replay_historical()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'before':result['before_summary'],'after':result['after_summary']},indent=2))


if __name__=='__main__': main()

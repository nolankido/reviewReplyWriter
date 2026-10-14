"""Ollama diagnostics and bounded receipts. No downloads or server configuration.

The model listing is a server claim, not proof of local execution. A completed
response is evidence of an API call, not evidence that its contents are true.
"""
from __future__ import annotations

import re

MODEL = 'gemma3:4b'
METRICS = ('total_duration', 'load_duration', 'prompt_eval_count',
           'prompt_eval_duration', 'eval_count', 'eval_duration')


class ModelText(str):
    def __new__(cls, value, receipt):
        item = super().__new__(cls, value)
        item.receipt = receipt
        return item


def checked_response(result):
    if not isinstance(result, dict) or not isinstance(result.get('response'), str):
        raise ValueError('Ollama returned no text response')
    if result.get('done') is not True or result.get('model') != MODEL:
        raise ValueError('Ollama did not return a completed response for gemma3:4b')
    if not result['response'].strip():
        raise ValueError('Ollama returned an empty response')
    if result.get('done_reason') == 'length':
        raise ValueError('Ollama stopped at its output limit; incomplete replies are rejected')
    receipt = {'transport': 'ollama-loopback', 'model': MODEL, 'done': True,
               'done_reason': str(result.get('done_reason', 'unspecified'))[:80]}
    for key in METRICS:
        value = result.get(key)
        if value is not None:
            if type(value) is not int or not 0 <= value <= 10**15:
                raise ValueError('Invalid Ollama metric: ' + key)
            receipt[key] = value
    return ModelText(result['response'].strip(), receipt)


def inspect_model(request=None):
    if request is None:
        from rrw_workspace import local_request
        request = local_request
    report = {'ready': False, 'model': MODEL, 'state': 'unavailable',
              'message': 'Ollama is unavailable. Start Ollama, then check again.',
              'identity': None, 'version': None,
              'local_execution_verified': False,
              'privacy_note': 'A loopback address and model metadata are not a network audit. Enable Ollama local-only mode and restart Ollama.',
              'steps': ['Start Ollama.', 'Run: ollama pull gemma3:4b',
                        'Disable Ollama cloud features and restart it.', 'Recheck, then run the Gemma smoke evaluation.']}
    try:
        result = request('/api/tags')
        if not isinstance(result, dict) or not isinstance(result.get('models'), list):
            raise ValueError('Unexpected model listing')
        candidates = [m for m in result['models'] if isinstance(m, dict) and m.get('name') == MODEL]
        if not candidates:
            report.update(state='missing', message='Ollama is running, but gemma3:4b is not installed.')
            return report
        if len(candidates) != 1:
            raise ValueError('Ambiguous model listing')
        item = candidates[0]
        details = item.get('details', {})
        if not isinstance(details, dict):
            raise ValueError('Malformed model details')
        digest = item.get('digest', '')
        if not isinstance(digest, str) or not re.fullmatch(r'(?:sha256:)?[0-9a-f]{64}', digest):
            raise ValueError('A model digest is required for reproducible evaluation')
        if type(item.get('size')) is not int or item['size'] <= 0:
            raise ValueError('A nonempty downloaded model is required')
        if any(source.get(key) for source in (item, details)
               for key in ('remote_host', 'remote_model')):
            raise ValueError('Cloud-backed model metadata is not accepted by this evaluation')
        if details.get('family') != 'gemma3':
            raise ValueError('This alias does not report the gemma3 family')
        report.update(ready=True, state='installed',
                      message='Gemma 3 is installed. Generation quality is not yet verified.',
                      identity={'name': MODEL, 'digest': digest.removeprefix('sha256:'),
                                'size': item['size'], 'family': 'gemma3',
                                'parameter_size': str(details.get('parameter_size', 'unknown'))[:40],
                                'quantization': str(details.get('quantization_level', 'unknown'))[:40]})
    except (OSError, ValueError) as exc:
        report.update(state='unavailable' if isinstance(exc, OSError) else 'unverified',
                      message='Model setup needs attention: ' + str(exc)[:220])
        return report
    try:
        version = request('/api/version')
        if isinstance(version, dict) and isinstance(version.get('version'), str):
            report['version'] = version['version'][:80]
    except (OSError, ValueError):
        pass  # Missing server version is reported, not invented.
    return report

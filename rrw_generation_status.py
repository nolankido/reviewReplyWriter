"""Bounded saved-generation explanations, separate from approval and raw traces."""

COPY = {
    'offline': ('Template preview, no AI call',
        'You selected templates. This saved reply passed the draft checks without calling Gemma.',
        'Read and edit the reply, then approve its exact content.', None),
    'model_checked': ('Gemma reply saved with a checked API receipt',
        'The selected reply came from a completed gemma3:4b response and passed the draft checks. An API receipt is not a factuality or server privacy guarantee.',
        'Check the details against the review and your policy before approval.', None),
    'model_unverified': ('Model reply saved, completion receipt not verified',
        'The reply passed the draft checks, but this generation has no checked receipt for the selected response. Do not treat it as verified Gemma evidence.',
        'Use the fictional Gemma smoke test in Quality Lab to collect current evidence.', 'quality'),
    'unavailable': ('Template saved: local model request failed',
        'Gemma was requested, but a local request did not complete. A checked template was saved instead, not AI output. The saved reply is available to read and edit.',
        'Check local setup before a deliberate retry. No retry or installation runs automatically.', 'setup'),
    'invalid_response': ('Template saved: model response not accepted',
        'Gemma was requested, but a response could not be accepted as a complete response for the required model. A checked template was saved instead, not AI output.',
        'Check local setup, then test fictional reviews in Quality Lab. Do not rely on this fallback as Gemma evidence.', 'setup'),
    'rejected': ('Template saved: model replies failed the draft checks',
        'Gemma returned replies, but neither attempt passed the draft checks. A checked template was saved instead, not AI output.',
        'Read the failed checks in Generation details. Test fictional reviews in Quality Lab before retrying a customer review.', 'quality'),
    'unknown': ('Generation result not recorded',
        'This older or imported draft has no recognized saved generation result. Its source label and technical details may help, but no new model evidence is inferred.',
        'Read and check the current reply before approval.', None),
}


def checked_receipt(receipt):
    return (isinstance(receipt, dict) and receipt.get('transport') == 'ollama-loopback'
            and receipt.get('model') == 'gemma3:4b' and receipt.get('done') is True
            and isinstance(receipt.get('done_reason'), str)
            and receipt['done_reason'] != 'length')


def outcome(mode, fallback, selected, trace):
    if mode == 'offline':
        state = 'offline'
    elif not fallback:
        state = 'model_checked' if checked_receipt(getattr(selected, 'receipt', None)) else 'model_unverified'
    else:
        state = trace[-1].get('failure', 'rejected') if trace else 'unknown'
    return {'version': 1, 'state': state, 'attempts': len(trace),
            'checked_completions': sum(checked_receipt(item.get('receipt')) for item in trace)}


def summary(draft):
    saved = draft.get('generation_outcome')
    state, attempts, completions = 'unknown', None, None
    if isinstance(saved, dict) and type(saved.get('version')) is int and saved['version'] == 1:
        proposed = saved.get('state')
        a, c = saved.get('attempts'), saved.get('checked_completions')
        if (isinstance(proposed, str) and proposed in COPY and type(a) is int and type(c) is int
                and 0 <= c <= a <= 2 and (proposed != 'offline' or a == 0)
                and (proposed != 'model_checked' or c > 0)):
            state, attempts, completions = proposed, a, c
    title, message, next_step, action = COPY[state]
    return {'state': state, 'title': title, 'message': message, 'next_step': next_step,
            'action': action, 'attempts': attempts, 'checked_completions': completions,
            'owner_edited': draft.get('human_edited') is True}

'use strict';
(function (root) {
  function session(storage, supplied) {
    let token = supplied || '', available = true;
    try {
      if (supplied) storage.setItem('rrw-session', supplied);
      else token = storage.getItem('rrw-session') || '';
    } catch (error) { available = false; }
    return {token, available};
  }
  async function request(path, data, token, fetcher = fetch, deadline) {
    if (!token) throw new Error('Open the session link printed by the launcher to connect this tab.');
    const long = ['generate', 'reroll', 'inbox-step', 'quality-step'].includes(path);
    const controller = new AbortController();
    const options = {method: data === undefined ? 'GET' : 'POST', credentials: 'omit',
      headers: {'X-RRW-Token': token, 'Accept': 'application/json'}, cache: 'no-store', signal: controller.signal};
    if (data !== undefined) {
      options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(data);
    }
    let timer;
    // Race as well as abort: even a broken transport cannot keep controls locked.
    const expired = new Promise((resolve, reject) => {
      timer = setTimeout(() => {
        controller.abort();
        const error = new Error('The request deadline passed. The server may still finish. Your inputs are kept. Check saved results before retrying.');
        error.uncertain = true; reject(error);
      }, deadline === undefined ? (long ? 390000 : 15000) : deadline);
    });
    try {
      return await Promise.race([expired, (async () => {
        const response = await fetcher('/api/' + path, options);
        const result = await response.json();
        if (!response.ok) {
          const error = new Error((result.error || 'The server could not complete this action.') +
            (Array.isArray(result.findings) ? '\n' + result.findings.join('\n') : ''));
          error.status = response.status;
          error.findings = Array.isArray(result.findings) ? result.findings : [];
          throw error;
        }
        return result;
      })()]);
    } catch (error) {
      if (error.status || error.uncertain) throw error;
      const failure = new Error('Connection lost or an unreadable response. Your inputs are kept. Check saved results before retrying.');
      failure.uncertain = true; throw failure;
    } finally { clearTimeout(timer); }
  }
  const api = {session, request};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.rrwConnection = api;
})(typeof window === 'undefined' ? globalThis : window);

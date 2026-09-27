/* Same-origin Jupyter execution. No session-cookie or credential export.
 * The anti-CSRF nonce stays inside the browser and goes only to this origin.
 * Caller must keep the authenticated project browser running.
 */
async (options) => {
  const result = {schema: 'von-jupyter-cell-1', status: 'refused',
    kernel_started: false, execution_reply: false, execution_idle: false,
    cleanup_verified: false, output: '', errors: []};
  let kernelId = null, ws = null, dispatched = false;
  const code = options.code;
  const budget = options.timeout_ms;
  const maxOutput = options.max_output_bytes ?? 262144;
  if (typeof code !== 'string' || !code || code.length > 16000000 ||
      !Number.isInteger(budget) || budget < 100 || budget > 300000 ||
      !Number.isInteger(maxOutput) || maxOutput < 1 || maxOutput > 1048576) {
    result.reason = 'invalid_options'; return result;
  }
  const raw = document.getElementById('jupyter-config-data');
  if (!raw) { result.reason = 'not_a_jupyter_document'; return result; }
  let base;
  try {
    const basePath = JSON.parse(raw.textContent).baseUrl;
    if (typeof basePath !== 'string' || !basePath.startsWith('/') || basePath.startsWith('//'))
      throw new Error('unsafe_base');
    base = new URL(basePath, location.origin);
    if (base.origin !== location.origin || base.search || base.hash || base.username || base.password)
      throw new Error('unsafe_base');
  } catch (_) { result.reason = 'invalid_server_base'; return result; }
  if (location.protocol !== 'https:' &&
      !['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname)) {
    result.reason = 'insecure_nonlocal_server'; return result;
  }
  if (!base.pathname.endsWith('/')) base.pathname += '/';
  const start = performance.now();
  const request = async (relative, method = 'GET', body = undefined) => {
    const url = new URL(relative, base);
    if (url.origin !== location.origin || !url.pathname.startsWith(base.pathname))
      throw new Error('outside_server');
    const headers = {'Content-Type':'application/json'};
    if (!['GET', 'HEAD'].includes(method)) {
      const cookie = document.cookie.split(';').map(x => x.trim()).find(x => x.startsWith('_xsrf='));
      if (cookie) headers['X-XSRFToken'] = decodeURIComponent(cookie.slice(6));
    }
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 12000);
    try {
      const response = await fetch(url, {method, credentials:'same-origin', headers,
        ...(body === undefined ? {} : {body:JSON.stringify(body)}), signal:abort.signal});
      if (!response.ok) throw new Error('http_' + response.status);
      return response.status === 204 ? null : await response.json();
    } finally { clearTimeout(timer); }
  };
  try {
    const specs = await request('api/kernelspecs');
    if (!specs.kernelspecs?.python3) throw new Error('python3_kernel_missing');
    // No retries: a lost creation response leaves an explicitly uncertain outcome.
    result.creation_attempted = true;
    const kernel = await request('api/kernels', 'POST', {name:'python3', path:'.'});
    if (!kernel || typeof kernel.id !== 'string' || !/^[a-zA-Z0-9-]{1,128}$/.test(kernel.id))
      throw new Error('invalid_kernel_identity');
    kernelId = kernel.id; result.kernel_started = true; result.kernel_id = kernelId;
    const session = crypto.randomUUID(), messageId = crypto.randomUUID();
    const endpoint = new URL('api/kernels/' + kernelId + '/channels', base);
    endpoint.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    endpoint.searchParams.set('session_id', session);
    let bytes = 0;
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('execution_deadline')), budget);
      const done = (error) => { clearTimeout(timer); error ? reject(error) : resolve(); };
      ws = new WebSocket(endpoint);
      ws.onopen = () => {
        dispatched = true;
        ws.send(JSON.stringify({header:{msg_id:messageId, username:'von-runner',
          session, msg_type:'execute_request', version:'5.3', date:new Date().toISOString()},
          parent_header:{}, metadata:{}, channel:'shell', buffers:[],
          content:{code, silent:false, store_history:false, user_expressions:{},
            allow_stdin:false, stop_on_error:true}}));
      };
      ws.onerror = () => done(new Error('websocket_error'));
      ws.onclose = () => { if (!result.execution_reply || !result.execution_idle)
        done(new Error('websocket_closed_before_completion')); };
      ws.onmessage = (event) => {
        let message;
        try { if (typeof event.data !== 'string') throw new Error(); message=JSON.parse(event.data); }
        catch (_) { done(new Error('unsupported_message_encoding')); return; }
        if (message.parent_header?.msg_id !== messageId) return;
        const type = message.header?.msg_type, content = message.content || {};
        if (type === 'stream') {
          const text = typeof content.text === 'string' ? content.text : '';
          bytes += new TextEncoder().encode(text).length;
          if (bytes > maxOutput) { done(new Error('output_limit')); return; }
          result.output += text;
        }
        if (type === 'error') result.errors.push({name:String(content.ename || 'error').slice(0,120)});
        if (type === 'execute_reply') {
          result.execution_reply = true;
          result.reply_status = content.status;
        }
        if (type === 'status' && content.execution_state === 'idle') result.execution_idle = true;
        if (result.execution_idle && result.execution_reply) {
          result.reply_status === 'ok' ? done() : done(new Error('kernel_execution_failed'));
        }
      };
    });
    result.status = 'passed';
  } catch (error) {
    result.status = 'failed';
    result.reason = String(error.message || 'unknown').slice(0,180);
    result.dispatch_outcome = dispatched ? 'sent' : (result.creation_attempted ? 'creation_attempted' : 'not_sent');
  } finally {
    if (ws) { ws.onclose = null; ws.onerror = null; ws.close(); }
    if (kernelId) {
      if (result.status !== 'passed') {
        try { await request('api/kernels/' + kernelId + '/interrupt', 'POST'); }
        catch (_) { result.interrupt_failed = true; }
      }
      try {
        await request('api/kernels/' + kernelId, 'DELETE');
        const running = await request('api/kernels');
        result.cleanup_verified = Array.isArray(running) && !running.some(k => k.id === kernelId);
      } catch (_) { result.cleanup_verified = false; }
      if (!result.cleanup_verified) { result.status='failed'; result.cleanup_reason='owned_kernel_shutdown_unverified'; }
    }
    result.elapsed_seconds = (performance.now()-start)/1000;
  }
  return result;
}

// All server responses are injected fixtures. No calls, accounts or real tokens.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(process.argv[2] || 'upstream');
const mode = process.argv[3] || 'baseline';
assert.ok(['baseline', 'patched'].includes(mode));
const out = path.resolve(process.argv[4] || 'evidence');
fs.mkdirSync(out, { recursive: true });
let unintendedRequests = 0;
globalThis.fetch = async () => {
  unintendedRequests++;
  throw new Error('External requests forbidden in this reproduction');
};
const { runCli } = await import(pathToFileURL(path.join(root, 'packages/cli/lib/cli.js')));
const { tokenCachePath, writePrivateJson } = await import(pathToFileURL(path.join(root, 'packages/core/lib/cache.js')));
const { MCP_PROTOCOL_VERSION } = await import(pathToFileURL(path.join(root, 'packages/core/lib/constants.js')));
const cases = [];
const errorResult = { isError: true, content: [{ type: 'text', text: 'Fixture: requested run does not exist.' }] };
const successResult = { isError: false, content: [{ type: 'text', text: 'Fixture: status found.' }], structuredContent: { run_id: 'fixture-only', status: 'completed' } };

async function exercise(name, route, result, responseKind = 'result') {
  const cacheRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'calle-exit-probe-'));
  const serverUrl = 'https://example.invalid/local-fixture-only';
  let stdout = '', stderr = '';
  const methods = [];
  writePrivateJson(tokenCachePath(cacheRoot, serverUrl), {
    token: { access_token: 'fixture-not-a-real-token' },
    expires_at: new Date(Date.now() + 3600000).toISOString(),
  });
  const fetchImpl = async (url, options) => {
    assert.equal(url, serverUrl);
    const request = JSON.parse(options.body);
    methods.push(request.method);
    if (request.method === 'notifications/initialized') return new Response(null, { status: 202 });
    if (request.method === 'initialize') return new Response(JSON.stringify({
      jsonrpc: '2.0', id: request.id,
      result: { protocolVersion: MCP_PROTOCOL_VERSION, capabilities: { tools: {} }, serverInfo: { name: 'offline-fixture', version: '1' } },
    }), { headers: { 'content-type': 'application/json' } });
    assert.equal(request.method, 'tools/call');
    assert.equal(request.params.name, 'get_call_run', 'Only a read-only fixture operation is allowed');
    assert.equal(request.params.arguments.run_id, 'fixture-only');
    if (responseKind === 'http-error') return new Response('Fixture failure', { status: 503 });
    const envelope = responseKind === 'rpc-error'
      ? { jsonrpc: '2.0', id: request.id, error: { code: -32602, message: 'Fixture invalid parameters' } }
      : { jsonrpc: '2.0', id: request.id, result };
    return new Response(JSON.stringify(envelope), { headers: { 'content-type': 'application/json' } });
  };
  const command = route === 'generic'
    ? ['mcp', 'call', 'get_call_run', '--args-json', JSON.stringify({ run_id: 'fixture-only' })]
    : ['call', 'status', '--run-id', 'fixture-only'];
  try {
    const exitCode = await runCli([...command, '--cache-root', cacheRoot, '--server-url', serverUrl], {
      env: { ...process.env, DO_NOT_TRACK: '1', CALLE_TELEMETRY: '0' },
      stdout: text => { stdout += text; }, stderr: text => { stderr += text; },
      fetchImpl, telemetryFetchImpl: globalThis.fetch,
    });
    const parsed = JSON.parse(stdout);
    const row = { name, route, response_kind: responseKind, exit_code: exitCode, wrapper_ok: parsed.ok, nested_isError: parsed.result?.isError ?? null, fixture_requests: methods, stdout: parsed, stderr };
    cases.push(row);
    const isToolError = responseKind === 'result' && result?.isError === true;
    if (route === 'generic' && responseKind === 'result') assert.deepEqual(parsed.result, result, 'Raw tool result should be preserved');
    const shouldFail = responseKind !== 'result' || isToolError;
    if (mode === 'baseline' && route === 'generic' && isToolError) {
      assert.equal(exitCode, 0, 'The reported baseline bug no longer reproduces');
      assert.equal(parsed.ok, true);
      assert.equal(parsed.result.isError, true);
      row.observation = 'Reproduced false-success wrapper and zero exit code for explicit tool error';
    } else {
      assert.equal(exitCode, shouldFail ? 1 : 0);
      assert.equal(parsed.ok, !shouldFail);
    }
  } finally { fs.rmSync(cacheRoot, { recursive: true, force: true }); }
}

try {
  await exercise('Generic route: normal JSON tool success', 'generic', successResult);
  await exercise('Generic route: explicit JSON tool error', 'generic', errorResult);
  await exercise('Typed status route: same explicit JSON tool error', 'typed', errorResult);
  await exercise('Generic route: isError absent', 'generic', { content: [] });
  await exercise('Generic route: JSON-RPC error', 'generic', null, 'rpc-error');
  await exercise('Generic route: HTTP error', 'generic', null, 'http-error');
  assert.equal(unintendedRequests, 0);
  const report = { status: 'completed', mode, node: process.version, platform: process.platform, scope: 'Injected local JSON fixtures only. No live CALL-E service requests, calls or credentials.', cases, unintended_requests: unintendedRequests };
  fs.writeFileSync(path.join(out, mode + '.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  fs.writeFileSync(path.join(out, mode + '.json'), JSON.stringify({ status: 'failed', mode, cases, unintended_requests: unintendedRequests, error: String(error), stack: error.stack }, null, 2) + '\n');
  throw error;
}

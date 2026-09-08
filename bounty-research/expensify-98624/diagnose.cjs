/* AI-assisted scope diagnostic. Runs unchanged, pinned Expensify modules.
 * This is NOT an iOS/Android app run, production reproduction, or proposed patch.
 * Filesystem adapters use real Node disk I/O; UI, Onyx, native fetch and FormData
 * are controlled boundaries. No customer accounts, API calls, or funds are used.
 */
'use strict';
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const ts = require('typescript');
const root = path.resolve(process.argv[2] || path.join(__dirname, 'snapshot'));
const out = path.resolve(process.argv[3] || path.join(__dirname, 'evidence'));
fs.mkdirSync(out, {recursive: true});
const upstream = '9f9ddbd4b4edfc615a9cec78aa24da45188f9f1a';
const report = {status: 'running', upstream, node: process.version, typescript: ts.version,
    scope: 'Unchanged source-level diagnostics with real temporary disk I/O and controlled native boundaries. Not native app/device QA; no patch tested or upstream PR opened.',
    started_at: new Date().toISOString(), sources: {}, checks: []};
let temporary;
class CapturedFormData {
    constructor() { this.fields = []; }
    append(key, value) { this.fields.push([key, value]); }
    has(key) { return this.fields.some(([k]) => k === key); }
    get(key) { return this.fields.find(([k]) => k === key)?.[1] ?? null; }
}
const noCall = (name) => () => { throw new Error('Unexpected boundary call: '+name); };
function load(name, dependencies, globals = {}) {
    const source = fs.readFileSync(path.join(root, name), 'utf8');
    report.sources[name] = crypto.createHash('sha256').update(source).digest('hex');
    const compiled = ts.transpileModule(source, {fileName: name, compilerOptions: {
        target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop: true,
    }, reportDiagnostics: true});
    assert.equal((compiled.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error).length, 0);
    const exports = {};
    const module = {exports};
    const requireStub = (id) => {
        if (!Object.hasOwn(dependencies, id)) throw new Error('Missing explicit dependency '+id+' for '+name);
        return dependencies[id];
    };
    vm.runInNewContext(compiled.outputText, {exports, module, require: requireStub, console,
        Blob, File, URL, Promise, setTimeout, clearTimeout, FormData: CapturedFormData, ...globals}, {filename: name});
    return module.exports;
}
async function check(name, run) {
    try { const detail = await run(); report.checks.push({name, status: 'passed', ...detail}); }
    catch (error) { report.checks.push({name, status: 'failed', error: String(error)}); throw error; }
}
(async () => {
    temporary = await fsp.mkdtemp(path.join(os.tmpdir(), 'expensify-98624-'));
    const folder = path.join(temporary, 'CURRENT/Documents/Receipts-Upload');
    const cacheRoot = path.join(temporary, 'CURRENT/Library/Caches');
    const current = 'file://'+path.join(folder, 'image.png');
    const stale = 'file://'+path.join(temporary, 'STALE/Documents/Receipts-Upload/image.png');
    const missing = 'file://'+path.join(folder, 'missing.png');
    const picture = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jKZkAAAAASUVORK5CYII=', 'base64');
    await fsp.mkdir(folder, {recursive: true});
    await fsp.writeFile(path.join(folder, 'image.png'), picture);
    const calls = {reads: [], warnings: [], debug: [], drops: [], onyx: [], copies: [], exists: []};
    const reset = () => { for (const v of Object.values(calls)) v.length = 0; };
    const uriToPath = load('src/libs/fileURIToPath.ts', {}).default;
    const fileExists = async uri => { calls.exists.push(uri); try { await fsp.access(uriToPath(uri)); return true; } catch { return false; } };
    const RNFS = {CachesDirectoryPath: cacheRoot, exists: fileExists,
        mkdir: p => fsp.mkdir(p, {recursive: true}),
        copyFile: async (from, to) => { calls.copies.push([from, to]); await fsp.copyFile(uriToPath(from), to); },
        unlink: p => fsp.rm(uriToPath(p), {recursive: true}), moveFile: noCall('moveFile')};
    const fetchLocal = async uri => {
        calls.reads.push(uri);
        assert.ok(uri.startsWith('file://'), 'Diagnostic must never use the network');
        const data = await fsp.readFile(uriToPath(uri));
        return {ok: true, status: 200, blob: async () => new Blob([data], {type: 'image/png'})};
    };
    const Log = {warn: (...a) => calls.warnings.push(a), hmmm: noCall('Log.hmmm'), info: noCall('Log.info')};
    const util = load('src/libs/fileDownload/FileUtils.ts', {
        '@libs/DateUtils': {}, '@libs/fileURIToPath': uriToPath, '@libs/getPlatform': () => 'ios',
        '@libs/Log': Log, '@libs/saveLastRoute': noCall('saveLastRoute'), '@src/CONST': {},
        'expensify-common': {Str: {}}, 'react-native': {Platform: {OS: 'ios'}, Alert: {}, Linking: {}},
        'react-native-blob-util': {}, 'react-native-image-size': {},
        './getImageManipulator': noCall('getImageManipulator'), './getImageResolution': noCall('getImageResolution'),
    }, {fetch: fetchLocal, console: {...console, debug: (...a) => calls.debug.push(a)}});
    const storage = load('src/libs/ReceiptStorage/index.native.ts', {
        '@libs/fileDownload/FileUtils': util, '@libs/fileURIToPath': uriToPath,
        '@libs/getReceiptsUploadFolderPath': () => folder, '@libs/NumberUtils': {rand64: noCall('rand64')},
        'react-native-fs': RNFS,
    }).default;
    const prepare = load('src/libs/prepareRequestPayload/index.native.ts', {
        '@libs/fileDownload/checkFileExists': fileExists, '@libs/fileDownload/FileUtils': util,
        '@libs/ReceiptStorage': storage,
        '@libs/telemetry/ReceiptObservability': {logReceiptDropped: (...a) => calls.drops.push(a)},
        '@libs/validateFormDataParameter': () => {},
    }).default;
    const attachment = load('src/libs/actions/Attachment/index.native.ts', {
        '@libs/AttachmentUtils': {getImageCacheFileExtension: mime => mime === 'image/png' ? 'png' : undefined},
        '@libs/Log': Log, '@src/CONST': {API_ATTACHMENT_VALIDATIONS: {MAX_SIZE: 100000}},
        '@src/ONYXKEYS': {COLLECTION: {ATTACHMENT: 'attachment_'}},
        'react-native-blob-util': {config: noCall('RNFetchBlob.config')}, 'react-native-fs': RNFS,
        'react-native-onyx': {set: async (...a) => calls.onyx.push(a)},
    }, {fetch: noCall('attachment HEAD')});
    const file = source => ({source, uri: source, name: 'image.png', type: 'image/png'});
    await check('Real resolver maps a stale receipts URI to the current file', async () => {
        assert.equal(storage.resolve(stale), current); assert.equal(await fileExists(current), true); assert.equal(await fileExists(stale), false);
    });
    await check('Unchanged offline file path omits image but returns comment field', async () => {
        reset(); const body = await prepare('AddComment', {file: file(stale), comment: 'synthetic comment'}, true);
        assert.equal(body.has('file'), false); assert.equal(body.get('comment'), 'synthetic comment');
        assert.deepEqual(calls.reads, [stale]); assert.equal(calls.drops.length, 0); assert.equal(calls.debug.length, 1);
        return {file_present: false, comment_present: true, dedicated_receipt_drop_events: 0, file_utils_debug_events: 1};
    });
    await check('Resolved-input control appends exact file bytes with the same unchanged function', async () => {
        reset(); const body = await prepare('AddComment', {file: file(storage.resolve(stale)), comment: 'synthetic comment'}, true);
        assert.equal(body.has('file'), true); assert.equal(body.get('file').uri, current);
        assert.deepEqual(Buffer.from(await body.get('file').arrayBuffer()), picture);
        assert.equal(calls.debug.length, 0); return {file_present: true, bytes_equal: true, note: 'Input control, not a patched app'};
    });
    await check('Receipt branch already resolves the same stale URI', async () => {
        reset(); const body = await prepare('RequestMoney', {receipt: file(stale), amount: '100'}, true);
        assert.equal(body.has('receipt'), true); assert.equal(body.get('receipt').uri, current); assert.equal(calls.drops.length, 0);
    });
    await check('Current-path offline file still appends', async () => {
        reset(); const body = await prepare('AddComment', {file: file(current)}, true); assert.equal(body.has('file'), true);
    });
    await check('A genuinely missing file is also omitted, so resolving alone is not failure handling', async () => {
        reset(); assert.equal(storage.resolve(missing), missing);
        const body = await prepare('AddComment', {file: file(missing), comment: 'synthetic comment'}, true);
        assert.equal(body.has('file'), false); assert.equal(body.has('comment'), true); assert.equal(calls.drops.length, 0);
        assert.equal(calls.debug.length, 1);
    });
    await check('Missing receipt emits existing dedicated telemetry unlike missing file', async () => {
        reset(); const body = await prepare('RequestMoney', {receipt: file(missing), amount: '100'}, true);
        assert.equal(body.has('receipt'), false); assert.equal(calls.drops.length, 1);
    });
    await check('Native online file branch passes through without re-read', async () => {
        reset(); const value = file(stale); const body = await prepare('AddComment', {file: value}, false);
        assert.equal(body.get('file'), value); assert.equal(calls.reads.length, 0);
    });
    await check('Offline file without source retains original pass-through', async () => {
        reset(); const value = {uri: current, name: 'image.png', type: 'image/png'};
        const body = await prepare('AddComment', {file: value}, true); assert.equal(body.get('file'), value); assert.equal(calls.reads.length, 0);
    });
    await check('Cache copy from stale URI fails even though current file exists', async () => {
        reset(); await attachment.cacheAttachment({attachmentID: 'stale', uri: stale, mimeType: 'image/png'});
        assert.equal(calls.warnings.length, 1); assert.equal(calls.onyx.length, 0);
        assert.equal(calls.copies[0][0], stale); assert.equal(calls.warnings[0][1].error.code, 'ENOENT');
        return {copy_error: 'ENOENT', onyx_cache_record_written: false};
    });
    await check('Resolved-input cache control copies bytes and publishes Onyx record', async () => {
        reset(); await attachment.cacheAttachment({attachmentID: 'current', uri: storage.resolve(stale), mimeType: 'image/png'});
        assert.equal(calls.warnings.length, 0); assert.equal(calls.onyx.length, 1);
        assert.deepEqual(await fsp.readFile(path.join(cacheRoot, 'attachments/current.png')), picture);
    });
    await check('Cache miss returns stale currentSource without recovery', async () => {
        reset(); const result = await attachment.getCachedAttachment({attachmentID: 'none', currentSource: stale});
        assert.equal(result, stale); assert.equal(calls.onyx.length, 0);
    });
    await check('Receipt resolver does not repair Caches/attachments paths', async () => {
        const staleCache = 'file://'+path.join(temporary, 'STALE/Library/Caches/attachments/current.png');
        assert.equal(storage.resolve(staleCache), staleCache);
        const result = await attachment.getCachedAttachment({attachmentID: 'current', attachment: {source: path.join(cacheRoot, 'attachments/current.png')}, currentSource: stale});
        assert.equal(result, 'file://'+path.join(cacheRoot, 'attachments/current.png'));
    });
    await check('Resolver preserves remote and non-receipts local paths', async () => {
        for (const source of ['https://example.invalid/image.png', 'content://test/image', 'blob:fixture', 'file:///other/file.png', '/other/file.png']) assert.equal(storage.resolve(source), source);
    });
    await check('Web payload implementation stays independent of native replay', async () => {
        reset(); const web = load('src/libs/prepareRequestPayload/index.ts', {'@libs/validateFormDataParameter': () => {}}).default;
        const value = file(stale); const body = await web('AddComment', {file: value, comment: 'text', none: null, unset: undefined}, true);
        assert.equal(body.get('file'), value); assert.equal(body.get('comment'), 'text'); assert.equal(body.has('none'), false); assert.equal(calls.reads.length, 0);
    });
    report.status = 'passed';
})().catch(error => { report.status = 'failed'; report.error = error.stack; process.exitCode = 1; })
.finally(async () => {
    if (temporary) await fsp.rm(temporary, {recursive: true, force: true});
    report.finished_at = new Date().toISOString();
    fs.writeFileSync(path.join(out, 'diagnostic.json'), JSON.stringify(report, null, 2)+'\n');
    console.log(JSON.stringify(report, null, 2));
});

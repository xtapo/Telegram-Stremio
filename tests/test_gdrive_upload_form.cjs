// Run with: node tests/test_gdrive_upload_form.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.join(__dirname, '../Backend/fastapi/templates/music_management.html'), 'utf8');
const start = template.indexOf('async function startGDriveUpload()');
const end = template.indexOf('function startPollingGDriveUpload()', start);
assert(start >= 0 && end > start);
assert.match(template, /<input type="password" id="gdrive-archive-password"/);

async function checkSubmission(succeeds) {
    const password = ' album pass;$ ';
    const elements = {
        'gdrive-url-input': { value: 'https://example.com/album.rar' },
        'gdrive-channel-select': { value: '-100123' },
        'gdrive-archive-password': { value: password },
        'btn-start-gdrive-upload': {},
    };
    let request;
    const context = vm.createContext({
        document: { getElementById: id => elements[id] },
        fetch: async (url, options) => {
            request = { url, payload: JSON.parse(options.body) };
            return { ok: succeeds, json: async () => ({ status: succeeds ? 'success' : 'error' }) };
        },
        alertToast() {}, switchToGDriveProgressView() {}, startPollingGDriveUpload() {},
    });
    vm.runInContext(template.slice(start, end), context);
    await context.startGDriveUpload();
    assert.equal(request.url, '/api/music/gdrive-upload/start');
    assert.equal(request.payload.archive_password, password);
    assert.equal(elements['gdrive-archive-password'].value, succeeds ? '' : password);
    assert.equal(elements['btn-start-gdrive-upload'].disabled, false);
}

(async () => {
    await checkSubmission(true);
    await checkSubmission(false);
    console.log('PASS: password submission, clearing on success, retention on rejected start');
})().catch(error => { console.error(error); process.exitCode = 1; });

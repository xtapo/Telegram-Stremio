// Run: node tests/test_music_pagination_form.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.join(__dirname, '../Backend/fastapi/templates/music_management.html'), 'utf8');
const start = template.indexOf('function isMusicPaginationSize(');
const end = template.indexOf("document.addEventListener('DOMContentLoaded'", start);
assert(start >= 0 && end > start);

function fixture() {
    const elements = Object.fromEntries([
        'music-player-page-size', 'music-player-mobile-page-size', 'music-pagination-settings-save',
        'music-pagination-settings-reload', 'music-pagination-settings-status', 'music-pagination-settings-form',
    ].map(id => [id, { value: '', disabled: false, textContent: '', reportValidity: () => true }]));
    const context = vm.createContext({ document: { getElementById: id => elements[id] } });
    vm.runInContext(template.slice(start, end), context);
    return { context, elements };
}

async function run() {
    const { context, elements } = fixture();
    const desktop = elements['music-player-page-size'];
    const mobile = elements['music-player-mobile-page-size'];
    const button = elements['music-pagination-settings-save'];
    const status = elements['music-pagination-settings-status'];
    context.fetch = async url => {
        assert.equal(url, '/api/music/player-settings');
        return { ok: true, json: async () => ({ status: 'success', settings: { music_tracklist_page_size: 60, music_mobile_tracklist_page_size: 50 } }) };
    };
    await context.loadMusicPaginationSettings();
    assert.equal(desktop.value, 60);
    assert.equal(mobile.value, 50);
    assert.equal(button.disabled, false);

    desktop.value = '30'; mobile.value = '20';
    let request, calls = 0, release;
    context.fetch = async (url, options) => {
        calls++;
        request = { url, payload: JSON.parse(options.body) };
        await new Promise(resolve => { release = resolve; });
        return { ok: true, json: async () => ({ message: 'Saved' }) };
    };
    const event = { preventDefault() {} };
    const pending = context.saveMusicPaginationSettings(event);
    await context.saveMusicPaginationSettings(event);
    assert.equal(calls, 1, 'duplicate saves are suppressed');
    assert.equal(desktop.disabled, true);
    assert.equal(request.url, '/api/admin/settings');
    assert.deepEqual(request.payload, { music_tracklist_page_size: 30, music_mobile_tracklist_page_size: 20 });
    release(); await pending;
    assert.match(status.textContent, /Đã lưu phân trang/);
    assert.equal(button.disabled, false);

    for (const invalid of ['9', '201', '20.5', '', 'Infinity']) {
        desktop.value = invalid;
        await context.saveMusicPaginationSettings(event);
    }
    assert.equal(calls, 1, 'invalid sizes never reach the backend');

    desktop.value = '40';
    context.fetch = async () => ({ ok: false, json: async () => ({ detail: 'Save rejected' }) });
    await context.saveMusicPaginationSettings(event);
    assert.match(status.textContent, /Save rejected/);
    assert.equal(desktop.value, '40', 'rejected saves preserve input for retry');
    assert.equal(button.disabled, false);

    context.fetch = async () => { throw new Error('Offline'); };
    await context.loadMusicPaginationSettings();
    assert.equal(button.disabled, true, 'failed loads cannot overwrite saved configuration with defaults');
    assert.equal(elements['music-pagination-settings-reload'].disabled, false);
    console.log('PASS: pagination form loading, exact save payload, duplicate saves, validation, and retry');
}

run().catch(error => { console.error(error); process.exitCode = 1; });

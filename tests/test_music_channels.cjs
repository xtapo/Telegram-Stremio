// Run: node --test tests/test_music_channels.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const template = fs.readFileSync(path.join(__dirname, '../Backend/fastapi/templates/music_management.html'), 'utf8');

function functionSource(name) {
    const pattern = new RegExp(`^(?:async )?function ${name}\\(`, 'm');
    const match = pattern.exec(template);
    if (!match) return '';
    return template.slice(match.index, template.indexOf('\n}', match.index) + 2);
}

function fixture(response) {
    const elements = {
        'channels-chips-list': { innerHTML: '' },
        'gdrive-channel-select': { innerHTML: '' },
    };
    let renders = 0;
    let nextTimer = 0;
    const timers = new Map();
    const context = vm.createContext({
        document: { getElementById: id => elements[id] },
        fetch: async url => {
            assert.equal(url, '/api/music/channels');
            return response.clone();
        },
        renderChannelsList: () => { renders++; },
        configuredChannels: [{ id: '-100old' }],
        AbortController,
        setTimeout: (callback, delay) => {
            const id = ++nextTimer;
            timers.set(id, { callback, delay });
            return id;
        },
        clearTimeout: id => timers.delete(id),
    });
    vm.runInContext([
        'escapeHtml', 'fetchMusicChannels', 'loadChannelsList', 'loadGDriveChannelsList',
    ].map(functionSource).join('\n'), context);
    return { context, elements, timers, renders: () => renders };
}

function json(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status, headers: { 'content-type': 'application/json' },
    });
}

for (const status of [502, 503, 504]) {
    test(`scan dialog reports HTML HTTP ${status} without a JSON syntax error`, async () => {
        const { context, elements, timers } = fixture(new Response('<html>Gateway Timeout</html>', {
            status, headers: { 'content-type': 'text/html' },
        }));
        await context.loadChannelsList();
        const message = elements['channels-chips-list'].innerHTML;
        assert.match(message, new RegExp(`HTTP ${status}`));
        assert.doesNotMatch(message, /Unexpected token|Gateway Timeout|<html>/);
        assert.equal(timers.size, 0, 'HTTP errors clear the request timeout');
    });
}

test('JSON service failures are shown as errors instead of an empty channel list', async () => {
    const { context, elements } = fixture(json({ detail: 'Kho dữ liệu tạm thời không phản hồi. Vui lòng thử lại.' }, 503));
    await context.loadChannelsList();
    assert.match(elements['channels-chips-list'].innerHTML, /Kho dữ liệu tạm thời/);
    assert.doesNotMatch(elements['channels-chips-list'].innerHTML, /Chưa có kênh nhạc/);
});

test('authentication failures prompt the user to log in again', async () => {
    const { context, elements } = fixture(json({ detail: 'Not authenticated' }, 401));
    await context.loadChannelsList();
    assert.match(elements['channels-chips-list'].innerHTML, /đăng nhập/i);
});

test('successful loads render saved channels', async () => {
    const channels = [{ id: '-100123', name: 'Nhạc Việt' }];
    const { context, renders, timers } = fixture(json({ status: 'success', channels }));
    await context.loadChannelsList();
    assert.deepEqual(JSON.parse(JSON.stringify(context.configuredChannels)), channels);
    assert.equal(renders(), 1);
    assert.equal(timers.size, 0, 'successful loads clear the request timeout');
});

test('a successful empty list still shows the channel setup prompt', async () => {
    const { context, elements } = fixture(json({ status: 'success', channels: [] }));
    await context.loadChannelsList();
    assert.match(elements['channels-chips-list'].innerHTML, /Chưa có kênh nhạc/);
});

test('malformed success responses are reported as errors', async () => {
    for (const response of [
        new Response('<html>Login page</html>', { headers: { 'content-type': 'text/html' } }),
        new Response('{broken', { headers: { 'content-type': 'application/json' } }),
        json({ status: 'success', channels: {} }),
    ]) {
        const { context, elements } = fixture(response);
        await context.loadChannelsList();
        assert.match(elements['channels-chips-list'].innerHTML, /Lỗi tải danh sách kênh/);
        assert.doesNotMatch(elements['channels-chips-list'].innerHTML, /Unexpected token|Login page/);
    }
});

test('an unresponsive request is aborted and the user can retry', async () => {
    const { context, elements, timers } = fixture();
    let signal;
    context.fetch = async (url, options) => {
        signal = options.signal;
        return new Promise((resolve, reject) => {
            signal.addEventListener('abort', () => reject(new Error('Request aborted')));
        });
    };
    const loading = context.loadChannelsList();
    const timeout = timers.values().next().value;
    assert.equal(timeout.delay, 10000);
    timeout.callback();
    await loading;
    assert.equal(signal.aborted, true);
    assert.match(elements['channels-chips-list'].innerHTML, /phản hồi quá chậm/);
    assert.equal(timers.size, 0);

    context.fetch = async () => json({ status: 'success', channels: [] });
    await context.loadChannelsList();
    assert.match(elements['channels-chips-list'].innerHTML, /Chưa có kênh nhạc/);
});

test('backend error messages are escaped when shown in the scan dialog', async () => {
    const { context, elements } = fixture(json({ detail: '<img src=x onerror=alert(1)>' }, 503));
    await context.loadChannelsList();
    assert.match(elements['channels-chips-list'].innerHTML, /&lt;img/);
    assert.doesNotMatch(elements['channels-chips-list'].innerHTML, /<img/);
});

test('Google Drive channel picker shows HTTP errors instead of a setup prompt', async () => {
    const { context, elements } = fixture(new Response('<html>Gateway Timeout</html>', {
        status: 504, headers: { 'content-type': 'text/html' },
    }));
    await context.loadGDriveChannelsList();
    assert.match(elements['gdrive-channel-select'].innerHTML, /HTTP 504/);
});

test('Google Drive channel picker escapes channel names and IDs', async () => {
    const { context, elements } = fixture(json({ status: 'success', channels: [
        { id: '" onfocus="alert(1)', name: '<img src=x onerror=alert(1)>' },
    ] }));
    await context.loadGDriveChannelsList();
    const options = elements['gdrive-channel-select'].innerHTML;
    assert.match(options, /&lt;img/);
    assert.doesNotMatch(options, /<img|value="" onfocus=/);
});

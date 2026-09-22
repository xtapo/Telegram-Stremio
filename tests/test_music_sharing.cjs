// Run with: node tests/test_music_sharing.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../Music/sharing.js'), 'utf8');
const context = vm.createContext({
    document: { activeElement: null, getElementById: () => ({ textContent: '' }) },
    requestAnimationFrame: fn => fn(),
});
vm.runInContext(source + '\nglobalThis.Controller = MusicSharingController;', context);

function fixture() {
    const controller = Object.create(context.Controller.prototype);
    const events = [];
    const control = () => ({ value: '', textContent: '', disabled: false, focus() {}, replaceChildren() {}, classList: { remove() {} } });
    Object.assign(controller, {
        app: {
            currentUser: { _id: 'alice' }, favoriteTracks: [{ title: 'Song' }],
            openModal() {}, closeModal() {}, openAuthModal() { events.push('login'); },
            showToast(message) { events.push(message); },
        },
        sendModal: control(), inboxModal: control(), recipient: control(), error: control(),
        sendButton: control(), moreButton: control(), refreshButton: control(), list: control(),
        generation: 0, sending: false, loading: false,
    });
    return { controller, events };
}

async function run() {
    let { controller, events } = fixture();
    controller.openFavorites({ chat_id: -100, msg_id: 42, title: 'Original title', artist: 'Artist' });
    controller.recipient.value = ' @bob ';
    const requests = [];
    let release;
    context.fetch = async (url, options) => {
        requests.push({ url, payload: JSON.parse(options.body) });
        await new Promise(resolve => { release = resolve; });
        return { ok: true, json: async () => ({ status: 'success', message: 'Sent' }) };
    };
    const pending = controller.send();
    await controller.send();
    assert.equal(requests.length, 1, 'double click submits once while request is in flight');
    assert.equal(controller.sendButton.disabled, true);
    assert.deepEqual(requests[0].payload, {
        kind: 'favorites', recipient: 'bob',
        favorite: { chat_id: '-100', msg_id: '42', title: 'Original title', artist: 'Artist' },
    });
    release();
    await pending;
    assert.deepEqual(events, ['Sent']);
    assert.equal(controller.sendButton.disabled, false);

    context.fetch = async () => ({ ok: false, json: async () => ({ detail: 'Recipient missing' }) });
    await controller.send();
    assert.equal(controller.error.textContent, 'Recipient missing');
    assert.equal(controller.sendButton.disabled, false, 'can retry after server rejection');
    controller.openFavorites();
    assert.equal(controller.selection.favorite, undefined, 'share all resets a prior single-song selection');
    controller.app.currentUser = null;
    controller.openPlaylist({ id: 'pl1', name: 'Playlist', tracks: [{}] });
    assert.equal(events.at(-1), 'login');

    ({ controller, events } = fixture());
    controller.openPlaylist({ id: 'pl1', name: 'Playlist', tracks: [{}] });
    controller.recipient.value = 'bob';
    context.fetch = async () => {
        await new Promise(resolve => { release = resolve; });
        return { ok: true, json: async () => ({ status: 'success', message: 'Stale result' }) };
    };
    const stale = controller.send();
    controller.reset();
    release();
    await stale;
    assert.deepEqual(events, [], 'logout suppresses results from the previous account');
    assert.equal(controller.selection, null);
    assert.equal(controller.refreshButton.disabled, false);
    assert.equal(controller.sendButton.disabled, false);
    console.log('PASS: favorite selection, duplicate-submit guard, errors/retry, auth, and stale-account isolation');
}

run().catch(error => { console.error(error); process.exitCode = 1; });

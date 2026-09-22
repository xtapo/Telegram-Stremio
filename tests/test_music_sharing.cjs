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

    const appSource = fs.readFileSync(path.join(__dirname, '../Music/app.js'), 'utf8');
    const method = (start, end) => appSource.slice(appSource.indexOf(start), appSource.indexOf(end, appSource.indexOf(start)));
    const playerMethods = [
        method('    isSharedFavorite(', '    updateFavoriteBtnState('),
        method('    async removeTrackFromPlaylist(', '    async reorderPlaylistTracks('),
        method('    async reorderPlaylistTracks(', '    async handleCreatePlaylist('),
        method('    async deletePlaylist(', '    playPlaylist('),
        method('    async addTrackToPlaylist(', '    async addTracksToPlaylist('),
    ].join('\n');
    const Player = vm.runInContext(`(class { ${playerMethods} })`, context);
    const player = new Player();
    const track = { name: 'Shared song', chatId: '-100', msgId: '42' };
    const shared = { id: 'pl_shared', source_share_id: 'share1', name: 'Shared playlist', tracks: [track] };
    player.playlists = [shared];
    player.favoriteTracks = [{ title: 'Shared song', chat_id: -100, msg_id: 42, source_share_id: 'share1' }];
    player.getTrackIdentifiers = track => ({ chatId: String(track.chatId || ''), msgId: String(track.msgId || '') });
    player.showToast = () => {};
    player.renderAddToPlaylistOptions = () => {};
    player.renderPlaylists = () => {};
    player.renderTracklist = () => {};
    player.currentAlbum = { artist: 'Artist', coverUrl: '' };
    let writes = 0;
    context.fetch = async () => { writes++; return { ok: true }; };
    assert.equal(player.isSharedFavorite(track), true);
    assert.equal(player.isSharedFavorite({ ...track, chatId: '-200' }), false);
    await player.removeTrackFromPlaylist(shared.id, track, 0);
    await player.deletePlaylist(shared.id);
    await player.addTrackToPlaylist(shared.id, track);
    assert.equal(writes, 0, 'shared playlist delete and duplicate toggle never send a mutation');
    await player.addTrackToPlaylist(shared.id, { name: 'New song', chatId: '-100', msgId: '43' });
    assert.equal(writes, 1, 'new songs can still be appended');
    assert.equal(shared.tracks.length, 2);
    assert.equal(shared.tracks[0], track, 'existing track is retained');

    const owned = { id: 'pl_owned', name: 'Owned', tracks: [{ name: 'A' }, { name: 'B' }, { name: 'C' }] };
    player.playlists = [owned];
    context.fetch = async (url, options) => {
        writes++;
        assert.equal(url, '/api/music/user/playlists/pl_owned');
        assert.equal(JSON.parse(options.body).tracks.map(item => item.name).join(','), 'B,C,A');
        return { ok: true, json: async () => ({ status: 'success' }) };
    };
    assert.equal(await player.reorderPlaylistTracks('pl_owned', 0, 2), true);
    assert.equal(owned.tracks.map(item => item.name).join(','), 'B,C,A');

    player.playlists = [shared];
    const writesBeforeSharedReorder = writes;
    assert.equal(await player.reorderPlaylistTracks(shared.id, 0, 1), false);
    assert.equal(writes, writesBeforeSharedReorder, 'shared playlist reorder never sends a mutation');
    const tvSource = fs.readFileSync(path.join(__dirname, '../Music/tv.html'), 'utf8');
    for (const script of tvSource.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) {
        new vm.Script(script[1]);
    }
    console.log('PASS: shared playlist UI permits additions and blocks removals; TV scripts compile');
}

run().catch(error => { console.error(error); process.exitCode = 1; });

// Run: node tests/test_music_performance.cjs [--benchmark]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { performance } = require('node:perf_hooks');

class Element {
    constructor() {
        this.children = [];
        this.style = {};
        this.listeners = {};
        this.classList = { toggle() {}, add() {}, remove() {} };
    }
    set innerHTML(value) { this.html = value; this.children = []; }
    get innerHTML() { return this.html || ''; }
    appendChild(child) {
        this.children.push(...(child.fragment ? child.children : [child]));
        return child;
    }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    querySelector() { return new Element(); }
    querySelectorAll() { return []; }
    closest() { return null; }
    remove() {}
}

const source = fs.readFileSync(path.join(__dirname, '../Music/app.js'), 'utf8');
const context = vm.createContext({
    console,
    localStorage: { setItem() {}, removeItem() {} },
    document: {
        createElement: () => new Element(),
        createDocumentFragment: () => Object.assign(new Element(), { fragment: true }),
        getElementById: () => null,
    },
});
vm.runInContext(source.slice(0, source.lastIndexOf('// Script nằm cuối')) + '\nglobalThis.App = XTAPOMusicApp;', context);

function fixture(albums) {
    const app = Object.create(context.App.prototype);
    Object.assign(app, { albums, artistCacheMap: new Map(), searchResults: new Element() });
    app.invalidateLibraryIndex();
    return app;
}

function library(albumCount = 12, trackCount = 20) {
    return Array.from({ length: albumCount }, (_, a) => ({
        id: `a${a}`, title: `Nhạc tuyển chọn ${a}`, artist: `Ca sĩ ${a % 100}`,
        publisher: 'Music', year: '2026',
        tracks: Array.from({ length: trackCount }, (_, t) => ({
            name: `Bài hát nhạc Việt ${t}`, artist: `Ca sĩ ${a % 100}`,
            genre: 'Pop', country: 'Việt Nam', chatId: '-100', msgId: a * trackCount + t,
        })),
    }));
}

async function run() {
    const app = fixture(library());
    assert.equal(app.getCountryMap(), app.getCountryMap(), 'country page reuses its cache before visiting artists');
    app.albums[0].tracks[0].name = 'Đêm nhạc';
    app.albums[0].tracks[1].name = 'Nhạc';
    app.albums[1].tracks[0].name = '東京の夜';
    for (const query of ['nhac', 'dem nhac', 'ca si 2', 'viet 2026', '東京', 'absent', '!!!']) {
        const normalized = app.normalizeSearchText(query);
        const tokens = [...new Set(normalized.split(' ').filter(Boolean))];
        const reference = app.getMusicSearchIndex()
            .map(entry => ({ ...entry, rank: app.scoreMusicSearchEntry(entry, normalized, tokens) }))
            .filter(entry => entry.rank.score > 0)
            .sort((a, b) => b.rank.score - a.rank.score || a.trackName.localeCompare(b.trackName, 'vi'));
        const result = app.findMusicSearchMatches(query);
        assert.equal(result.totalMatches, reference.length, `total matches for ${query}`);
        assert.deepEqual(Array.from(result.matches, item => [item.track.msgId, item.rank.score, item.rank.label]),
            Array.from(reference.slice(0, 100), item => [item.track.msgId, item.rank.score, item.rank.label]),
            `top 100 and stable Vietnamese ranking for ${query}`);
    }
    assert.equal(app.findMusicSearchMatches('nhac').matches[0].track.name, 'Nhạc');
    assert.equal(app.removeVietnameseTones('ĐẶNG đêm e\u0302\u0301'), 'DANG dem e');

    // Repeated typing must reuse normalized album fields, including contained tracks.
    app.albumGrid = new Element();
    app.albumSearchInput = { value: 'khong tim thay' };
    let normalizations = 0;
    const normalize = app.normalizeSearchText;
    app.normalizeSearchText = function (value) { normalizations++; return normalize.call(this, value); };
    app.renderAlbumGrid();
    normalizations = 0;
    app.albumSearchInput.value = 'cung khong tim thay';
    app.renderAlbumGrid();
    assert(normalizations < 10, 'typing another album query must not normalize the library again');
    app.normalizeSearchText = normalize;
    app.albums[0].tracks[0].name = 'Bản mới độc quyền';
    app.invalidateLibraryIndex();
    app.albumSearchInput.value = 'ban moi doc quyen';
    app.renderAlbumGrid();
    assert.equal(app.albumGrid.children.length, 1, 'album text cache invalidates after editing metadata');

    app.invalidateLibraryIndex();
    assert.equal(app.getCountryMap(), app.getCountryMap(), 'country page reuses its cache before visiting artists');
    const genres = app.getGenreGroups();
    assert.equal(genres, app.getGenreGroups(), 'genre grouping is shared across searches and country filters');
    assert(genres.genreMaps.get('all').size > 0);
    const oldIndex = app.getMusicSearchIndex();
    app.invalidateLibraryIndex();
    assert.notEqual(app.getMusicSearchIndex(), oldIndex);
    assert.notEqual(app.getGenreGroups(), genres);

    const metadataApp = fixture([{
        id: 'metadata', title: 'Example', artist: 'Example Artist',
        tracks: [{ name: 'Example Song', artist: 'Example Artist', msgId: 1 }],
    }]);
    assert.equal(metadataApp.getCountryMap().get('Âu Mỹ').tracks.length, 1);
    assert.equal(metadataApp.getGenreGroups().genreMaps.get('all').has('Pop / Ballad'), true);
    context.fetch = async () => ({ ok: true, json: async () => ({
        status: 'success', artists: [{ name: 'Example Artist', country: 'Việt Nam' }],
    }) });
    await metadataApp.fetchArtistMetadata();
    assert.equal(metadataApp.getCountryMap().get('Việt Nam').tracks.length, 1,
        'background artist metadata invalidates inferred countries');
    assert.equal(metadataApp.getGenreGroups().genreMaps.get('all').has('V-Pop / Nhạc Trẻ'), true,
        'background artist metadata invalidates country-dependent genres');

    context.fetch = async url => {
        assert.equal(url, '/api/music/player-settings');
        return { ok: true, json: async () => ({ status: 'success', settings: {
            music_tracklist_page_size: 30, music_mobile_tracklist_page_size: 20,
        } }) };
    };
    await app.fetchMusicPlayerSettings();
    assert.equal(app.getTracklistPageSize(), 30);
    assert.equal(app.getTracklistPageSize(true), 20);

    // Profile verification still gates library loading, but personal lists must not delay it.
    const authApp = fixture([]);
    let releaseLists;
    const listsPending = new Promise(resolve => { releaseLists = resolve; });
    const started = [];
    context.fetch = async () => ({ json: async () => ({ status: 'authenticated', user: { _id: 'alice' } }) });
    Object.assign(authApp, {
        updateAuthUI() {}, startHeartbeat() {},
        fetchUserFavorites() { started.push('favorites'); return listsPending; },
        loadPlaylists() { started.push('playlists'); return listsPending; },
        async fetchTelegramAlbums() { started.push('albums'); },
    });
    const profile = authApp.fetchUserProfile(true);
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(started, ['favorites', 'playlists', 'albums'], 'library starts while personal lists are pending');
    releaseLists();
    await profile;
    for (const status of ['guest', 'pending_approval']) {
        started.length = 0;
        context.fetch = async () => ({ json: async () => ({ status, user: { _id: 'alice' } }) });
        authApp.updateAuthUI = authApp.stopHeartbeat = authApp.showChannelWarningBanner = () => {};
        await authApp.fetchUserProfile(true);
        assert.equal(started.length, 0, `${status} cannot trigger a library request`);
    }

    if (process.argv.includes('--benchmark')) {
        const large = fixture(library(3000));
        const measure = (label, fn) => {
            const start = performance.now(); fn();
            console.log(`${label}: ${(performance.now() - start).toFixed(1)} ms`);
        };
        measure('search cold, 60000 tracks', () => large.handleSearch('nhac'));
        measure('search warm, 60000 tracks', () => large.handleSearch('nhac'));
        large.albumGrid = new Element();
        large.albumSearchInput = { value: 'khong co ket qua' };
        measure('album search first', () => large.renderAlbumGrid());
        large.albumSearchInput.value = 'khong co ket qua khac';
        measure('album search next query', () => large.renderAlbumGrid());
    }
    console.log('PASS: search ranking, accent tolerance, reusable indexes, metadata invalidation, and parallel startup');
}

run().catch(error => { console.error(error); process.exitCode = 1; });

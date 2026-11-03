// Run: node tests/test_music_tracklist.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { performance } = require('node:perf_hooks');

class Element {
    constructor(tag = 'div') {
        this.tagName = tag;
        this.children = [];
        this.style = {};
        this.dataset = {};
        this.listeners = {};
        this.classes = new Set();
        this.classList = {
            add: (...names) => names.forEach(name => this.classes.add(name)),
            remove: (...names) => names.forEach(name => this.classes.delete(name)),
            contains: name => this.classes.has(name),
        };
    }
    set className(value) { this.classes = new Set(value.split(/\s+/)); }
    get className() { return [...this.classes].join(' '); }
    set innerHTML(value) { this.html = value; this.children = []; }
    get innerHTML() { return this.html || ''; }
    setAttribute(key, value) { if (key === 'data-index') this.dataset.index = String(value); }
    appendChild(child) {
        if (child.fragment) {
            this.children.push(...child.children);
            child.children = [];
        } else this.children.push(child);
        return child;
    }
    replaceChildren(...children) { this.children = []; children.forEach(child => this.appendChild(child)); }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    querySelector(selector) {
        if (selector === '.search-item-cover') return new Element('img');
        const index = selector.match(/data-index="(\d+)"/);
        return this.children.find(child => index ? child.dataset.index === index[1]
            : selector === '.track-item.active' ? child.classList.contains('active')
                : selector === 'button' && child.tagName === 'button') || null;
    }
    querySelectorAll(selector) {
        return this.children.filter(child => selector === '.track-item'
            ? child.classList.contains('track-item') : child.classList.contains(selector.slice(1)));
    }
    scrollIntoView() { this.scrolledIntoView = true; }
    closest() { return null; }
    click() { this.listeners.click?.({ stopPropagation() {} }); }
}

const source = fs.readFileSync(path.join(__dirname, '../Music/app.js'), 'utf8');
const context = vm.createContext({
    console, setTimeout: () => 0, requestAnimationFrame: () => {},
    document: {
        createElement: tag => new Element(tag), querySelector: () => null,
        createDocumentFragment: () => Object.assign(new Element(), { fragment: true }),
        getElementById: () => null,
    },
});
vm.runInContext(source.slice(0, source.lastIndexOf('// Script nằm cuối')) + '\nglobalThis.App = XTAPOMusicApp;', context);

function fixture() {
    const tracks = Array.from({ length: 78886 }, (_, i) => ({
        name: `Track ${i}`, artist: 'Example Artist', chatId: '-1001', msgId: i + 1, duration: '3:00',
    }));
    tracks[77284].name = 'Ngày Còn Đôi Mươi';
    const app = Object.create(context.App.prototype);
    let created = 0;
    Object.assign(app, {
        albums: [{ id: 'large', title: 'MUSIC XTAPO', artist: 'GRASSHOPPER', tracks }],
        currentAlbumIndex: 0, currentTrackIndex: 0, currentUser: { _id: 'alice' },
        tracklistEl: new Element('ul'), modalTracklistEl: new Element('ul'), searchResults: new Element(),
        nowPlayingTitle: new Element(), nowPlayingArtist: new Element(), timeTotal: new Element(), timeCurrent: new Element(),
        cancelSeamlessTransition() {}, updateAudioBadges() {}, updateCovers() {}, updateDrawerInfo() {},
        updateProgress() {}, stopAudioSynth() {}, syncPlaybackCacheWindow() {}, pauseVisuals() {},
        getTrackCover: () => '', getPlaybackStreamUrl: () => '', renderAlbumGrid() {}, closeModal() {}, showToast() {},
        play() { this.isPlaying = true; },
        createTrackListItem(track, idx) {
            created++;
            const row = new Element('li');
            row.className = `track-item${idx === this.currentTrackIndex ? ' active' : ''}`;
            row.setAttribute('data-index', idx);
            row.textContent = track.name;
            return row;
        },
    });
    app.invalidateLibraryIndex();
    return { app, tracks, created: () => created };
}

const { app, tracks, created } = fixture();
app.handleSearch('ngay con doi muoi');
const result = app.searchResults.children.find(child => child.classList.contains('search-item'));
assert(result, 'the regression starts at the real search-result click handler');
const start = performance.now();
result.click();
const elapsed = performance.now() - start;
console.log(`Search -> track #77285 of 78886: ${created()} rows created, ${elapsed.toFixed(1)} ms (DOM fixture)`);
assert.equal(app.currentTrack, tracks[77284], 'search plays the exact selected track');
assert(app.tracklistEl.querySelector('.track-item.active')?.scrolledIntoView, 'selected track is visible');
assert(created() <= 180, 'selecting a late search result must not construct all preceding tracks');
assert(app.tracklistEl.querySelectorAll('.track-item').length <= 60, 'main tracklist has at most 60 mounted tracks');
assert(app.modalTracklistEl.querySelectorAll('.track-item').length <= 50, 'mobile tracklist has at most 50 mounted tracks');

// Repainting a late selection and switching albums must also remain bounded.
app.renderTracklist();
assert(app.tracklistEl.querySelectorAll('.track-item').length <= 60);
assert(app.tracklistEl.querySelector('.track-item.active'));
app.albums.push({ id: 'other', title: 'Other', tracks: tracks.slice(0, 100) });
app.loadAlbum(1, 0, false);
assert.equal(app.currentTrackIndex, 0);
assert(app.tracklistEl.querySelectorAll('.track-item').length <= 60);
app.loadAlbum(0, 78885, false);
assert(app.tracklistEl.querySelector('.track-item.active'));
app.loadTrack(0, false);
assert.equal(app.tracklistEl.querySelector('.track-item.active').dataset.index, '0');
assert(app.tracklistEl.querySelectorAll('.track-item').length <= 60, 'jumping backwards discards the old window');

// Page controls expose the rest of the queue without accumulating DOM nodes.
function pageButton(container, direction) {
    return container.children.find(child => child.dataset.direction === direction)?.querySelector('button');
}
for (let page = 0; page < 10; page++) {
    pageButton(app.tracklistEl, 'next').click();
    assert(app.tracklistEl.querySelectorAll('.track-item').length <= 60);
}
const laterStart = app.tracklistEl.querySelectorAll('.track-item')[0].dataset.index;
pageButton(app.tracklistEl, 'previous').click();
assert(Number(app.tracklistEl.querySelectorAll('.track-item')[0].dataset.index) < Number(laterStart));
assert.equal(app.currentTrackIndex, 0, 'browsing pages must not change playback');

app.renderTracklist('ngay con doi muoi');
assert.equal(app.modalTracklistEl.querySelectorAll('.track-item').length, 1, 'mobile list searches without Vietnamese accents');
assert.equal(app.modalTracklistEl.querySelectorAll('.track-item')[0].dataset.index, '77284');
assert(Number(app.tracklistEl.querySelectorAll('.track-item')[0].dataset.index) > 0, 'mobile search leaves the main list page intact');
app.renderTracklist('no such track');
assert.equal(app.modalTracklistEl.querySelectorAll('.track-item').length, 0);
app.renderTracklist('');
pageButton(app.modalTracklistEl, 'next').click();
assert.equal(app.modalTracklistEl.querySelectorAll('.track-item').length, 50);
app.renderTracklist('track 1');
pageButton(app.modalTracklistEl, 'next').click();
assert(app.modalTracklistEl.querySelectorAll('.track-item').length <= 50, 'filtered pages also stay bounded');
assert(app.modalTracklistEl.querySelectorAll('.track-item').every(row => tracks[Number(row.dataset.index)].name.toLowerCase().includes('track 1')));

// Album titles and song names are not unique; the clicked result's identity wins.
tracks[10].name = tracks[77284].name;
app.albums.unshift({ ...app.albums[0], id: 'same-title-other-album', tracks: tracks.slice(0, 5) });
app.invalidateLibraryIndex();
app.handleSearch('ngay con doi muoi');
const duplicates = app.searchResults.children.filter(child => child.classList.contains('search-item') && child.innerHTML.includes('MUSIC XTAPO'));
assert.equal(duplicates.length, 2);
duplicates.at(-1).click();
assert.equal(app.currentAlbum.id, 'large', 'duplicate album titles cannot redirect a search result');
assert.equal(app.currentTrack, tracks[77284], 'duplicate song names cannot redirect a search result');

// Admin sizes apply to both lists, including the minimum where fixed overscan would hide the selection.
for (const [desktopSize, mobileSize] of [[10, 10], [30, 20], [200, 100]]) {
    app.tracklistPageSize = desktopSize;
    app.mobileTracklistPageSize = mobileSize;
    app.loadAlbum(1, 77284, false);
    assert.equal(app.tracklistEl.querySelectorAll('.track-item').length, desktopSize);
    assert.equal(app.modalTracklistEl.querySelectorAll('.track-item').length, mobileSize);
    assert.equal(app.tracklistEl.querySelector('.track-item.active').dataset.index, '77284');
    assert.equal(app.modalTracklistEl.querySelector('.track-item.active').dataset.index, '77284');
    pageButton(app.tracklistEl, 'next').click();
    assert.equal(app.tracklistEl.querySelectorAll('.track-item').length, desktopSize);
    pageButton(app.modalTracklistEl, 'next').click();
    assert.equal(app.modalTracklistEl.querySelectorAll('.track-item').length, mobileSize);
}
app.tracklistPageSize = 100000;
app.mobileTracklistPageSize = 0;
app.loadAlbum(1, 77284, false);
assert.equal(app.tracklistEl.querySelectorAll('.track-item').length, 60, 'invalid server sizes cannot create an unbounded list');
assert.equal(app.modalTracklistEl.querySelectorAll('.track-item').length, 50);

context.window = { matchMedia: () => ({ matches: true }) };
app.tracklistPageSize = 30;
app.mobileTracklistPageSize = 20;
app.renderTracklist();
assert.equal(app.tracklistEl.querySelectorAll('.track-item').length, 20, 'phone layout applies the mobile size to the main list too');
assert.equal(app.modalTracklistEl.querySelectorAll('.track-item').length, 20);
delete context.window;

app.albums.push({ id: 'empty', title: 'Empty', tracks: [] });
app.loadAlbum(app.albums.length - 1, 100000, false);
assert.equal(app.currentTrackIndex, 0);
assert.equal(app.tracklistEl.querySelectorAll('.track-item').length, 0);
assert.equal(app.modalTracklistEl.querySelectorAll('.track-item').length, 0);

console.log('PASS: late search selection, bounded main/mobile lists, page navigation, backward jumps, and accent-tolerant filtering');

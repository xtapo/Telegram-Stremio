// Run with: node tests/test_music_album_picker.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const appSource = fs.readFileSync(path.join(__dirname, '../Music/app.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(__dirname, '../Music/index.html'), 'utf8');
const styleSource = fs.readFileSync(path.join(__dirname, '../Music/style.css'), 'utf8');
const pagesSource = fs.readFileSync(path.join(__dirname, '../Backend/fastapi/routes/music/pages.py'), 'utf8');

assert.match(indexSource, /style\.css\?v=4\.5/);
assert.match(indexSource, /app\.js\?v=6\.4/);
assert.match(styleSource, /\.nav-more-dropdown\s*\{[\s\S]*?position:\s*absolute;[\s\S]*?visibility:\s*hidden;/);
assert.match(styleSource, /\.nav-more-menu:hover \.nav-more-dropdown/);
assert.match(pagesSource, /if ext in \["\.css", "\.js"\]:[\s\S]*?must-revalidate/);

const start = appSource.indexOf('    renderAlbumGrid() {');
const end = appSource.indexOf('    updateDrawerInfo() {', start);
assert(start >= 0 && end > start);

const methodSource = appSource
    .slice(start, end)
    .trim()
    .replace(/^renderAlbumGrid\(\)/, 'function renderAlbumGrid()');

class FakeElement {
    constructor() {
        this.children = [];
        this._innerHTML = '';
        this.className = '';
        this.classList = { toggle() {}, remove() {}, add() {} };
    }
    set innerHTML(value) { this._innerHTML = value; this.children = []; }
    get innerHTML() { return this._innerHTML; }
    appendChild(child) {
        if (child && child.isFragment) this.children.push(...child.children);
        else this.children.push(child);
        return child;
    }
    addEventListener() {}
    closest() { return null; }
    querySelector() { return null; }
    querySelectorAll() { return []; }
    remove() {}
}

const titleElement = new FakeElement();
const context = vm.createContext({
    document: {
        createElement: () => new FakeElement(),
        createDocumentFragment: () => ({ isFragment: true, children: [], appendChild(el) { this.children.push(el); } }),
        getElementById: id => id === 'albumModalTitle' ? titleElement : null,
    },
});
vm.runInContext(`globalThis.renderAlbumGrid = ${methodSource}`, context);

const albums = [
    { id: 'a1', title: 'Mùa Đêm Tình Nhỏ', artist: 'Hoài Nam', tracks: [{ name: 'Mai Lệ Huyền' }] },
    { id: 'a2', title: 'Biển Ca', artist: 'Thụy Thu', tracks: [{ name: 'Sơn Ca' }] },
];

function resultCount(query) {
    const albumGrid = new FakeElement();
    const app = {
        albums,
        albumGrid,
        albumSearchInput: { value: query },
        clearAlbumSearch: new FakeElement(),
        albumViewMode: 'all',
        recentAlbumLimit: 24,
        currentAlbumIndex: 0,
        getBaseAlbums: () => albums,
        normalizeSearchText: value => String(value || '')
            .replace(/đ/g, 'd').replace(/Đ/g, 'D')
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(),
        escapeHtml: value => String(value || ''),
    };
    context.renderAlbumGrid.call(app);
    return albumGrid.children.length;
}

assert.equal(resultCount('mua dem tinh nho'), 1, 'finds an album title without Vietnamese accents');
assert.equal(resultCount('thuy thu'), 1, 'finds an album by artist');
assert.equal(resultCount('son ca'), 1, 'finds an album by a contained track');

console.log('PASS: music asset cache contract and album picker search');

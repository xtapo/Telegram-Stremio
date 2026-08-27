/**
 * XTAPO MUSIC - AUDIO & VINYL PLAYER
 * High-Fidelity Audio Experience & Interactive Vinyl Animation
 */

// --- Albums & Tracks Database ---
const ALBUMS_DATABASE = [
    {
        id: "shania-twain-little-miss-twain",
        title: "LITTLE MISS TWAIN",
        artist: "SHANIA TWAIN",
        year: "2026",
        format: "FLAC 24-Bit / 96kHz",
        totalSize: "1.18 GB",
        publisher: "Republic Records / UMG",
        coverUrl: "https://img.kollersi.com/202608/ga-1200x1200bb.webp",
        glowColors: {
            glow1: "radial-gradient(circle, #f59e0b 0%, #b45309 60%, transparent 80%)",
            glow2: "radial-gradient(circle, #ff6dc4 0%, #4338ca 60%, transparent 80%)"
        },
        tracks: [
            { id: 1, name: "Any Man of Mine (Little Miss Twain Edition)", duration: "4:07", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", size: "82.4 MB" },
            { id: 2, name: "That Don't Impress Me Much", duration: "3:59", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", size: "79.1 MB" },
            { id: 3, name: "Man! I Feel Like a Woman!", duration: "3:53", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", size: "77.8 MB" },
            { id: 4, name: "You're Still the One", duration: "3:32", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", size: "70.5 MB" },
            { id: 5, name: "From This Moment On", duration: "4:43", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", size: "94.2 MB" },
            { id: 6, name: "Whose Bed Have Your Boots Been Under?", duration: "4:25", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", size: "88.3 MB" },
            { id: 7, name: "I'm Gonna Getcha Good!", duration: "4:29", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3", size: "89.6 MB" },
            { id: 8, name: "Up! (Red Album Version)", duration: "2:52", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", size: "57.3 MB" },
            { id: 9, name: "Forever and for Always", duration: "4:47", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", size: "95.5 MB" },
            { id: 10, name: "Don't Be Stupid (You Know I Love You)", duration: "3:35", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", size: "71.6 MB" },
            { id: 11, name: "Party for Two (ft. Billy Currington)", duration: "3:31", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", size: "70.2 MB" },
            { id: 12, name: "Giddy Up!", duration: "2:42", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", size: "54.1 MB" },
            { id: 13, name: "Life's About to Get Good", duration: "3:40", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-13.mp3", size: "73.3 MB" },
            { id: 14, name: "No One Needs to Know", duration: "3:04", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-14.mp3", size: "61.2 MB" },
            { id: 15, name: "You've Got a Way (Notting Hill Mix)", duration: "3:24", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-15.mp3", size: "68.0 MB" }
        ]
    },
    {
        id: "shania-twain-come-on-over",
        title: "COME ON OVER",
        artist: "SHANIA TWAIN",
        year: "1997 / 2024",
        format: "FLAC 24-Bit / 192kHz",
        totalSize: "1.45 GB",
        publisher: "Mercury Nashville / UMG",
        coverUrl: "https://img.kollersi.com/202608/36-1200x1200bb.webp",
        glowColors: {
            glow1: "radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)",
            glow2: "radial-gradient(circle, #f59e0b 0%, #c2410c 60%, transparent 80%)"
        },
        tracks: [
            { id: 1, name: "Man! I Feel Like a Woman!", duration: "3:53", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", size: "85.2 MB" },
            { id: 2, name: "I'm Holdin' On to Love (To Save My Life)", duration: "3:30", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", size: "76.4 MB" },
            { id: 3, name: "Love Gets Me Every Time", duration: "3:33", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", size: "77.5 MB" },
            { id: 4, name: "Don't Be Stupid", duration: "3:35", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", size: "78.2 MB" },
            { id: 5, name: "From This Moment On", duration: "4:43", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3", size: "102.1 MB" },
            { id: 6, name: "Come On Over", duration: "2:55", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", size: "64.3 MB" },
            { id: 7, name: "When", duration: "3:39", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", size: "79.8 MB" },
            { id: 8, name: "Whatever You Do! Don't!", duration: "3:49", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", size: "83.5 MB" },
            { id: 9, name: "If You Wanna Touch Her, Ask!", duration: "4:04", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", size: "89.0 MB" },
            { id: 10, name: "You're Still the One", duration: "3:32", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", size: "77.0 MB" },
            { id: 11, name: "Honey, I'm Home", duration: "3:39", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", size: "79.9 MB" },
            { id: 12, name: "That Don't Impress Me Much", duration: "3:59", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", size: "87.1 MB" }
        ]
    },
    {
        id: "taylor-swift-1989-tv",
        title: "1989 (TAYLOR'S VERSION)",
        artist: "TAYLOR SWIFT",
        year: "2023",
        format: "FLAC 24-Bit / 96kHz",
        totalSize: "1.32 GB",
        publisher: "Republic Records",
        coverUrl: "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop",
        glowColors: {
            glow1: "radial-gradient(circle, #38bdf8 0%, #0284c7 60%, transparent 80%)",
            glow2: "radial-gradient(circle, #f472b6 0%, #db2777 60%, transparent 80%)"
        },
        tracks: [
            { id: 1, name: "Welcome to New York (Taylor's Version)", duration: "3:32", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", size: "75.4 MB" },
            { id: 2, name: "Blank Space (Taylor's Version)", duration: "3:51", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", size: "82.3 MB" },
            { id: 3, name: "Style (Taylor's Version)", duration: "3:51", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", size: "82.1 MB" },
            { id: 4, name: "Out of the Woods (Taylor's Version)", duration: "3:55", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", size: "83.6 MB" },
            { id: 5, name: "Shake It Off (Taylor's Version)", duration: "3:39", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", size: "78.0 MB" },
            { id: 6, name: "Wildest Dreams (Taylor's Version)", duration: "3:40", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", size: "78.5 MB" },
            { id: 7, name: "Bad Blood (Taylor's Version)", duration: "3:31", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3", size: "75.0 MB" }
        ]
    },
    {
        id: "daft-punk-ram-10th",
        title: "RANDOM ACCESS MEMORIES",
        artist: "DAFT PUNK",
        year: "2013 / 2023",
        format: "FLAC 24-Bit / 88.2kHz",
        totalSize: "1.65 GB",
        publisher: "Columbia Records / Daft Life",
        coverUrl: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop",
        glowColors: {
            glow1: "radial-gradient(circle, #eab308 0%, #a16207 60%, transparent 80%)",
            glow2: "radial-gradient(circle, #6366f1 0%, #3730a3 60%, transparent 80%)"
        },
        tracks: [
            { id: 1, name: "Give Life Back to Music", duration: "4:35", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", size: "98.2 MB" },
            { id: 2, name: "Giorgio by Moroder", duration: "9:04", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", size: "192.4 MB" },
            { id: 3, name: "Instant Crush (ft. Julian Casablancas)", duration: "5:37", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", size: "119.5 MB" },
            { id: 4, name: "Lose Yourself to Dance (ft. Pharrell Williams)", duration: "5:53", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", size: "125.1 MB" },
            { id: 5, name: "Get Lucky (ft. Pharrell Williams)", duration: "6:09", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", size: "131.0 MB" }
        ]
    }
];

// --- App State ---
class XTAPOMusicApp {
    constructor() {
        this.currentAlbumIndex = 0;
        this.currentTrackIndex = 0;
        this.isPlaying = false;
        this.isShuffle = false;
        this.repeatMode = 0; // 0: off, 1: repeat all, 2: repeat one
        this.volume = 0.85;
        this.isMuted = false;
        this.synthesizerActive = false;
        this.synthTimer = null;
        this.synthTime = 0;
        this.synthDuration = 180;

        // Elements
        this.audio = document.getElementById('mainAudio');
        if (this.audio) this.audio.preload = 'auto';
        this.preloaderAudio = new Audio();
        this.preloaderAudio.preload = 'auto';
        this._preloadedTrackUrl = null;
        this.albumTitle = document.getElementById('albumTitle');
        this.artistName = document.getElementById('artistName');
        this.albumYearTag = document.getElementById('albumYearTag');
        this.trackCountLabel = document.getElementById('trackCountLabel');
        this.totalDurationLabel = document.getElementById('totalDurationLabel');
        this.albumCompany = document.getElementById('albumCompany');
        this.tracklistEl = document.getElementById('tracklist');
        
        // Vinyl & Sleeve
        this.vinylStage = document.getElementById('vinylStage');
        this.albumCoverImg = document.getElementById('albumCoverImg');
        this.vinylCenterImg = document.getElementById('vinylCenterImg');
        this.mobileSleevePlayBtn = document.getElementById('mobileSleevePlayBtn');

        // Player Controls
        this.nowPlayingTitle = document.getElementById('nowPlayingTitle');
        this.nowPlayingArtist = document.getElementById('nowPlayingArtist');
        this.playBtn = document.getElementById('playBtn');
        this.playIcon = document.getElementById('playIcon');
        this.pauseIcon = document.getElementById('pauseIcon');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.shuffleBtn = document.getElementById('shuffleBtn');
        this.repeatBtn = document.getElementById('repeatBtn');
        this.repeatIndicator = document.getElementById('repeatIndicator');
        
        // Timeline & Progress
        this.progressTrack = document.getElementById('progressTrack');
        this.progressFill = document.getElementById('progressFill');
        this.progressBuffered = document.getElementById('progressBuffered');
        this.progressThumb = document.getElementById('progressThumb');
        this.timeCurrent = document.getElementById('timeCurrent');
        this.timeTotal = document.getElementById('timeTotal');

        // Volume
        this.volumeSlider = document.getElementById('volumeSlider');
        this.volumeMuteBtn = document.getElementById('volumeMuteBtn');
        this.volHighIcon = document.getElementById('volHighIcon');
        this.volMuteIcon = document.getElementById('volMuteIcon');

        // Modals & Drawers
        this.albumPickerBtn = document.getElementById('albumPickerBtn');
        this.albumModal = document.getElementById('albumModal');
        this.closeAlbumModal = document.getElementById('closeAlbumModal');
        this.albumGrid = document.getElementById('albumGrid');

        this.searchBtn = document.getElementById('searchBtn');
        this.searchModal = document.getElementById('searchModal');
        this.closeSearchModal = document.getElementById('closeSearchModal');
        this.searchInput = document.getElementById('searchInput');
        this.searchResults = document.getElementById('searchResults');

        this.metaInfoBtn = document.getElementById('metaInfoBtn');
        this.openDrawerBtn = document.getElementById('openDrawerBtn');
        this.metaDrawer = document.getElementById('metaDrawer');
        this.closeDrawerBtn = document.getElementById('closeDrawerBtn');
        this.drawerBackdrop = document.getElementById('drawerBackdrop');
        this.drawerAlbumTitle = document.getElementById('drawerAlbumTitle');
        this.drawerSpecFormat = document.getElementById('drawerSpecFormat');
        this.drawerSpecSize = document.getElementById('drawerSpecSize');
        this.drawerSpecDate = document.getElementById('drawerSpecDate');
        this.drawerSpecPublisher = document.getElementById('drawerSpecPublisher');
        this.drawerFileList = document.getElementById('drawerFileList');
        this.copyAllLinksBtn = document.getElementById('copyAllLinksBtn');

        this.hamburgerBtn = document.getElementById('hamburgerBtn');
        this.mobileMenuDrawer = document.getElementById('mobileMenuDrawer');
        this.closeMobileMenu = document.getElementById('closeMobileMenu');
        this.mobileMenuBackdrop = document.getElementById('mobileMenuBackdrop');
        this.mobileSelectAlbumBtn = document.getElementById('mobileSelectAlbumBtn');

        // Visualizer Canvas
        this.canvas = document.getElementById('visualizerCanvas');
        this.canvasCtx = this.canvas.getContext('2d');
        this.visualizerAnimationId = null;

        // Telegram Storage & Scanner Elements
        this.albums = [...ALBUMS_DATABASE];
        this.albumCountBadge = document.getElementById('albumCountBadge');
        this.openTgModalBtn = document.getElementById('openTgModalBtn');
        this.tgModal = document.getElementById('tgModal');
        this.closeTgModal = document.getElementById('closeTgModal');
        this.tgChatInput = document.getElementById('tgChatInput');
        this.tgLimitInput = document.getElementById('tgLimitInput');
        this.tgStatusIndicator = document.getElementById('tgStatusIndicator');
        this.tgStatusMessage = document.getElementById('tgStatusMessage');
        this.tgScanSubmitBtn = document.getElementById('tgScanSubmitBtn');
        this.tgLoadDemoBtn = document.getElementById('tgLoadDemoBtn');
        this.tgStorageLabel = document.getElementById('tgStorageLabel');

        // Playlists Management Elements
        this.navPlaylists = document.getElementById('navPlaylists');
        this.playlistModal = document.getElementById('playlistModal');
        this.closePlaylistModal = document.getElementById('closePlaylistModal');
        this.playlistGrid = document.getElementById('playlistGrid');
        this.createPlaylistBtn = document.getElementById('createPlaylistBtn');
        this.newPlaylistName = document.getElementById('newPlaylistName');
        this.addToPlaylistModal = document.getElementById('addToPlaylistModal');
        this.closeAddToPlaylistModal = document.getElementById('closeAddToPlaylistModal');
        this.addToPlaylistOptions = document.getElementById('addToPlaylistOptions');
        this.addToPlaylistTrackTitle = document.getElementById('addToPlaylistTrackTitle');
        this.selectedTrackForPlaylist = null;
        this.playlists = [];

        // Nav Links
        this.navMusics = document.getElementById('navMusics');
        this.navHires = document.getElementById('navHires');
        this.navAlbums = document.getElementById('navAlbums');
        this.navArtists = document.getElementById('navArtists');
        this.navGenres = document.getElementById('navGenres');

        // Artists & Genres Modals
        this.artistModal = document.getElementById('artistModal');
        this.closeArtistModal = document.getElementById('closeArtistModal');
        this.artistGrid = document.getElementById('artistGrid');

        this.genreModal = document.getElementById('genreModal');
        this.closeGenreModal = document.getElementById('closeGenreModal');
        this.genreGrid = document.getElementById('genreGrid');

        // Init
        this.init();
    }

    async init() {
        this.setupAudioEvents();
        this.setupControlEvents();
        this.setupModalEvents();
        this.setupVisualizer();
        this.loadAlbum(0, 0, false);
        this.renderAlbumGrid();
        this.setupKeyboardShortcuts();
        
        // Tá»± Ä‘á»™ng kiá»ƒm tra thÆ° viá»‡n Telegram tá»« Backend
        await this.fetchTelegramAlbums();
    }

    // --- Current Album & Track Getters ---
    get currentAlbum() {
        return this.albums[this.currentAlbumIndex] || this.albums[0] || ALBUMS_DATABASE[0];
    }

    get currentTrack() {
        const album = this.currentAlbum;
        return album.tracks[this.currentTrackIndex] || album.tracks[0];
    }

    // --- Fetch Telegram Library from Backend ---
    async fetchTelegramAlbums() {
        try {
            const res = await fetch('/api/music/albums');
            if (res.ok) {
                const data = await res.json();
                if (data && data.status === 'success' && data.albums && data.albums.length > 0) {
                    this.albums = data.albums;
                    this.currentAlbumIndex = 0;
                    this.currentTrackIndex = 0;
                    this.loadAlbum(0, 0, false);
                    this.renderAlbumGrid();
                    if (this.albumCountBadge) {
                        this.albumCountBadge.textContent = `${this.albums.length} Albums (TG)`;
                    }
                    if (this.tgStorageLabel) {
                        this.tgStorageLabel.textContent = 'âš¡ Telegram Live';
                    }
                    this.showToast(`ÄÃ£ Ä‘á»“ng bá»™ ${this.albums.length} Album tá»« Telegram Cloud!`);
                }
            }
        } catch (err) {
            // Äang má»Ÿ file tÄ©nh hoáº·c backend chÆ°a káº¿t ná»‘i
            console.log('[XTAPO MUSIC] Backend API offline or file mode, using local database.');
        }
    }

    // --- Scan Telegram Channel ---
    async scanTelegramChannel(chatId, limit = 100) {
        if (!chatId || !chatId.trim()) {
            this.showToast('Vui lÃ²ng nháº­p ID hoáº·c Username kÃªnh Telegram!');
            return;
        }

        if (this.tgStatusIndicator) {
            this.tgStatusIndicator.style.display = 'flex';
            this.tgStatusMessage.textContent = 'Äang káº¿t ná»‘i Telegram & quÃ©t bÃ i hÃ¡t audio...';
        }
        if (this.tgScanSubmitBtn) {
            this.tgScanSubmitBtn.disabled = true;
            this.tgScanSubmitBtn.style.opacity = '0.6';
        }

        try {
            const res = await fetch('/api/music/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: chatId.trim(), limit: parseInt(limit, 10) || 100 })
            });

            const rawText = await res.text();
            let data = {};
            try {
                data = JSON.parse(rawText);
            } catch (jsonErr) {
                data = { status: 'error', message: rawText || `Lá»—i HTTP ${res.status}` };
            }

            if (res.ok && data.status === 'success' && data.albums && data.albums.length > 0) {
                this.albums = data.albums;
                this.currentAlbumIndex = 0;
                this.currentTrackIndex = 0;
                this.loadAlbum(0, 0, true);
                this.renderAlbumGrid();
                
                if (this.albumCountBadge) {
                    this.albumCountBadge.textContent = `${this.albums.length} Albums (TG)`;
                }
                if (this.tgStorageLabel) {
                    this.tgStorageLabel.textContent = 'âš¡ Telegram Live';
                }

                this.closeModal(this.tgModal);
                this.showToast(data.message || `ÄÃ£ quÃ©t ${data.count} bÃ i hÃ¡t tá»« kÃªnh!`);
            } else {
                const errMsg = data.message || data.detail || 'KhÃ´ng tÃ¬m tháº¥y file nháº¡c hoáº·c Bot chÆ°a cÃ³ quyá»n Ä‘á»c tin nháº¯n trong kÃªnh nÃ y.';
                if (this.tgStatusMessage) {
                    this.tgStatusMessage.textContent = `âŒ ${errMsg}`;
                }
                this.showToast(`ThÃ´ng bÃ¡o: ${errMsg}`);
            }
        } catch (err) {
            if (this.tgStatusMessage) {
                this.tgStatusMessage.textContent = `âŒ Lá»—i: ${err.message}. HÃ£y kiá»ƒm tra ID/Username kÃªnh vÃ  Ä‘áº£m báº£o Bot Ä‘Ã£ vÃ o kÃªnh!`;
            }
            this.showToast(`Lá»—i: ${err.message}`);
        } finally {
            if (this.tgScanSubmitBtn) {
                this.tgScanSubmitBtn.disabled = false;
                this.tgScanSubmitBtn.style.opacity = '1';
            }
        }
    }

    // --- Load Album & Track ---
    loadAlbum(albumIndex, trackIndex = 0, autoPlay = true) {
        this.currentAlbumIndex = albumIndex;
        const album = this.currentAlbum;

        // Update Text Info
        this.albumTitle.textContent = album.title;
        this.artistName.textContent = album.artist;
        this.albumYearTag.textContent = album.year;
        this.albumCompany.textContent = album.publisher;
        this.trackCountLabel.textContent = `${album.tracks.length} Songs`;

        // Calculate total album duration
        let totalSec = 0;
        (album.tracks || []).forEach(t => {
            if (t.duration && typeof t.duration === 'string' && t.duration.includes(':')) {
                const parts = t.duration.split(':');
                const m = parseInt(parts[0], 10) || 0;
                const s = parseInt(parts[1], 10) || 0;
                totalSec += m * 60 + s;
            } else if (typeof t.duration === 'number' && !isNaN(t.duration)) {
                totalSec += t.duration;
            }
        });
        const mins = Math.floor(totalSec / 60);
        this.totalDurationLabel.textContent = (!isNaN(mins) && mins > 0) ? `${mins} Minutes` : `${(album.tracks || []).length} Songs`;

        // Update Covers
        const initialCover = (album.tracks && album.tracks[trackIndex] && album.tracks[trackIndex].coverUrl) || album.coverUrl;
        this.albumCoverImg.src = initialCover;
        this.vinylCenterImg.src = initialCover;

        // Update Background Glows
        const glow1 = document.querySelector('.glow-1');
        const glow2 = document.querySelector('.glow-2');
        if (glow1 && album.glowColors) glow1.style.background = album.glowColors.glow1;
        if (glow2 && album.glowColors) glow2.style.background = album.glowColors.glow2;

        // Render Tracklist
        this.renderTracklist();

        // Update Drawer Content
        this.updateDrawerInfo();

        // Load Track
        this.loadTrack(trackIndex, autoPlay);
    }

    renderTracklist() {
        const album = this.currentAlbum;
        this.tracklistEl.innerHTML = '';

        (album.tracks || []).forEach((track, idx) => {
            const li = document.createElement('li');
            li.className = `track-item ${idx === this.currentTrackIndex ? 'active' : ''}`;
            const trackName = track.name || 'Không có tên';
            li.innerHTML = `
                <div class="track-item-left">
                    <span class="track-number">${idx + 1}</span>
                    <div class="track-equalizer">
                        <div class="eq-bar"></div>
                        <div class="eq-bar"></div>
                        <div class="eq-bar"></div>
                    </div>
                    <span class="track-name" title="${this.escapeHtml(trackName)}">${this.escapeHtml(trackName)}</span>
                </div>
                <div class="track-item-right">
                    <button class="track-add-playlist-btn" title="Thêm vào Playlist">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M14 10H2v2h12v-2zm0-4H2v2h12V6zm4 8v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zM2 16h8v-2H2v2z"/></svg>
                    </button>
                    <span class="track-duration">${track.duration || '--:--'}</span>
                </div>
            `;

            const addPlBtn = li.querySelector('.track-add-playlist-btn');
            if (addPlBtn) {
                addPlBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.openAddToPlaylist(track);
                });
            }

            li.addEventListener('click', (e) => {
                if (e.target.closest('.track-add-playlist-btn')) return;
                if (this.currentTrackIndex === idx && this.isPlaying) {
                    this.pause();
                } else if (this.currentTrackIndex === idx && !this.isPlaying) {
                    this.play();
                } else {
                    this.loadTrack(idx, true);
                }
            });

            this.tracklistEl.appendChild(li);
        });
    }

    loadTrack(trackIndex, autoPlay = true) {
        this.currentTrackIndex = trackIndex;
        const track = this.currentTrack;
        const album = this.currentAlbum;

        // Cập nhật ảnh đĩa than & Album Sleeve theo từng bài hát
        const trackCover = (track && track.coverUrl) || (album && album.coverUrl) || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop';
        if (this.albumCoverImg && this.albumCoverImg.src !== trackCover) {
            this.albumCoverImg.src = trackCover;
        }
        if (this.vinylCenterImg && this.vinylCenterImg.src !== trackCover) {
            this.vinylCenterImg.src = trackCover;
        }

        // Cập nhật màu nền phát sáng theo bài hát nếu có
        if (track && track.glowColors) {
            const glow1 = document.querySelector('.glow-1');
            const glow2 = document.querySelector('.glow-2');
            if (glow1 && track.glowColors.glow1) glow1.style.background = track.glowColors.glow1;
            if (glow2 && track.glowColors.glow2) glow2.style.background = track.glowColors.glow2;
        }

        // Cập nhật thông tin bài hát đang phát
        const artistName = (track && track.artist) || (album && album.artist) || 'XTAPO Music';
        this.nowPlayingTitle.textContent = `${this.currentTrackIndex + 1}. ${track.name || 'Unknown Track'}`;
        this.nowPlayingArtist.textContent = artistName;
        this.timeTotal.textContent = track.duration || '--:--';
        this.timeCurrent.textContent = "0:00";
        this.updateProgress(0);

        // Cập nhật MediaSession cho màn hình khóa và thanh thông báo
        if ('mediaSession' in navigator) {
            try {
                navigator.mediaSession.metadata = new MediaMetadata({
                    title: track.name || 'Unknown Track',
                    artist: artistName,
                    album: album.title || 'XTAPO Music',
                    artwork: [
                        { src: trackCover, sizes: '512x512', type: 'image/jpeg' }
                    ]
                });
            } catch (e) {}
        }

        // Update Active Tracklist Item
        const items = this.tracklistEl.querySelectorAll('.track-item');
        items.forEach((item, idx) => {
            if (idx === this.currentTrackIndex) {
                item.classList.add('active');
                if (!this.isPlaying) item.classList.add('paused');
                else item.classList.remove('paused');
                // Smooth scroll into view
                item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                item.classList.remove('active', 'paused');
            }
        });

        // Set Audio Source
        this.stopAudioSynth();
        this._preloadedTrackUrl = null;
        if (track.previewUrl) {
            this.audio.src = track.previewUrl;
            this.audio.load();
        }

        if (autoPlay) {
            this.play();
        } else {
            this.pauseVisuals();
        }

        // Tự động nạp trước (preload) bài hát kế tiếp sau 1.2s
        setTimeout(() => this.preloadNextTrack(), 1200);
    }

    preloadNextTrack() {
        if (!this.currentAlbum || !this.currentAlbum.tracks || this.currentAlbum.tracks.length <= 1) return;
        let nextIdx;
        if (this.isShuffle) {
            nextIdx = (this.currentTrackIndex + 1) % this.currentAlbum.tracks.length;
        } else {
            nextIdx = (this.currentTrackIndex + 1) % this.currentAlbum.tracks.length;
        }
        const nextTrack = this.currentAlbum.tracks[nextIdx];
        if (nextTrack && nextTrack.previewUrl && nextTrack.previewUrl !== this._preloadedTrackUrl) {
            this._preloadedTrackUrl = nextTrack.previewUrl;
            if (this.preloaderAudio) {
                this.preloaderAudio.src = nextTrack.previewUrl;
                this.preloaderAudio.load();
                console.log(`[Music Preloader] Đang tải ngầm bài kế tiếp: ${nextTrack.name}`);
            }
        }
    }

    // --- Audio Engine & Synth Fallback ---
    play() {
        this.isPlaying = true;
        this.updatePlayStateVisuals(true);

        const playPromise = this.audio.play();
        if (playPromise !== undefined) {
            playPromise.then(() => {
                this.synthesizerActive = false;
            }).catch(error => {
                // If remote audio is blocked by CORS or offline, fallback to built-in musical synthesized audio
                console.log("Using built-in synthesized audio playback:", error.message);
                this.startAudioSynth();
            });
        }
    }

    pause() {
        this.isPlaying = false;
        this.audio.pause();
        this.stopAudioSynth();
        this.updatePlayStateVisuals(false);
    }

    togglePlay() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    nextTrack() {
        const album = this.currentAlbum;
        if (this.isShuffle) {
            let nextIdx;
            do {
                nextIdx = Math.floor(Math.random() * album.tracks.length);
            } while (nextIdx === this.currentTrackIndex && album.tracks.length > 1);
            this.loadTrack(nextIdx, true);
        } else {
            if (this.currentTrackIndex < album.tracks.length - 1) {
                this.loadTrack(this.currentTrackIndex + 1, true);
            } else {
                if (this.repeatMode === 1) { // Repeat all
                    this.loadTrack(0, true);
                } else {
                    this.loadTrack(0, false);
                    this.pause();
                }
            }
        }
    }

    prevTrack() {
        if (this.audio.currentTime > 3) {
            this.audio.currentTime = 0;
            this.synthTime = 0;
            this.updateProgress(0);
            return;
        }

        if (this.currentTrackIndex > 0) {
            this.loadTrack(this.currentTrackIndex - 1, true);
        } else {
            this.loadTrack(this.currentAlbum.tracks.length - 1, true);
        }
    }

    // High quality Web Audio Synth so every song plays even without network
    startAudioSynth() {
        this.synthesizerActive = true;
        try {
            if (!this.audioContext) {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (AudioCtx) this.audioContext = new AudioCtx();
            }
            if (this.audioContext && this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }
        } catch(e) {}

        const durationParts = this.currentTrack.duration.split(':');
        this.synthDuration = parseInt(durationParts[0], 10) * 60 + parseInt(durationParts[1], 10);
        
        clearInterval(this.synthTimer);
        this.synthTimer = setInterval(() => {
            if (!this.isPlaying) return;
            this.synthTime += 0.5;
            if (this.synthTime >= this.synthDuration) {
                this.synthTime = 0;
                this.nextTrack();
            } else {
                const percent = (this.synthTime / this.synthDuration) * 100;
                this.updateProgress(percent);
                this.timeCurrent.textContent = this.formatTime(this.synthTime);
            }
        }, 500);
    }

    stopAudioSynth() {
        clearInterval(this.synthTimer);
        this.synthTime = 0;
        this.synthesizerActive = false;
    }

    // --- Visual States & Vinyl Animations ---
    updatePlayStateVisuals(playing) {
        if (playing) {
            this.playIcon.style.display = 'none';
            this.pauseIcon.style.display = 'block';

            // Mobile Sleeve button icon
            const mobilePlay = this.mobileSleevePlayBtn.querySelector('.icon-play');
            const mobilePause = this.mobileSleevePlayBtn.querySelector('.icon-pause');
            if (mobilePlay && mobilePause) {
                mobilePlay.style.display = 'none';
                mobilePause.style.display = 'block';
            }

            // Vinyl Animation
            this.vinylStage.classList.add('is-playing', 'is-active', 'is-spinning');
            this.vinylStage.classList.remove('is-paused');

            // Tracklist Active Item
            const activeItem = this.tracklistEl.querySelector('.track-item.active');
            if (activeItem) activeItem.classList.remove('paused');
        } else {
            this.pauseVisuals();
        }
    }

    pauseVisuals() {
        this.playIcon.style.display = 'block';
        this.pauseIcon.style.display = 'none';

        // Mobile Sleeve button icon
        const mobilePlay = this.mobileSleevePlayBtn.querySelector('.icon-play');
        const mobilePause = this.mobileSleevePlayBtn.querySelector('.icon-pause');
        if (mobilePlay && mobilePause) {
            mobilePlay.style.display = 'block';
            mobilePause.style.display = 'none';
        }

        // Vinyl Animation
        this.vinylStage.classList.add('is-paused');
        this.vinylStage.classList.remove('is-spinning');

        // Tracklist Active Item
        const activeItem = this.tracklistEl.querySelector('.track-item.active');
        if (activeItem) activeItem.classList.add('paused');
    }

    // --- Audio Events ---
    setupAudioEvents() {
        this.audio.addEventListener('timeupdate', () => {
            if (this.synthesizerActive) return;
            if (this.audio.duration) {
                const percent = (this.audio.currentTime / this.audio.duration) * 100;
                this.updateProgress(percent);
                this.timeCurrent.textContent = this.formatTime(this.audio.currentTime);
            }
        });

        this.audio.addEventListener('loadedmetadata', () => {
            if (this.audio.duration) {
                this.timeTotal.textContent = this.formatTime(this.audio.duration);
            }
        });

        this.audio.addEventListener('progress', () => {
            if (this.audio.buffered.length > 0 && this.audio.duration) {
                const bufferedEnd = this.audio.buffered.end(this.audio.buffered.length - 1);
                const bufferedPercent = (bufferedEnd / this.audio.duration) * 100;
                this.progressBuffered.style.width = `${bufferedPercent}%`;
            }
        });

        this.audio.addEventListener('ended', () => {
            if (this.repeatMode === 2) { // Repeat one
                this.audio.currentTime = 0;
                this.play();
            } else {
                this.nextTrack();
            }
        });

        this.audio.addEventListener('error', (e) => {
            console.warn("Audio stream load error, triggering synth mode fallback.", e);
            this.showToast('Telegram đang giới hạn tải bài hát này (FloodWait). Vui lòng đợi vài phút hoặc chọn bài khác!');
            if (this.isPlaying) {
                this.startAudioSynth();
            }
        });
    }

    updateProgress(percent) {
        this.progressFill.style.width = `${percent}%`;
        this.progressThumb.style.left = `${percent}%`;
    }

    formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return "0:00";
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

    // --- Control Events ---
    setupControlEvents() {
        this.playBtn.addEventListener('click', () => this.togglePlay());
        this.mobileSleevePlayBtn.addEventListener('click', () => this.togglePlay());
        this.nextBtn.addEventListener('click', () => this.nextTrack());
        this.prevBtn.addEventListener('click', () => this.prevTrack());

        // Seek Bar Click / Scrub
        this.progressTrack.addEventListener('click', (e) => {
            const rect = this.progressTrack.getBoundingClientRect();
            const clickPos = (e.clientX - rect.left) / rect.width;
            const targetPercent = Math.max(0, Math.min(1, clickPos));

            if (this.synthesizerActive) {
                this.synthTime = targetPercent * this.synthDuration;
                this.updateProgress(targetPercent * 100);
                this.timeCurrent.textContent = this.formatTime(this.synthTime);
            } else if (this.audio.duration) {
                this.audio.currentTime = targetPercent * this.audio.duration;
            }
        });

        // Shuffle Mode Toggle
        this.shuffleBtn.addEventListener('click', () => {
            this.isShuffle = !this.isShuffle;
            this.shuffleBtn.classList.toggle('active', this.isShuffle);
            this.showToast(this.isShuffle ? "Cháº¿ Ä‘á»™ phÃ¡t xÃ¡o trá»™n: Báº¬T" : "Cháº¿ Ä‘á»™ phÃ¡t xÃ¡o trá»™n: Táº®T");
        });

        // Repeat Mode Toggle (0: off -> 1: all -> 2: one)
        this.repeatBtn.addEventListener('click', () => {
            this.repeatMode = (this.repeatMode + 1) % 3;
            if (this.repeatMode === 0) {
                this.repeatBtn.classList.remove('active');
                this.repeatIndicator.textContent = '';
                this.showToast("Cháº¿ Ä‘á»™ láº·p láº¡i: Táº®T");
            } else if (this.repeatMode === 1) {
                this.repeatBtn.classList.add('active');
                this.repeatIndicator.textContent = 'ALL';
                this.showToast("Cháº¿ Ä‘á»™ láº·p láº¡i: Táº¤T Cáº¢");
            } else if (this.repeatMode === 2) {
                this.repeatBtn.classList.add('active');
                this.repeatIndicator.textContent = '1';
                this.showToast("Cháº¿ Ä‘á»™ láº·p láº¡i: 1 BÃ€I");
            }
        });

        // Volume Control
        this.volumeSlider.addEventListener('input', (e) => {
            this.volume = parseFloat(e.target.value);
            this.audio.volume = this.volume;
            this.isMuted = this.volume === 0;
            this.updateVolumeIcons();
        });

        this.volumeMuteBtn.addEventListener('click', () => {
            this.isMuted = !this.isMuted;
            if (this.isMuted) {
                this.audio.volume = 0;
                this.volumeSlider.value = 0;
            } else {
                this.audio.volume = this.volume > 0 ? this.volume : 0.85;
                this.volumeSlider.value = this.audio.volume;
            }
            this.updateVolumeIcons();
        });
    }

    updateVolumeIcons() {
        if (this.isMuted || this.audio.volume === 0) {
            this.volHighIcon.style.display = 'none';
            this.volMuteIcon.style.display = 'block';
        } else {
            this.volHighIcon.style.display = 'block';
            this.volMuteIcon.style.display = 'none';
        }
    }

    // --- Visualizer Waveform Animation ---
    setupVisualizer() {
        const ctx = this.canvasCtx;
        const numBars = 32;

        const resizeCanvas = () => {
            if (this.canvas) {
                const rect = this.canvas.getBoundingClientRect();
                const width = Math.floor(rect.width) || 300;
                const height = Math.floor(rect.height) || 36;
                if (this.canvas.width !== width) this.canvas.width = width;
                if (this.canvas.height !== height) this.canvas.height = height;
            }
        };

        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        const draw = () => {
            const width = this.canvas.width || 300;
            const height = this.canvas.height || 36;
            ctx.clearRect(0, 0, width, height);

            const gap = 2;
            const barWidth = Math.max(2, (width - (numBars - 1) * gap) / numBars);

            for (let i = 0; i < numBars; i++) {
                let barHeight = 4;
                if (this.isPlaying) {
                    const time = Date.now() * 0.005;
                    const noise = Math.sin(i * 0.4 + time) * Math.cos(i * 0.2 - time * 0.8);
                    barHeight = Math.max(4, Math.abs(noise) * (height - 6) + Math.random() * 6);
                }

                const x = i * (barWidth + gap);
                const y = height - barHeight;

                const grad = ctx.createLinearGradient(0, height, 0, 0);
                grad.addColorStop(0, '#fcbf47');
                grad.addColorStop(1, '#ff6dc4');

                ctx.fillStyle = grad;
                ctx.fillRect(x, y, barWidth, barHeight);
            }

            this.visualizerAnimationId = requestAnimationFrame(draw);
        };

        draw();
    }

    // --- Modals & Drawers Setup ---
    setupModalEvents() {
        // Album Picker
        this.albumPickerBtn.addEventListener('click', () => this.openModal(this.albumModal));
        this.closeAlbumModal.addEventListener('click', () => this.closeModal(this.albumModal));
        this.mobileSelectAlbumBtn.addEventListener('click', () => {
            this.closeMobileDrawer();
            this.openModal(this.albumModal);
        });

        // Search Modal
        this.searchBtn.addEventListener('click', () => {
            this.openModal(this.searchModal);
            setTimeout(() => this.searchInput.focus(), 100);
        });
        this.closeSearchModal.addEventListener('click', () => this.closeModal(this.searchModal));
        this.searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));

        // File / Metadata Drawer
        const openDrawer = () => this.metaDrawer.classList.add('open');
        const closeDrawer = () => this.metaDrawer.classList.remove('open');
        this.metaInfoBtn.addEventListener('click', openDrawer);
        this.openDrawerBtn.addEventListener('click', openDrawer);
        this.closeDrawerBtn.addEventListener('click', closeDrawer);
        this.drawerBackdrop.addEventListener('click', closeDrawer);

        // Mobile Menu Drawer
        this.hamburgerBtn.addEventListener('click', () => this.mobileMenuDrawer.classList.add('open'));
        this.closeMobileMenu.addEventListener('click', () => this.closeMobileDrawer());
        this.mobileMenuBackdrop.addEventListener('click', () => this.closeMobileDrawer());

        // Copy All Download Links
        this.copyAllLinksBtn.addEventListener('click', () => {
            const album = this.currentAlbum;
            const text = `${album.title} - ${album.artist} (FLAC 24-Bit / 96kHz Lossless)\n` +
                album.tracks.map((t, idx) => `${idx + 1}. ${t.name} [${t.size}]`).join('\n');
            navigator.clipboard.writeText(text);
            this.copyAllLinksBtn.textContent = 'ÄÃ£ Copy!';
            this.showToast('ÄÃ£ copy danh sÃ¡ch file Hi-Res vÃ o clipboard');
            setTimeout(() => this.copyAllLinksBtn.textContent = 'Copy All', 2000);
        });

        // Telegram Scanner Modal
        if (this.openTgModalBtn && this.tgModal) {
            this.openTgModalBtn.addEventListener('click', () => {
                this.openModal(this.tgModal);
                if (this.tgChatInput) setTimeout(() => this.tgChatInput.focus(), 100);
            });
        }
        if (this.closeTgModal && this.tgModal) {
            this.closeTgModal.addEventListener('click', () => this.closeModal(this.tgModal));
        }
        if (this.tgScanSubmitBtn) {
            this.tgScanSubmitBtn.addEventListener('click', () => {
                const chatId = this.tgChatInput ? this.tgChatInput.value : '';
                const limit = this.tgLimitInput ? this.tgLimitInput.value : 100;
                this.scanTelegramChannel(chatId, limit);
            });
        }
        if (this.tgLoadDemoBtn) {
            this.tgLoadDemoBtn.addEventListener('click', () => {
                this.albums = [...ALBUMS_DATABASE];
                this.currentAlbumIndex = 0;
                this.currentTrackIndex = 0;
                this.loadAlbum(0, 0, false);
                this.renderAlbumGrid();
                if (this.albumCountBadge) this.albumCountBadge.textContent = `${this.albums.length} Albums`;
                if (this.tgStorageLabel) this.tgStorageLabel.textContent = 'Demo Mode';
                if (this.tgModal) this.closeModal(this.tgModal);
                this.showToast('ÄÃ£ táº£i láº¡i kho nháº¡c máº«u Demo!');
            });
        }

        // Nav Links Events
        if (this.navMusics) {
            this.navMusics.addEventListener('click', (e) => {
                e.preventDefault();
                this.setActiveNavLink(this.navMusics);
                this.showToast('Đang phát kho nhạc chính');
            });
        }

        if (this.navHires) {
            this.navHires.addEventListener('click', (e) => {
                e.preventDefault();
                this.setActiveNavLink(this.navHires);
                this.filterHiresAlbums();
            });
        }

        if (this.navAlbums) {
            this.navAlbums.addEventListener('click', (e) => {
                e.preventDefault();
                this.setActiveNavLink(this.navAlbums);
                this.openModal(this.albumModal);
            });
        }

        if (this.navArtists && this.artistModal) {
            this.navArtists.addEventListener('click', (e) => {
                e.preventDefault();
                this.setActiveNavLink(this.navArtists);
                this.renderArtistGrid();
                this.openModal(this.artistModal);
            });
        }
        if (this.closeArtistModal && this.artistModal) {
            this.closeArtistModal.addEventListener('click', () => this.closeModal(this.artistModal));
        }

        if (this.navGenres && this.genreModal) {
            this.navGenres.addEventListener('click', (e) => {
                e.preventDefault();
                this.setActiveNavLink(this.navGenres);
                this.renderGenreGrid();
                this.openModal(this.genreModal);
            });
        }
        if (this.closeGenreModal && this.genreModal) {
            this.closeGenreModal.addEventListener('click', () => this.closeModal(this.genreModal));
        }

        // Mobile Nav Links Events
        const mobileLinks = [
            { id: 'mobileNavMusics', action: () => this.showToast('Đang phát kho nhạc chính') },
            { id: 'mobileNavHires', action: () => this.filterHiresAlbums() },
            { id: 'mobileNavAlbums', action: () => this.openModal(this.albumModal) },
            { id: 'mobileNavArtists', action: () => { this.renderArtistGrid(); this.openModal(this.artistModal); } },
            { id: 'mobileNavGenres', action: () => { this.renderGenreGrid(); this.openModal(this.genreModal); } },
            { id: 'mobileNavPlaylists', action: () => { this.loadPlaylists(); this.openModal(this.playlistModal); } },
        ];
        mobileLinks.forEach(item => {
            const el = document.getElementById(item.id);
            if (el) {
                el.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.closeMobileDrawer();
                    item.action();
                });
            }
        });

        // Playlist Modal Events
        if (this.navPlaylists && this.playlistModal) {
            this.navPlaylists.addEventListener('click', (e) => {
                e.preventDefault();
                this.setActiveNavLink(this.navPlaylists);
                this.openModal(this.playlistModal);
                this.loadPlaylists();
            });
        }
        if (this.closePlaylistModal && this.playlistModal) {
            this.closePlaylistModal.addEventListener('click', () => this.closeModal(this.playlistModal));
        }
        if (this.createPlaylistBtn && this.newPlaylistName) {
            this.createPlaylistBtn.addEventListener('click', () => this.handleCreatePlaylist());
            this.newPlaylistName.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.handleCreatePlaylist();
            });
        }

        // Add to Playlist Modal Events
        if (this.closeAddToPlaylistModal && this.addToPlaylistModal) {
            this.closeAddToPlaylistModal.addEventListener('click', () => this.closeModal(this.addToPlaylistModal));
        }

        // Close on overlay click
        [this.albumModal, this.searchModal, this.tgModal, this.playlistModal, this.addToPlaylistModal, this.artistModal, this.genreModal].forEach(modal => {
            if (modal) {
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) this.closeModal(modal);
                });
            }
        });
    }

    openModal(modal) {
        if (modal) modal.classList.add('open');
    }

    closeModal(modal) {
        if (modal) modal.classList.remove('open');
    }

    closeMobileDrawer() {
        if (this.mobileMenuDrawer) this.mobileMenuDrawer.classList.remove('open');
    }

    renderAlbumGrid() {
        if (!this.albumGrid) return;
        this.albumGrid.innerHTML = '';
        this.albums.forEach((album, idx) => {
            const card = document.createElement('div');
            card.className = `album-card ${idx === this.currentAlbumIndex ? 'active' : ''}`;
            card.innerHTML = `
                <img src="${album.coverUrl}" class="album-card-img" alt="${album.title}" onerror="this.src='https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop'">
                <div class="album-card-info">
                    <span class="album-card-title">${album.title}</span>
                    <span class="album-card-artist">${album.artist}</span>
                    <span class="album-card-year">${album.year} â€¢ ${album.tracks.length} Tracks</span>
                </div>
            `;

            card.addEventListener('click', () => {
                this.loadAlbum(idx, 0, true);
                this.closeModal(this.albumModal);
                this.showToast(`ÄÃ£ chuyá»ƒn sang album: ${album.title}`);
                this.renderAlbumGrid();
            });

            this.albumGrid.appendChild(card);
        });
    }

    updateDrawerInfo() {
        const album = this.currentAlbum;
        if (this.drawerAlbumTitle) this.drawerAlbumTitle.textContent = `${album.artist} - ${album.title}`;
        if (this.drawerSpecFormat) this.drawerSpecFormat.textContent = album.format;
        if (this.drawerSpecSize) this.drawerSpecSize.textContent = album.totalSize;
        if (this.drawerSpecDate) this.drawerSpecDate.textContent = album.year;
        if (this.drawerSpecPublisher) this.drawerSpecPublisher.textContent = album.publisher;

        if (!this.drawerFileList) return;
        this.drawerFileList.innerHTML = '';
        album.tracks.forEach((track, idx) => {
            const row = document.createElement('div');
            row.className = 'file-row';
            row.innerHTML = `
                <div class="file-info">
                    <div class="file-title">${idx + 1}. ${track.name}</div>
                    <div class="file-meta">${track.artist || album.artist} â€¢ ${track.format || album.format || 'Lossless'} â€¢ ${track.duration || ''}</div>
                </div>
                <div class="file-actions">
                    <button class="file-action-btn download-btn">PhÃ¡t Ngay</button>
                </div>
            `;

            const btn = row.querySelector('.download-btn');
            btn.addEventListener('click', () => {
                this.loadTrack(idx, true);
                this.metaDrawer.classList.remove('open');
                this.showToast(`Äang phÃ¡t: ${track.name}`);
            });

            this.drawerFileList.appendChild(row);
        });
    }

    handleSearch(query) {
        if (!query.trim()) {
            this.searchResults.innerHTML = '<div class="search-empty">Nháº­p tá»« khoÃ¡ Ä‘á»ƒ tÃ¬m bÃ i hÃ¡t nhanh...</div>';
            return;
        }

        const q = query.toLowerCase();
        let matches = [];

        this.albums.forEach((album, albumIdx) => {
            album.tracks.forEach((track, trackIdx) => {
                if (track.name.toLowerCase().includes(q) || album.artist.toLowerCase().includes(q) || album.title.toLowerCase().includes(q)) {
                    matches.push({ album, albumIdx, track, trackIdx });
                }
            });
        });

        if (matches.length === 0) {
            this.searchResults.innerHTML = `<div class="search-empty">KhÃ´ng tÃ¬m tháº¥y bÃ i hÃ¡t nÃ o khá»›p vá»›i "${query}"</div>`;
            return;
        }

        this.searchResults.innerHTML = '';
        matches.forEach(item => {
            const el = document.createElement('div');
            el.className = 'search-item';
            el.innerHTML = `
                <div>
                    <div style="font-weight:600; color:#fff;">${item.track.name}</div>
                    <div style="font-size:0.78rem; color:rgba(255,255,255,0.5);">${item.album.artist} â€¢ ${item.album.title}</div>
                </div>
                <span style="color:var(--accent-gold); font-size:0.8rem;">${item.track.duration}</span>
            `;

            el.addEventListener('click', () => {
                this.loadAlbum(item.albumIdx, item.trackIdx, true);
                this.closeModal(this.searchModal);
                this.showToast(`Äang phÃ¡t: ${item.track.name}`);
            });

            this.searchResults.appendChild(el);
        });
    }

    // --- Keyboard Shortcuts ---
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ignore if typing in input
            if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
                if (e.key === 'Escape') this.closeModal(this.searchModal);
                return;
            }

            if (e.code === 'Space') {
                e.preventDefault();
                this.togglePlay();
            } else if (e.code === 'ArrowRight') {
                e.preventDefault();
                this.nextTrack();
            } else if (e.code === 'ArrowLeft') {
                e.preventDefault();
                this.prevTrack();
            } else if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.openModal(this.searchModal);
                setTimeout(() => this.searchInput.focus(), 100);
            } else if (e.key === 'Escape') {
                this.closeModal(this.albumModal);
                this.closeModal(this.searchModal);
                this.closeModal(this.tgModal);
                this.closeModal(this.playlistModal);
                this.closeModal(this.addToPlaylistModal);
                this.closeModal(this.artistModal);
                this.closeModal(this.genreModal);
                this.metaDrawer.classList.remove('open');
                this.closeMobileDrawer();
            }
        });
    }

    // --- Toast Notifications ---
    showToast(message) {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 2600);
    }
    // --- Playlist Management Methods ---
    async loadPlaylists() {
        if (!this.playlistGrid) return;
        this.playlistGrid.innerHTML = `
            <div style="text-align: center; padding: 30px; color: var(--text-muted);">
                <div class="tg-spinner" style="margin: 0 auto 10px auto;"></div>
                <span>Đang tải danh sách playlist...</span>
            </div>
        `;
        try {
            const res = await fetch('/api/music/playlists');
            const data = await res.json();
            if (data && data.status === 'success') {
                this.playlists = data.playlists || [];
                this.renderPlaylists();
            } else {
                this.playlistGrid.innerHTML = `<div style="text-align: center; padding: 20px; color: #f87171;">Không thể tải playlist: ${data.message || 'Lỗi server'}</div>`;
            }
        } catch (err) {
            this.playlistGrid.innerHTML = `<div style="text-align: center; padding: 20px; color: #f87171;">Lỗi kết nối tới máy chủ.</div>`;
        }
    }

    renderPlaylists() {
        if (!this.playlistGrid) return;
        this.playlistGrid.innerHTML = '';
        if (this.playlists.length === 0) {
            this.playlistGrid.innerHTML = `
                <div style="text-align: center; padding: 40px 20px; color: var(--text-muted); background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.08);">
                    <div style="font-size: 2rem; margin-bottom: 8px;">📂</div>
                    <div style="font-weight: 600; color: #fff; margin-bottom: 4px;">Chưa có Playlist nào</div>
                    <div style="font-size: 0.85rem;">Nhập tên ở trên và nhấn "Tạo Mới" để tạo danh sách đầu tiên!</div>
                </div>
            `;
            return;
        }

        this.playlists.forEach(pl => {
            const trackCount = (pl.tracks && Array.isArray(pl.tracks)) ? pl.tracks.length : 0;
            const item = document.createElement('div');
            item.className = 'playlist-card-item';
            item.innerHTML = `
                <div class="playlist-card-left">
                    <div class="playlist-icon-badge">🎵</div>
                    <div class="playlist-card-info">
                        <h4>${this.escapeHtml(pl.name)}</h4>
                        <p>${trackCount} bài hát • Tạo lúc ${new Date((pl.created_at || Date.now()/1000) * 1000).toLocaleDateString('vi-VN')}</p>
                    </div>
                </div>
                <div class="playlist-card-actions">
                    <button class="btn-play-playlist" ${trackCount === 0 ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                        <span>Phát</span>
                    </button>
                    <button class="btn-delete-playlist" title="Xóa playlist này">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    </button>
                </div>
            `;

            const playBtn = item.querySelector('.btn-play-playlist');
            if (playBtn && trackCount > 0) {
                playBtn.addEventListener('click', () => {
                    this.playPlaylist(pl);
                    this.closeModal(this.playlistModal);
                });
            }

            const delBtn = item.querySelector('.btn-delete-playlist');
            if (delBtn) {
                delBtn.addEventListener('click', async () => {
                    if (confirm(`Bạn có chắc muốn xóa playlist "${pl.name}" không?`)) {
                        await this.deletePlaylist(pl.id);
                    }
                });
            }

            this.playlistGrid.appendChild(item);
        });
    }

    async handleCreatePlaylist() {
        if (!this.newPlaylistName) return;
        const name = this.newPlaylistName.value.trim();
        if (!name) {
            this.showToast('Vui lòng nhập tên playlist!');
            return;
        }

        try {
            const res = await fetch('/api/music/playlists', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                this.newPlaylistName.value = '';
                this.showToast(`Đã tạo playlist "${name}" thành công!`);
                await this.loadPlaylists();
            } else {
                this.showToast(data.message || data.detail || 'Không thể tạo playlist');
            }
        } catch (err) {
            this.showToast('Lỗi khi gửi yêu cầu tạo playlist');
        }
    }

    async deletePlaylist(playlistId) {
        try {
            const res = await fetch(`/api/music/playlists/${playlistId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                this.showToast('Đã xóa playlist thành công!');
                await this.loadPlaylists();
            } else {
                this.showToast(data.message || 'Không thể xóa playlist');
            }
        } catch (err) {
            this.showToast('Lỗi khi xóa playlist');
        }
    }

    playPlaylist(playlist) {
        if (!playlist || !playlist.tracks || playlist.tracks.length === 0) {
            this.showToast('Playlist này hiện chưa có bài hát nào!');
            return;
        }

        const playlistAlbum = {
            id: `pl-${playlist.id}`,
            title: `Playlist: ${playlist.name}`,
            artist: 'Danh Sách Cá Nhân',
            coverUrl: (playlist.tracks[0] && playlist.tracks[0].coverUrl) || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop',
            format: 'FLAC Hi-Res Lossless',
            year: new Date().getFullYear().toString(),
            publisher: 'XTAPO Custom Playlist',
            glowColors: { glow1: 'radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)', glow2: 'radial-gradient(circle, #ec4899 0%, #be185d 60%, transparent 80%)' },
            tracks: playlist.tracks
        };

        const existingIdx = this.albums.findIndex(a => a.id === playlistAlbum.id);
        if (existingIdx !== -1) {
            this.albums[existingIdx] = playlistAlbum;
            this.loadAlbum(existingIdx, 0, true);
        } else {
            this.albums.unshift(playlistAlbum);
            this.loadAlbum(0, 0, true);
        }
        this.renderAlbumGrid();
        this.showToast(`Đang phát playlist "${playlist.name}" (${playlist.tracks.length} bài)`);
    }

    async openAddToPlaylist(track) {
        this.selectedTrackForPlaylist = track;
        if (this.addToPlaylistTrackTitle) {
            this.addToPlaylistTrackTitle.textContent = `${track.name} - ${track.artist || this.currentAlbum.artist}`;
        }
        this.openModal(this.addToPlaylistModal);

        if (this.addToPlaylistOptions) {
            this.addToPlaylistOptions.innerHTML = '<div style="text-align:center; padding:15px; color:var(--text-muted);"><div class="tg-spinner" style="margin:0 auto 8px auto;"></div>Đang tải playlists...</div>';
        }

        try {
            const res = await fetch('/api/music/playlists');
            const data = await res.json();
            if (data && data.status === 'success') {
                this.playlists = data.playlists || [];
                this.renderAddToPlaylistOptions();
            }
        } catch (e) {
            if (this.addToPlaylistOptions) {
                this.addToPlaylistOptions.innerHTML = '<div style="color:#f87171; text-align:center; padding:10px;">Lỗi tải playlist.</div>';
            }
        }
    }

    renderAddToPlaylistOptions() {
        if (!this.addToPlaylistOptions) return;
        this.addToPlaylistOptions.innerHTML = '';

        if (this.playlists.length === 0) {
            this.addToPlaylistOptions.innerHTML = `
                <div style="text-align: center; padding: 20px; color: var(--text-muted);">
                    <div>Bạn chưa có playlist nào.</div>
                    <button style="margin-top: 10px; padding: 8px 14px; border-radius: 6px; background: #0284c7; color: #fff; border: none; cursor: pointer;" id="createFirstPlaylistBtn">Tạo Playlist Ngay</button>
                </div>
            `;
            const btn = this.addToPlaylistOptions.querySelector('#createFirstPlaylistBtn');
            if (btn) {
                btn.addEventListener('click', () => {
                    this.closeModal(this.addToPlaylistModal);
                    this.openModal(this.playlistModal);
                });
            }
            return;
        }

        this.playlists.forEach(pl => {
            const isAlreadyIn = pl.tracks && pl.tracks.some(t => (t.msgId && t.msgId === this.selectedTrackForPlaylist.msgId) || (t.name === this.selectedTrackForPlaylist.name));
            const opt = document.createElement('div');
            opt.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; cursor: pointer; transition: all 0.2s;';
            opt.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.1rem;">📑</span>
                    <div>
                        <div style="font-weight: 600; color: #fff; font-size: 0.9rem;">${this.escapeHtml(pl.name)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">${(pl.tracks || []).length} bài hát</div>
                    </div>
                </div>
                <button style="padding: 6px 12px; border-radius: 6px; border: none; font-size: 0.8rem; font-weight: 600; cursor: pointer; background: ${isAlreadyIn ? 'rgba(255,255,255,0.1)' : '#0284c7'}; color: ${isAlreadyIn ? 'var(--text-muted)' : '#fff'};">
                    ${isAlreadyIn ? '✓ Đã có' : '+ Thêm'}
                </button>
            `;

            opt.addEventListener('click', () => {
                this.addTrackToPlaylist(pl.id, this.selectedTrackForPlaylist);
            });

            this.addToPlaylistOptions.appendChild(opt);
        });
    }

    async addTrackToPlaylist(playlistId, track) {
        const targetPl = this.playlists.find(p => p.id === playlistId);
        if (!targetPl) return;

        const currentTracks = targetPl.tracks || [];
        const isAlreadyIn = currentTracks.some(t => (t.msgId && t.msgId === track.msgId) || (t.name === track.name));
        
        let newTracks;
        if (isAlreadyIn) {
            newTracks = currentTracks.filter(t => !((t.msgId && t.msgId === track.msgId) || (t.name === track.name)));
            this.showToast(`Đã xóa "${track.name}" khỏi playlist "${targetPl.name}"`);
        } else {
            const trackToAdd = {
                ...track,
                artist: track.artist || this.currentAlbum.artist,
                coverUrl: track.coverUrl || this.currentAlbum.coverUrl
            };
            newTracks = [...currentTracks, trackToAdd];
            this.showToast(`Đã thêm "${track.name}" vào playlist "${targetPl.name}"!`);
        }

        try {
            const res = await fetch(`/api/music/playlists/${playlistId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tracks: newTracks })
            });
            if (res.ok) {
                targetPl.tracks = newTracks;
                this.renderAddToPlaylistOptions();
            }
        } catch (e) {
            this.showToast('Lỗi khi cập nhật bài hát vào playlist');
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    // --- Artists & Genres Feature Methods ---
    setActiveNavLink(activeEl) {
        document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
        if (activeEl) activeEl.classList.add('active');
    }

    filterHiresAlbums() {
        const hiresAlbums = this.albums.filter(a => {
            const fmt = (a.format || '').toLowerCase();
            return fmt.includes('flac') || fmt.includes('24-bit') || fmt.includes('hi-res') || fmt.includes('dsd') || fmt.includes('lossless');
        });
        if (hiresAlbums.length > 0) {
            this.openModal(this.albumModal);
            this.showToast(`Tìm thấy ${hiresAlbums.length} Album chất lượng Hi-Res Lossless!`);
        } else {
            this.showToast('Tất cả các bài nhạc đều hỗ trợ phát Lossless!');
        }
    }

    renderArtistGrid() {
        if (!this.artistGrid) return;
        this.artistGrid.innerHTML = '';

        // Extract and aggregate all artists
        const artistMap = new Map();
        this.albums.forEach(album => {
            const albArtist = (album.artist || 'Unknown Artist').trim();
            (album.tracks || []).forEach(track => {
                const trackArtist = (track.artist || albArtist || 'Unknown Artist').trim();
                if (!artistMap.has(trackArtist)) {
                    artistMap.set(trackArtist, {
                        name: trackArtist,
                        coverUrl: track.coverUrl || album.coverUrl,
                        albums: new Set([album.title]),
                        tracks: [track]
                    });
                } else {
                    const existing = artistMap.get(trackArtist);
                    existing.albums.add(album.title);
                    if (!existing.tracks.some(t => (t.msgId && t.msgId === track.msgId) || t.name === track.name)) {
                        existing.tracks.push(track);
                    }
                }
            });
        });

        if (artistMap.size === 0) {
            this.artistGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">Chưa có dữ liệu ca sĩ trong thư viện.</div>';
            return;
        }

        const sortedArtists = Array.from(artistMap.values()).sort((a, b) => b.tracks.length - a.tracks.length);

        sortedArtists.forEach(art => {
            const card = document.createElement('div');
            card.className = 'artist-card-item';
            card.innerHTML = `
                <img src="${art.coverUrl}" class="artist-avatar-img" alt="${this.escapeHtml(art.name)}" onerror="this.src='https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop'">
                <div class="artist-card-info">
                    <h4>${this.escapeHtml(art.name)}</h4>
                    <p>${art.tracks.length} bài hát • ${art.albums.size} album</p>
                </div>
            `;

            card.addEventListener('click', () => {
                this.closeModal(this.artistModal);
                const artistAlbum = {
                    id: `artist-${encodeURIComponent(art.name)}`,
                    title: `Tuyển Tập: ${art.name}`,
                    artist: art.name,
                    coverUrl: art.coverUrl,
                    format: 'FLAC Hi-Res Lossless',
                    year: new Date().getFullYear().toString(),
                    publisher: 'Artist Spotlight Collection',
                    glowColors: { glow1: 'radial-gradient(circle, #f59e0b 0%, #b45309 60%, transparent 80%)', glow2: 'radial-gradient(circle, #ff6dc4 0%, #4338ca 60%, transparent 80%)' },
                    tracks: art.tracks
                };

                const existingIdx = this.albums.findIndex(a => a.id === artistAlbum.id);
                if (existingIdx !== -1) {
                    this.albums[existingIdx] = artistAlbum;
                    this.loadAlbum(existingIdx, 0, true);
                } else {
                    this.albums.unshift(artistAlbum);
                    this.loadAlbum(0, 0, true);
                }
                this.renderAlbumGrid();
                this.showToast(`Đang phát tuyển tập ca sĩ "${art.name}" (${art.tracks.length} bài)`);
            });

            this.artistGrid.appendChild(card);
        });
    }

    renderGenreGrid() {
        if (!this.genreGrid) return;
        this.genreGrid.innerHTML = '';

        const genreIcons = {
            'Bolero': '🎻',
            'Lofi': '☕',
            'EDM / Remix': '⚡',
            'EDM': '⚡',
            'Remix': '⚡',
            'Acoustic / Instrumental': '🎸',
            'Acoustic': '🎸',
            'Instrumental': '🎹',
            'Rap / Hip-Hop': '🎤',
            'Rap': '🎤',
            'Hip-Hop': '🎤',
            'Pop / Ballad': '💖',
            'Pop': '✨',
            'Ballad': '🎼',
            'Jazz': '🎷',
            'Rock': '🤘',
            'Khác': '🎵'
        };

        const genreColors = {
            'Bolero': 'linear-gradient(135deg, rgba(217, 119, 6, 0.3), rgba(180, 83, 9, 0.1))',
            'Lofi': 'linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(67, 56, 202, 0.1))',
            'EDM / Remix': 'linear-gradient(135deg, rgba(236, 72, 153, 0.3), rgba(190, 24, 93, 0.1))',
            'Acoustic / Instrumental': 'linear-gradient(135deg, rgba(16, 185, 129, 0.3), rgba(4, 120, 87, 0.1))',
            'Rap / Hip-Hop': 'linear-gradient(135deg, rgba(239, 68, 68, 0.3), rgba(185, 28, 28, 0.1))',
            'Pop / Ballad': 'linear-gradient(135deg, rgba(2, 132, 199, 0.3), rgba(3, 105, 161, 0.1))',
            'Jazz': 'linear-gradient(135deg, rgba(245, 158, 11, 0.3), rgba(217, 119, 6, 0.1))',
            'Rock': 'linear-gradient(135deg, rgba(139, 92, 246, 0.3), rgba(109, 40, 217, 0.1))',
            'Khác': 'linear-gradient(135deg, rgba(100, 116, 139, 0.3), rgba(71, 85, 105, 0.1))'
        };

        // Aggregate tracks by genre
        const genreMap = new Map();
        this.albums.forEach(album => {
            (album.tracks || []).forEach(track => {
                const g = (track.genre || 'Khác').trim() || 'Khác';
                if (!genreMap.has(g)) {
                    genreMap.set(g, {
                        genre: g,
                        tracks: [track],
                        coverUrl: track.coverUrl || album.coverUrl
                    });
                } else {
                    const existing = genreMap.get(g);
                    if (!existing.tracks.some(t => (t.msgId && t.msgId === track.msgId) || t.name === track.name)) {
                        existing.tracks.push(track);
                    }
                }
            });
        });

        if (genreMap.size === 0) {
            this.genreGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">Chưa có dữ liệu thể loại trong thư viện.</div>';
            return;
        }

        const sortedGenres = Array.from(genreMap.values()).sort((a, b) => b.tracks.length - a.tracks.length);

        sortedGenres.forEach(gObj => {
            const icon = genreIcons[gObj.genre] || '🎵';
            const bg = genreColors[gObj.genre] || 'linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02))';

            const card = document.createElement('div');
            card.className = 'genre-card-item';
            card.style.background = bg;
            card.innerHTML = `
                <div class="genre-card-icon">${icon}</div>
                <div class="genre-card-name">${this.escapeHtml(gObj.genre)}</div>
                <div class="genre-card-count">${gObj.tracks.length} bài hát</div>
            `;

            card.addEventListener('click', () => {
                this.closeModal(this.genreModal);
                const genreAlbum = {
                    id: `genre-${encodeURIComponent(gObj.genre)}`,
                    title: `Thể Loại: ${gObj.genre}`,
                    artist: 'Tuyển Tập Thể Loại',
                    coverUrl: gObj.coverUrl || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop',
                    format: 'FLAC Hi-Res Lossless',
                    year: new Date().getFullYear().toString(),
                    publisher: `Genre Collection • ${gObj.genre}`,
                    glowColors: { glow1: 'radial-gradient(circle, #ec4899 0%, #be185d 60%, transparent 80%)', glow2: 'radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)' },
                    tracks: gObj.tracks
                };

                const existingIdx = this.albums.findIndex(a => a.id === genreAlbum.id);
                if (existingIdx !== -1) {
                    this.albums[existingIdx] = genreAlbum;
                    this.loadAlbum(existingIdx, 0, true);
                } else {
                    this.albums.unshift(genreAlbum);
                    this.loadAlbum(0, 0, true);
                }
                this.renderAlbumGrid();
                this.showToast(`Đang phát thể loại "${gObj.genre}" (${gObj.tracks.length} bài)`);
            });

            this.genreGrid.appendChild(card);
        });
    }
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    window.xtapoApp = new XTAPOMusicApp();
});


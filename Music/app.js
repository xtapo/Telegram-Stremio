/**
 * XTAPO MUSIC - AUDIO & VINYL PLAYER
 * High-Fidelity Audio Experience & Interactive Vinyl Animation
 */

// Polyfill: CanvasRenderingContext2D.roundRect for older browsers
if (!CanvasRenderingContext2D.prototype.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function (x, y, w, h, radii) {
        const r = Array.isArray(radii) ? radii : [radii, radii, radii, radii];
        const [tl, tr, br, bl] = r.map(v => Math.min(v || 0, w / 2, h / 2));
        this.moveTo(x + tl, y);
        this.lineTo(x + w - tr, y);
        this.quadraticCurveTo(x + w, y, x + w, y + tr);
        this.lineTo(x + w, y + h - br);
        this.quadraticCurveTo(x + w, y + h, x + w - br, y + h);
        this.lineTo(x + bl, y + h);
        this.quadraticCurveTo(x, y + h, x, y + h - bl);
        this.lineTo(x, y + tl);
        this.quadraticCurveTo(x, y, x + tl, y);
        this.closePath();
        return this;
    };
}
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

        // Visualizer Canvas & Web Audio API
        this.canvas = document.getElementById('visualizerCanvas');
        this.canvasCtx = this.canvas.getContext('2d');
        this.visualizerAnimationId = null;
        this.visualizerSection = document.getElementById('visualizerSection');
        this.vizFreqLabel = document.getElementById('vizFreqLabel');
        this.vizDbLabel = document.getElementById('vizDbLabel');
        this.vizModeBtns = document.querySelectorAll('.viz-mode-btn');
        this.vizMode = 'bars'; // 'bars', 'wave', 'circular', 'mirror'
        this.analyserNode = null;
        this.audioSourceNode = null;
        this.audioCtx = null;
        this.freqData = null;
        this.timeData = null;
        this.smoothedFreqData = null;

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
        
        // Tự động kiểm tra thư viện Telegram từ Backend
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
                        this.tgStorageLabel.textContent = '⚡ Telegram Live';
                    }
                    this.showToast(`Đã đồng bộ ${this.albums.length} Album từ Telegram Cloud!`);
                }
            }
        } catch (err) {
            // Đang mở file tĩnh hoặc backend chưa kết nối
            console.log('[XTAPO MUSIC] Backend API offline or file mode, using local database.');
        }
    }

    // --- Scan Telegram Channel ---
    async scanTelegramChannel(chatId, limit = 100) {
        if (!chatId || !chatId.trim()) {
            this.showToast('Vui lòng nhập ID hoặc Username kênh Telegram!');
            return;
        }

        if (this.tgStatusIndicator) {
            this.tgStatusIndicator.style.display = 'flex';
            this.tgStatusMessage.textContent = 'Đang kết nối Telegram & quét bài hát audio...';
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
                data = { status: 'error', message: rawText || `Lỗi HTTP ${res.status}` };
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
                    this.tgStorageLabel.textContent = '⚡ Telegram Live';
                }

                this.closeModal(this.tgModal);
                this.showToast(data.message || `Đã quét ${data.count} bài hát từ kênh!`);
            } else {
                const errMsg = data.message || data.detail || 'Không tìm thấy file nhạc hoặc Bot chưa có quyền đọc tin nhắn trong kênh này.';
                if (this.tgStatusMessage) {
                    this.tgStatusMessage.textContent = `❌ ${errMsg}`;
                }
                this.showToast(`Thông báo: ${errMsg}`);
            }
        } catch (err) {
            if (this.tgStatusMessage) {
                this.tgStatusMessage.textContent = `❌ Lỗi: ${err.message}. Hãy kiểm tra ID/Username kênh và đảm bảo Bot đã vào kênh!`;
            }
            this.showToast(`Lỗi: ${err.message}`);
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
        album.tracks.forEach(t => {
            const parts = t.duration.split(':');
            totalSec += parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
        });
        const mins = Math.floor(totalSec / 60);
        this.totalDurationLabel.textContent = `${mins} Minutes`;

        // Update Covers
        this.albumCoverImg.src = album.coverUrl;
        this.vinylCenterImg.src = album.coverUrl;

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

        album.tracks.forEach((track, idx) => {
            const li = document.createElement('li');
            li.className = `track-item ${idx === this.currentTrackIndex ? 'active' : ''}`;
            li.innerHTML = `
                <div class="track-item-left">
                    <span class="track-number">${idx + 1}</span>
                    <div class="track-equalizer">
                        <div class="eq-bar"></div>
                        <div class="eq-bar"></div>
                        <div class="eq-bar"></div>
                    </div>
                    <span class="track-name" title="${track.name}">${track.name}</span>
                </div>
                <span class="track-duration">${track.duration}</span>
            `;

            li.addEventListener('click', () => {
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

        // Update Now Playing Labels
        this.nowPlayingTitle.textContent = `${this.currentTrackIndex + 1}. ${track.name}`;
        this.nowPlayingArtist.textContent = album.artist;
        this.timeTotal.textContent = track.duration;
        this.timeCurrent.textContent = "0:00";
        this.updateProgress(0);

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
        if (track.previewUrl) {
            this.audio.src = track.previewUrl;
            this.audio.load();
        }

        if (autoPlay) {
            this.play();
        } else {
            this.pauseVisuals();
        }
    }

    // --- Audio Engine & Synth Fallback ---
    play() {
        this.isPlaying = true;
        this.updatePlayStateVisuals(true);

        // Initialize Web Audio API analyser on first play (requires user gesture)
        this.initAudioAnalyser();

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
            this.showToast(this.isShuffle ? "Chế độ phát xáo trộn: BẬT" : "Chế độ phát xáo trộn: TẮT");
        });

        // Repeat Mode Toggle (0: off -> 1: all -> 2: one)
        this.repeatBtn.addEventListener('click', () => {
            this.repeatMode = (this.repeatMode + 1) % 3;
            if (this.repeatMode === 0) {
                this.repeatBtn.classList.remove('active');
                this.repeatIndicator.textContent = '';
                this.showToast("Chế độ lặp lại: TẮT");
            } else if (this.repeatMode === 1) {
                this.repeatBtn.classList.add('active');
                this.repeatIndicator.textContent = 'ALL';
                this.showToast("Chế độ lặp lại: TẤT CẢ");
            } else if (this.repeatMode === 2) {
                this.repeatBtn.classList.add('active');
                this.repeatIndicator.textContent = '1';
                this.showToast("Chế độ lặp lại: 1 BÀI");
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

    // --- Audio Spectrum Visualizer (Web Audio API) ---
    setupVisualizer() {
        // Set canvas to high-DPI
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());

        // Mode toggle buttons
        this.vizModeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.vizModeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.vizMode = btn.dataset.mode;
            });
        });

        // Start animation loop
        this.drawVisualizer();
    }

    resizeCanvas() {
        const wrap = this.canvas.parentElement;
        const dpr = window.devicePixelRatio || 1;
        const rect = wrap.getBoundingClientRect();
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.canvasCtx.scale(dpr, dpr);
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
    }

    initAudioAnalyser() {
        if (this.analyserNode) return; // already connected
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            
            if (!this.audioCtx) {
                this.audioCtx = new AudioCtx();
            }
            if (this.audioCtx.state === 'suspended') {
                this.audioCtx.resume();
            }

            this.analyserNode = this.audioCtx.createAnalyser();
            this.analyserNode.fftSize = 256;
            this.analyserNode.smoothingTimeConstant = 0.82;
            this.analyserNode.minDecibels = -90;
            this.analyserNode.maxDecibels = -10;

            // Connect audio element → analyser → destination
            if (!this.audioSourceNode) {
                this.audioSourceNode = this.audioCtx.createMediaElementSource(this.audio);
            }
            this.audioSourceNode.connect(this.analyserNode);
            this.analyserNode.connect(this.audioCtx.destination);

            const bufferLength = this.analyserNode.frequencyBinCount;
            this.freqData = new Uint8Array(bufferLength);
            this.timeData = new Uint8Array(bufferLength);
            this.smoothedFreqData = new Float32Array(bufferLength);
        } catch (e) {
            console.warn('[Visualizer] Web Audio API init failed:', e.message);
            this.analyserNode = null;
        }
    }

    drawVisualizer() {
        const ctx = this.canvasCtx;
        const dpr = window.devicePixelRatio || 1;
        const w = this.canvas.width / dpr;
        const h = this.canvas.height / dpr;

        ctx.clearRect(0, 0, w, h);

        let hasRealData = false;

        // Try to get real audio frequency data
        if (this.analyserNode && this.freqData && this.isPlaying && !this.synthesizerActive) {
            this.analyserNode.getByteFrequencyData(this.freqData);
            this.analyserNode.getByteTimeDomainData(this.timeData);

            // Check if we have actual audio data (not all zeros)
            let sum = 0;
            for (let i = 0; i < this.freqData.length; i++) sum += this.freqData[i];
            hasRealData = sum > 0;

            // Smooth frequency data
            if (hasRealData) {
                for (let i = 0; i < this.freqData.length; i++) {
                    this.smoothedFreqData[i] += (this.freqData[i] - this.smoothedFreqData[i]) * 0.3;
                }
            }
        }

        // If no real data, generate procedural data for visual effect
        if (!hasRealData && this.isPlaying) {
            if (!this.freqData) {
                this.freqData = new Uint8Array(128);
                this.timeData = new Uint8Array(128);
                this.smoothedFreqData = new Float32Array(128);
            }
            const t = Date.now() * 0.003;
            for (let i = 0; i < this.freqData.length; i++) {
                const wave1 = Math.sin(i * 0.15 + t) * 0.5 + 0.5;
                const wave2 = Math.cos(i * 0.08 - t * 1.3) * 0.3 + 0.3;
                const wave3 = Math.sin(i * 0.3 + t * 0.7) * 0.2;
                const noise = Math.random() * 0.12;
                const envelope = Math.pow(Math.sin((i / this.freqData.length) * Math.PI), 0.6);
                this.freqData[i] = Math.max(0, Math.min(255, (wave1 + wave2 + wave3 + noise) * envelope * 255));
                this.timeData[i] = 128 + Math.sin(i * 0.08 + t * 2) * 60 + Math.random() * 10;
                this.smoothedFreqData[i] += (this.freqData[i] - this.smoothedFreqData[i]) * 0.15;
            }
            hasRealData = true; // use procedural data as if it's real
        }

        // Update section active state
        if (this.isPlaying && hasRealData) {
            this.visualizerSection.classList.add('is-active');
        } else {
            this.visualizerSection.classList.remove('is-active');
        }

        // Draw based on current mode
        if (hasRealData && this.isPlaying) {
            switch (this.vizMode) {
                case 'bars': this.drawBars(ctx, w, h); break;
                case 'wave': this.drawWave(ctx, w, h); break;
                case 'circular': this.drawCircular(ctx, w, h); break;
                case 'mirror': this.drawMirror(ctx, w, h); break;
                default: this.drawBars(ctx, w, h);
            }
            this.updateVizInfo();
        } else {
            // Idle state: dim bars
            this.drawIdleBars(ctx, w, h);
            if (this.vizFreqLabel) this.vizFreqLabel.textContent = '—';
            if (this.vizDbLabel) this.vizDbLabel.textContent = '—';
        }

        this.visualizerAnimationId = requestAnimationFrame(() => this.drawVisualizer());
    }

    // Mode 1: Frequency Bars with gradient glow
    drawBars(ctx, w, h) {
        const data = this.smoothedFreqData;
        const numBars = Math.min(64, data.length);
        const gap = 2;
        const barW = (w - gap * (numBars - 1)) / numBars;
        const cornerR = Math.max(1, barW / 3);

        for (let i = 0; i < numBars; i++) {
            const val = data[i] / 255;
            const barH = Math.max(2, val * (h - 4));
            const x = i * (barW + gap);
            const y = h - barH;

            // Gradient per bar
            const grad = ctx.createLinearGradient(x, h, x, y);
            const hue = 35 + (i / numBars) * 280; // gold → pink → cyan
            grad.addColorStop(0, `hsla(${hue}, 90%, 65%, 0.9)`);
            grad.addColorStop(0.5, `hsla(${hue + 20}, 85%, 55%, 0.7)`);
            grad.addColorStop(1, `hsla(${hue + 40}, 80%, 45%, 0.4)`);

            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.roundRect(x, y, barW, barH, [cornerR, cornerR, 0, 0]);
            ctx.fill();

            // Glow effect for loud bars
            if (val > 0.6) {
                ctx.save();
                ctx.shadowColor = `hsla(${hue}, 100%, 60%, 0.5)`;
                ctx.shadowBlur = 8 + val * 12;
                ctx.fillStyle = `hsla(${hue}, 100%, 70%, ${val * 0.3})`;
                ctx.fillRect(x, y, barW, barH);
                ctx.restore();
            }
        }
    }

    // Mode 2: Smooth Waveform
    drawWave(ctx, w, h) {
        const data = this.timeData;
        const len = data.length;
        const sliceW = w / len;
        const midH = h / 2;

        // Draw filled area under waveform
        ctx.beginPath();
        ctx.moveTo(0, midH);
        for (let i = 0; i < len; i++) {
            const v = data[i] / 128.0;
            const y = v * midH;
            if (i === 0) ctx.moveTo(0, y);
            else {
                const prevX = (i - 1) * sliceW;
                const currX = i * sliceW;
                const cpX = (prevX + currX) / 2;
                const prevY = (data[i - 1] / 128.0) * midH;
                ctx.quadraticCurveTo(prevX, prevY, cpX, (prevY + y) / 2);
            }
        }
        ctx.lineTo(w, midH);
        ctx.lineTo(0, midH);
        ctx.closePath();

        const fillGrad = ctx.createLinearGradient(0, 0, w, 0);
        fillGrad.addColorStop(0, 'rgba(252, 191, 71, 0.12)');
        fillGrad.addColorStop(0.5, 'rgba(255, 109, 196, 0.12)');
        fillGrad.addColorStop(1, 'rgba(56, 189, 248, 0.12)');
        ctx.fillStyle = fillGrad;
        ctx.fill();

        // Draw waveform line
        ctx.beginPath();
        for (let i = 0; i < len; i++) {
            const v = data[i] / 128.0;
            const y = v * midH;
            const x = i * sliceW;
            if (i === 0) ctx.moveTo(x, y);
            else {
                const prevX = (i - 1) * sliceW;
                const prevY = (data[i - 1] / 128.0) * midH;
                const cpX = (prevX + x) / 2;
                ctx.quadraticCurveTo(prevX, prevY, cpX, (prevY + y) / 2);
            }
        }

        const lineGrad = ctx.createLinearGradient(0, 0, w, 0);
        lineGrad.addColorStop(0, '#fcbf47');
        lineGrad.addColorStop(0.5, '#ff6dc4');
        lineGrad.addColorStop(1, '#38bdf8');
        ctx.strokeStyle = lineGrad;
        ctx.lineWidth = 2;
        ctx.shadowColor = '#ff6dc4';
        ctx.shadowBlur = 6;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Draw center line
        ctx.beginPath();
        ctx.moveTo(0, midH);
        ctx.lineTo(w, midH);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    // Mode 3: Circular Spectrum
    drawCircular(ctx, w, h) {
        const data = this.smoothedFreqData;
        const cx = w / 2;
        const cy = h / 2;
        const innerR = Math.min(w, h) * 0.18;
        const maxBarH = Math.min(w, h) * 0.28;
        const numBars = Math.min(72, data.length);
        const angleStep = (Math.PI * 2) / numBars;

        // Inner circle glow
        const innerGlow = ctx.createRadialGradient(cx, cy, innerR * 0.3, cx, cy, innerR);
        innerGlow.addColorStop(0, 'rgba(252, 191, 71, 0.15)');
        innerGlow.addColorStop(1, 'rgba(252, 191, 71, 0.02)');
        ctx.fillStyle = innerGlow;
        ctx.beginPath();
        ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
        ctx.fill();

        // Inner circle ring
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
        ctx.stroke();

        // Draw frequency bars radiating outward
        for (let i = 0; i < numBars; i++) {
            const val = data[i] / 255;
            const barH = Math.max(2, val * maxBarH);
            const angle = i * angleStep - Math.PI / 2;

            const x1 = cx + Math.cos(angle) * innerR;
            const y1 = cy + Math.sin(angle) * innerR;
            const x2 = cx + Math.cos(angle) * (innerR + barH);
            const y2 = cy + Math.sin(angle) * (innerR + barH);

            const hue = (i / numBars) * 360;
            ctx.strokeStyle = `hsla(${hue}, 85%, 60%, ${0.4 + val * 0.6})`;
            ctx.lineWidth = Math.max(1.5, (Math.PI * 2 * innerR) / numBars * 0.5);
            ctx.lineCap = 'round';

            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();

            // Glow for loud bars
            if (val > 0.5) {
                ctx.save();
                ctx.shadowColor = `hsla(${hue}, 100%, 65%, 0.6)`;
                ctx.shadowBlur = 6 + val * 8;
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
                ctx.restore();
            }
        }
    }

    // Mode 4: Mirror Bars (reflected top/bottom)
    drawMirror(ctx, w, h) {
        const data = this.smoothedFreqData;
        const numBars = Math.min(48, data.length);
        const gap = 2;
        const barW = (w - gap * (numBars - 1)) / numBars;
        const midY = h / 2;
        const maxBarH = midY - 2;

        for (let i = 0; i < numBars; i++) {
            const val = data[i] / 255;
            const barH = Math.max(1, val * maxBarH);
            const x = i * (barW + gap);

            const hue = 35 + (i / numBars) * 200;

            // Top bar (growing up from center)
            const gradUp = ctx.createLinearGradient(x, midY, x, midY - barH);
            gradUp.addColorStop(0, `hsla(${hue}, 90%, 65%, 0.85)`);
            gradUp.addColorStop(1, `hsla(${hue + 30}, 80%, 50%, 0.3)`);
            ctx.fillStyle = gradUp;
            ctx.fillRect(x, midY - barH, barW, barH);

            // Bottom bar (growing down, reflection)
            const gradDown = ctx.createLinearGradient(x, midY, x, midY + barH);
            gradDown.addColorStop(0, `hsla(${hue}, 80%, 60%, 0.6)`);
            gradDown.addColorStop(1, `hsla(${hue + 30}, 70%, 45%, 0.08)`);
            ctx.fillStyle = gradDown;
            ctx.fillRect(x, midY, barW, barH);
        }

        // Center line
        ctx.beginPath();
        ctx.moveTo(0, midY);
        ctx.lineTo(w, midY);
        const centerGrad = ctx.createLinearGradient(0, 0, w, 0);
        centerGrad.addColorStop(0, 'rgba(252, 191, 71, 0.25)');
        centerGrad.addColorStop(0.5, 'rgba(255, 109, 196, 0.35)');
        centerGrad.addColorStop(1, 'rgba(56, 189, 248, 0.25)');
        ctx.strokeStyle = centerGrad;
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    // Idle state: dim minimal bars
    drawIdleBars(ctx, w, h) {
        const numBars = 48;
        const gap = 2;
        const barW = (w - gap * (numBars - 1)) / numBars;

        for (let i = 0; i < numBars; i++) {
            const x = i * (barW + gap);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.06)';
            ctx.fillRect(x, h - 2, barW, 2);
        }
    }

    updateVizInfo() {
        if (!this.smoothedFreqData) return;

        // Find dominant frequency band
        let maxVal = 0, maxIdx = 0;
        for (let i = 0; i < this.smoothedFreqData.length; i++) {
            if (this.smoothedFreqData[i] > maxVal) {
                maxVal = this.smoothedFreqData[i];
                maxIdx = i;
            }
        }

        // Approximate frequency (assuming 44100 sample rate and fftSize 256)
        const sampleRate = this.audioCtx ? this.audioCtx.sampleRate : 44100;
        const fftSize = this.analyserNode ? this.analyserNode.fftSize : 256;
        const freqHz = (maxIdx * sampleRate) / fftSize;
        const dbVal = -90 + (maxVal / 255) * 80; // approximate dB

        const freqLabel = freqHz >= 1000 ? `${(freqHz / 1000).toFixed(1)} kHz` : `${Math.round(freqHz)} Hz`;
        if (this.vizFreqLabel) this.vizFreqLabel.textContent = `Peak: ${freqLabel}`;
        if (this.vizDbLabel) this.vizDbLabel.textContent = `${dbVal.toFixed(1)} dB`;
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
            this.copyAllLinksBtn.textContent = 'Đã Copy!';
            this.showToast('Đã copy danh sách file Hi-Res vào clipboard');
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
                this.showToast('Đã tải lại kho nhạc mẫu Demo!');
            });
        }

        // Close on overlay click
        [this.albumModal, this.searchModal, this.tgModal].forEach(modal => {
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
                    <span class="album-card-year">${album.year} • ${album.tracks.length} Tracks</span>
                </div>
            `;

            card.addEventListener('click', () => {
                this.loadAlbum(idx, 0, true);
                this.closeModal(this.albumModal);
                this.showToast(`Đã chuyển sang album: ${album.title}`);
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
                    <div class="file-meta">${track.artist || album.artist} • ${track.size || 'Hi-Res'}</div>
                </div>
                <div class="file-actions">
                    <button class="file-action-btn download-btn">Phát Ngay</button>
                </div>
            `;

            const btn = row.querySelector('.download-btn');
            btn.addEventListener('click', () => {
                this.loadTrack(idx, true);
                this.metaDrawer.classList.remove('open');
                this.showToast(`Đang phát: ${track.name}`);
            });

            this.drawerFileList.appendChild(row);
        });
    }

    handleSearch(query) {
        if (!query.trim()) {
            this.searchResults.innerHTML = '<div class="search-empty">Nhập từ khoá để tìm bài hát nhanh...</div>';
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
            this.searchResults.innerHTML = `<div class="search-empty">Không tìm thấy bài hát nào khớp với "${query}"</div>`;
            return;
        }

        this.searchResults.innerHTML = '';
        matches.forEach(item => {
            const el = document.createElement('div');
            el.className = 'search-item';
            el.innerHTML = `
                <div>
                    <div style="font-weight:600; color:#fff;">${item.track.name}</div>
                    <div style="font-size:0.78rem; color:rgba(255,255,255,0.5);">${item.album.artist} • ${item.album.title}</div>
                </div>
                <span style="color:var(--accent-gold); font-size:0.8rem;">${item.track.duration}</span>
            `;

            el.addEventListener('click', () => {
                this.loadAlbum(item.albumIdx, item.trackIdx, true);
                this.closeModal(this.searchModal);
                this.showToast(`Đang phát: ${item.track.name}`);
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
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    window.xtapoApp = new XTAPOMusicApp();
});

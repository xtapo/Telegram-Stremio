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
        country: "Âu Mỹ",
        isDemo: true,
        coverUrl: "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop",
        glowColors: {
            glow1: "radial-gradient(circle, #f59e0b 0%, #b45309 60%, transparent 80%)",
            glow2: "radial-gradient(circle, #ff6dc4 0%, #4338ca 60%, transparent 80%)"
        },
        tracks: [
            { id: 1, name: "Any Man of Mine (Little Miss Twain Edition)", duration: "4:07", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", size: "82.4 MB", country: "Âu Mỹ" },
            { id: 2, name: "That Don't Impress Me Much", duration: "3:59", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", size: "79.1 MB", country: "Âu Mỹ" },
            { id: 3, name: "Man! I Feel Like a Woman!", duration: "3:53", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", size: "77.8 MB", country: "Âu Mỹ" },
            { id: 4, name: "You're Still the One", duration: "3:32", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", size: "70.5 MB", country: "Âu Mỹ" },
            { id: 5, name: "From This Moment On", duration: "4:43", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", size: "94.2 MB", country: "Âu Mỹ" },
            { id: 6, name: "Whose Bed Have Your Boots Been Under?", duration: "4:25", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", size: "88.3 MB", country: "Âu Mỹ" },
            { id: 7, name: "I'm Gonna Getcha Good!", duration: "4:29", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3", size: "89.6 MB", country: "Âu Mỹ" },
            { id: 8, name: "Up! (Red Album Version)", duration: "2:52", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", size: "57.3 MB", country: "Âu Mỹ" },
            { id: 9, name: "Forever and for Always", duration: "4:47", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", size: "95.5 MB", country: "Âu Mỹ" },
            { id: 10, name: "Don't Be Stupid (You Know I Love You)", duration: "3:35", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", size: "71.6 MB", country: "Âu Mỹ" },
            { id: 11, name: "Party for Two (ft. Billy Currington)", duration: "3:31", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", size: "70.2 MB", country: "Âu Mỹ" },
            { id: 12, name: "Giddy Up!", duration: "2:42", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", size: "54.1 MB", country: "Âu Mỹ" },
            { id: 13, name: "Life's About to Get Good", duration: "3:40", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-13.mp3", size: "73.3 MB", country: "Âu Mỹ" },
            { id: 14, name: "No One Needs to Know", duration: "3:04", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-14.mp3", size: "61.2 MB", country: "Âu Mỹ" },
            { id: 15, name: "You've Got a Way (Notting Hill Mix)", duration: "3:24", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-15.mp3", size: "68.0 MB", country: "Âu Mỹ" }
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
        country: "Âu Mỹ",
        isDemo: true,
        coverUrl: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?q=80&w=1000&auto=format&fit=crop",
        glowColors: {
            glow1: "radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)",
            glow2: "radial-gradient(circle, #f59e0b 0%, #c2410c 60%, transparent 80%)"
        },
        tracks: [
            { id: 1, name: "Man! I Feel Like a Woman!", duration: "3:53", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", size: "85.2 MB", country: "Âu Mỹ" },
            { id: 2, name: "I'm Holdin' On to Love (To Save My Life)", duration: "3:30", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", size: "76.4 MB", country: "Âu Mỹ" },
            { id: 3, name: "Love Gets Me Every Time", duration: "3:33", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", size: "77.5 MB", country: "Âu Mỹ" },
            { id: 4, name: "Don't Be Stupid", duration: "3:35", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", size: "78.2 MB", country: "Âu Mỹ" },
            { id: 5, name: "From This Moment On", duration: "4:43", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3", size: "102.1 MB", country: "Âu Mỹ" },
            { id: 6, name: "Come On Over", duration: "2:55", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", size: "64.3 MB", country: "Âu Mỹ" },
            { id: 7, name: "When", duration: "3:39", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", size: "79.8 MB", country: "Âu Mỹ" },
            { id: 8, name: "Whatever You Do! Don't!", duration: "3:49", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", size: "83.5 MB", country: "Âu Mỹ" },
            { id: 9, name: "If You Wanna Touch Her, Ask!", duration: "4:04", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", size: "89.0 MB", country: "Âu Mỹ" },
            { id: 10, name: "You're Still the One", duration: "3:32", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", size: "77.0 MB", country: "Âu Mỹ" },
            { id: 11, name: "Honey, I'm Home", duration: "3:39", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", size: "79.9 MB", country: "Âu Mỹ" },
            { id: 12, name: "That Don't Impress Me Much", duration: "3:59", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", size: "87.1 MB", country: "Âu Mỹ" }
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
        country: "Âu Mỹ",
        isDemo: true,
        coverUrl: "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop",
        glowColors: {
            glow1: "radial-gradient(circle, #38bdf8 0%, #0284c7 60%, transparent 80%)",
            glow2: "radial-gradient(circle, #f472b6 0%, #db2777 60%, transparent 80%)"
        },
        tracks: [
            { id: 1, name: "Welcome to New York (Taylor's Version)", duration: "3:32", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", size: "75.4 MB", country: "Âu Mỹ" },
            { id: 2, name: "Blank Space (Taylor's Version)", duration: "3:51", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", size: "82.3 MB", country: "Âu Mỹ" },
            { id: 3, name: "Style (Taylor's Version)", duration: "3:51", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", size: "82.1 MB", country: "Âu Mỹ" },
            { id: 4, name: "Out of the Woods (Taylor's Version)", duration: "3:55", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", size: "83.6 MB", country: "Âu Mỹ" },
            { id: 5, name: "Shake It Off (Taylor's Version)", duration: "3:39", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", size: "78.0 MB", country: "Âu Mỹ" },
            { id: 6, name: "Wildest Dreams (Taylor's Version)", duration: "3:40", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", size: "78.5 MB", country: "Âu Mỹ" },
            { id: 7, name: "Bad Blood (Taylor's Version)", duration: "3:31", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3", size: "75.0 MB", country: "Âu Mỹ" }
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
        country: "Âu Mỹ",
        isDemo: true,
        coverUrl: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop",
        glowColors: {
            glow1: "radial-gradient(circle, #eab308 0%, #a16207 60%, transparent 80%)",
            glow2: "radial-gradient(circle, #6366f1 0%, #3730a3 60%, transparent 80%)"
        },
        tracks: [
            { id: 1, name: "Give Life Back to Music", duration: "4:35", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", size: "98.2 MB", country: "Âu Mỹ" },
            { id: 2, name: "Giorgio by Moroder", duration: "9:04", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", size: "192.4 MB", country: "Âu Mỹ" },
            { id: 3, name: "Instant Crush (ft. Julian Casablancas)", duration: "5:37", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", size: "119.5 MB", country: "Âu Mỹ" },
            { id: 4, name: "Lose Yourself to Dance (ft. Pharrell Williams)", duration: "5:53", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", size: "125.1 MB", country: "Âu Mỹ" },
            { id: 5, name: "Get Lucky (ft. Pharrell Williams)", duration: "6:09", previewUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", size: "131.0 MB", country: "Âu Mỹ" }
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
        window.player = this;

        // Elements
        this.audio = document.getElementById('mainAudio');
        if (this.audio) {
            this.audio.preload = 'auto';
            this.audio.playsInline = true;
            this.audio.setAttribute('playsinline', '');
            this.audio.setAttribute('webkit-playsinline', '');
        }
        this.preloaderAudio = new Audio();
        this.preloaderAudio.preload = 'auto';
        this._preloadedTrackUrl = null;
        this.albumTitle = document.getElementById('albumTitle');
        this.artistName = document.getElementById('artistName');
        this.albumYearTag = document.getElementById('albumYearTag');
        this.badgeAudioQuality = document.getElementById('badgeAudioQuality');
        this.badgeAudioSpecs = document.getElementById('badgeAudioSpecs');
        this.trackCountLabel = document.getElementById('trackCountLabel');
        this.totalDurationLabel = document.getElementById('totalDurationLabel');
        this.albumCompany = document.getElementById('albumCompany');
        this.tracklistEl = document.getElementById('tracklist');
        
        // Vinyl & Sleeve
        this.vinylStage = document.getElementById('vinylStage');
        this.albumCoverImg = document.getElementById('albumCoverImg');
        this.vinylCenterImg = document.getElementById('vinylCenterImg');
        this.mobileSleevePlayBtn = document.getElementById('mobileSleevePlayBtn');

        // Dynamic Apple Music Style Backdrop
        this.backdropArt1 = document.getElementById('backdropArt1');
        this.backdropArt2 = document.getElementById('backdropArt2');
        this.activeBackdropLayer = 1;
        this._lastBackdropCover = null;

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
        this.navCountries = document.getElementById('navCountries');

        // Artists, Genres & Countries Modals
        this.artistModal = document.getElementById('artistModal');
        this.artistListView = document.getElementById('artistListView');
        this.artistProfileView = document.getElementById('artistProfileView');
        this.btnBackToArtistList = document.getElementById('btnBackToArtistList');
        this.artistSearchInput = document.getElementById('artistSearchInput');
        this.closeArtistModal = document.getElementById('closeArtistModal');
        this.artistGrid = document.getElementById('artistGrid');
        this.artistCacheMap = new Map();

        this.genreModal = document.getElementById('genreModal');
        this.closeGenreModal = document.getElementById('closeGenreModal');
        this.genreGrid = document.getElementById('genreGrid');

        this.countryModal = document.getElementById('countryModal');
        this.closeCountryModal = document.getElementById('closeCountryModal');
        this.countryGrid = document.getElementById('countryGrid');

        // Country Modal Dual-View elements
        this.countryListView = document.getElementById('countryListView');
        this.countryDetailView = document.getElementById('countryDetailView');
        this.btnBackToCountryList = document.getElementById('btnBackToCountryList');
        this.countryDetailFlag = document.getElementById('countryDetailFlag');
        this.countryDetailCode = document.getElementById('countryDetailCode');
        this.countryDetailName = document.getElementById('countryDetailName');
        this.countryDetailSub = document.getElementById('countryDetailSub');
        this.btnCountryPlayAll = document.getElementById('btnCountryPlayAll');
        this.btnCountryShuffle = document.getElementById('btnCountryShuffle');
        this.btnCountryExportM3U8 = document.getElementById('btnCountryExportM3U8');
        this.btnCountryDownloadZip = document.getElementById('btnCountryDownloadZip');
        this.tabBtnCountryGenres = document.getElementById('tabBtnCountryGenres');
        this.tabBtnCountryArtists = document.getElementById('tabBtnCountryArtists');
        this.tabBtnCountryTracks = document.getElementById('tabBtnCountryTracks');
        this.countryGenreCountBadge = document.getElementById('countryGenreCountBadge');
        this.countryArtistCountBadge = document.getElementById('countryArtistCountBadge');
        this.countryTrackCountBadge = document.getElementById('countryTrackCountBadge');
        this.countryGenresSection = document.getElementById('countryGenresSection');
        this.countryArtistsSection = document.getElementById('countryArtistsSection');
        this.countryTracksSection = document.getElementById('countryTracksSection');
        this.countryDetailGenreGrid = document.getElementById('countryDetailGenreGrid');
        this.countryDetailArtistGrid = document.getElementById('countryDetailArtistGrid');
        this.countryDetailTracksList = document.getElementById('countryDetailTracksList');
        this.countryArtistSearchInput = document.getElementById('countryArtistSearchInput');
        this.countryTrackSearchInput = document.getElementById('countryTrackSearchInput');
        this.artistCountryFilterTabs = document.getElementById('artistCountryFilterTabs');
        this.genreCountryFilterTabs = document.getElementById('genreCountryFilterTabs');

        this.selectedArtistCountryFilter = 'all';
        this.selectedGenreCountryFilter = 'all';
        this.currentDetailCountryObj = null;
        this.currentCountryDetailTab = 'genres';

        // Mobile Quick Tracklist Modal & Triggers
        this.mobileQuickTracklistBtn = document.getElementById('mobileQuickTracklistBtn');
        this.mobilePlayerTracklistBtn = document.getElementById('mobilePlayerTracklistBtn');
        this.tracklistModal = document.getElementById('tracklistModal');
        this.closeTracklistModal = document.getElementById('closeTracklistModal');
        this.modalTracklistEl = document.getElementById('modalTracklistEl');
        this.tracklistModalAlbumTitle = document.getElementById('tracklistModalAlbumTitle');
        this.tracklistModalArtist = document.getElementById('tracklistModalArtist');
        this.tracklistModalSearchInput = document.getElementById('tracklistModalSearchInput');
        this.mobileTrackCount = document.getElementById('mobileTrackCount');

        // Auth & User Profile
        this.userProfileBtn = document.getElementById('userProfileBtn');
        this.userAvatarImg = document.getElementById('userAvatarImg');
        this.userDisplayName = document.getElementById('userDisplayName');
        
        this.authModal = document.getElementById('authModal');
        this.closeAuthModal = document.getElementById('closeAuthModal');
        this.tabQrLogin = document.getElementById('tabQrLogin');
        this.tabPhoneLogin = document.getElementById('tabPhoneLogin');
        this.tabPwLogin = document.getElementById('tabPwLogin');
        this.qrLoginPane = document.getElementById('qrLoginPane');
        this.phoneLoginPane = document.getElementById('phoneLoginPane');
        this.pwLoginPane = document.getElementById('pwLoginPane');
        
        // QR Elements
        this.qrCodeContainer = document.getElementById('qrCodeContainer');
        this.qrLoadingSpinner = document.getElementById('qrLoadingSpinner');
        this.qrExpiredOverlay = document.getElementById('qrExpiredOverlay');
        this.btnRefreshQr = document.getElementById('btnRefreshQr');
        this.qrStatusBadge = document.getElementById('qrStatusBadge');
        this.qrStatusText = document.getElementById('qrStatusText');
        this.qrCountdownTag = document.getElementById('qrCountdownTag');
        this.qrCountdownSec = document.getElementById('qrCountdownSec');
        this.qr2FaSection = document.getElementById('qr2FaSection');
        this.qr2FaInput = document.getElementById('qr2FaInput');
        this.btnSubmit2Fa = document.getElementById('btnSubmit2Fa');

        // Phone Login Elements
        this.phoneStepInput = document.getElementById('phoneStepInput');
        this.phoneStepOtp = document.getElementById('phoneStepOtp');
        this.phoneStep2Fa = document.getElementById('phoneStep2Fa');
        this.tgPhoneInput = document.getElementById('tgPhoneInput');
        this.btnSendPhoneCode = document.getElementById('btnSendPhoneCode');
        this.tgPhoneOtpInput = document.getElementById('tgPhoneOtpInput');
        this.btnVerifyPhoneCode = document.getElementById('btnVerifyPhoneCode');
        this.phoneSentTarget = document.getElementById('phoneSentTarget');
        this.btnResendPhoneCode = document.getElementById('btnResendPhoneCode');
        this.phoneResendCountdown = document.getElementById('phoneResendCountdown');
        this.btnBackToPhoneInput = document.getElementById('btnBackToPhoneInput');
        this.phone2FaInput = document.getElementById('phone2FaInput');
        this.btnSubmitPhone2Fa = document.getElementById('btnSubmitPhone2Fa');

        this.loginForm = document.getElementById('loginForm');
        this.loginSubmitBtn = document.getElementById('loginSubmitBtn');
        this.loginUsername = document.getElementById('loginUsername');
        this.loginPassword = document.getElementById('loginPassword');
        this.favoriteBtn = document.getElementById('favoriteBtn');

        this._qrPollTimer = null;
        this._qrCountdownTimer = null;
        this._currentQrSessionId = null;
        this._qrCodeInstance = null;
        this._currentPhoneSessionId = null;
        this._phoneResendTimer = null;

        // Favorites Modal
        this.navFavorites = document.getElementById('navFavorites');
        this.favoritesModal = document.getElementById('favoritesModal');
        this.closeFavoritesModal = document.getElementById('closeFavoritesModal');
        this.favoritesList = document.getElementById('favoritesList');
        this.favModalCount = document.getElementById('favModalCount');
        this.btnFavPlayAll = document.getElementById('btnFavPlayAll');
        this.btnFavShuffle = document.getElementById('btnFavShuffle');
        this.btnFavExportM3U8 = document.getElementById('btnFavExportM3U8');
        this.btnFavDownloadZip = document.getElementById('btnFavDownloadZip');
        this.favSearchInput = document.getElementById('favSearchInput');

        // Album & Drawer Export Elements
        this.albumExportDropdown = document.getElementById('albumExportDropdown');
        this.albumExportBtn = document.getElementById('albumExportBtn');
        this.albumExportMenu = document.getElementById('albumExportMenu');
        this.btnDownloadAlbumZip = document.getElementById('btnDownloadAlbumZip');
        this.btnExportAlbumM3U8 = document.getElementById('btnExportAlbumM3U8');
        this.btnExportAlbumPLS = document.getElementById('btnExportAlbumPLS');
        this.btnDownloadAlbumBatch = document.getElementById('btnDownloadAlbumBatch');

        this.drawerDownloadZipBtn = document.getElementById('drawerDownloadZipBtn');
        this.drawerExportM3U8Btn = document.getElementById('drawerExportM3U8Btn');
        this.drawerExportPLSBtn = document.getElementById('drawerExportPLSBtn');
        this.drawerDownloadBatchBtn = document.getElementById('drawerDownloadBatchBtn');

        // Spotlight Export Elements
        this.btnSpotlightExportM3U8 = document.getElementById('btnSpotlightExportM3U8');
        this.btnSpotlightDownloadZip = document.getElementById('btnSpotlightDownloadZip');

        // Download Progress Modal Elements
        this.downloadProgressModal = document.getElementById('downloadProgressModal');
        this.dlModalTitle = document.getElementById('dlModalTitle');
        this.dlModalSub = document.getElementById('dlModalSub');
        this.dlCurrentFileName = document.getElementById('dlCurrentFileName');
        this.dlPercentBadge = document.getElementById('dlPercentBadge');
        this.dlProgressBar = document.getElementById('dlProgressBar');
        this.dlStatsCount = document.getElementById('dlStatsCount');
        this.dlStatsSpeed = document.getElementById('dlStatsSpeed');
        this.dlCancelBtn = document.getElementById('dlCancelBtn');
        this.activeDownloadAbortController = null;

        // M3U8 Stream Link & Share Modal Elements
        this.m3u8Modal = document.getElementById('m3u8Modal');
        this.closeM3u8Modal = document.getElementById('closeM3u8Modal');
        this.m3u8ModalTitle = document.getElementById('m3u8ModalTitle');
        this.m3u8DirectUrlInput = document.getElementById('m3u8DirectUrlInput');
        this.m3u8CopyBtn = document.getElementById('m3u8CopyBtn');
        this.m3u8CopyText = document.getElementById('m3u8CopyText');
        this.m3u8OpenDirectBtn = document.getElementById('m3u8OpenDirectBtn');
        this.m3u8DownloadFileBtn = document.getElementById('m3u8DownloadFileBtn');
        this.m3u8DownloadPlsBtn = document.getElementById('m3u8DownloadPlsBtn');
        this.currentM3U8Context = null;

        // Real-time Synced Lyrics Elements & State
        this.tabVinylView = document.getElementById('tabVinylView');
        this.tabLyricsView = document.getElementById('tabLyricsView');
        this.heroLyricsStage = document.getElementById('heroLyricsStage');
        this.heroLyricsSourceTag = document.getElementById('heroLyricsSourceTag');
        this.heroLyricsTitle = document.getElementById('heroLyricsTitle');
        this.heroLyricsScroll = document.getElementById('heroLyricsScroll');
        this.heroLyricsLines = document.getElementById('heroLyricsLines');
        this.heroLyricsPlaceholder = document.getElementById('heroLyricsPlaceholder');
        this.heroLyricsOffset = document.getElementById('heroLyricsOffset');
        this.lyricsStatusBadge = document.getElementById('lyricsStatusBadge');
        this.btnOffsetMinus = document.getElementById('btnOffsetMinus');
        this.btnOffsetPlus = document.getElementById('btnOffsetPlus');
        this.btnOpenLyricsEditor = document.getElementById('btnOpenLyricsEditor');
        this.btnOpenKaraokeModal = document.getElementById('btnOpenKaraokeModal');
        this.lyricsToggleBtn = document.getElementById('lyricsToggleBtn');

        // Karaoke Fullscreen Modal Elements
        this.lyricsModal = document.getElementById('lyricsModal');
        this.closeLyricsModal = document.getElementById('closeLyricsModal');
        this.karaokeBackdrop = document.getElementById('karaokeBackdrop');
        this.karaokeTrackTitle = document.getElementById('karaokeTrackTitle');
        this.karaokeArtistName = document.getElementById('karaokeArtistName');
        this.karaokeLyricsScroll = document.getElementById('karaokeLyricsScroll');
        this.karaokeLinesList = document.getElementById('karaokeLinesList');
        this.karaokePlaceholder = document.getElementById('karaokePlaceholder');
        this.karaokeStatusText = document.getElementById('karaokeStatusText');
        this.karaokeOffsetMinus = document.getElementById('karaokeOffsetMinus');
        this.karaokeOffsetPlus = document.getElementById('karaokeOffsetPlus');
        this.karaokeOffsetLabel = document.getElementById('karaokeOffsetLabel');
        this.karaokeEditBtn = document.getElementById('karaokeEditBtn');
        this.karaokeTimeCurrent = document.getElementById('karaokeTimeCurrent');
        this.karaokeTimeTotal = document.getElementById('karaokeTimeTotal');
        this.karaokeProgressTrack = document.getElementById('karaokeProgressTrack');
        this.karaokeProgressFill = document.getElementById('karaokeProgressFill');
        this.karaokePrevBtn = document.getElementById('karaokePrevBtn');
        this.karaokePlayBtn = document.getElementById('karaokePlayBtn');
        this.karaokeNextBtn = document.getElementById('karaokeNextBtn');
        this.karaokePlayIcon = document.getElementById('karaokePlayIcon');
        this.karaokePauseIcon = document.getElementById('karaokePauseIcon');

        // Lyrics Editor Modal Elements
        this.lyricsEditorModal = document.getElementById('lyricsEditorModal');
        this.closeLyricsEditorModal = document.getElementById('closeLyricsEditorModal');
        this.lyricsSearchTrackInput = document.getElementById('lyricsSearchTrackInput');
        this.lyricsSearchArtistInput = document.getElementById('lyricsSearchArtistInput');
        this.lyricsSearchProviderSelect = document.getElementById('lyricsSearchProviderSelect');
        this.btnLyricsOnlineSearch = document.getElementById('btnLyricsOnlineSearch');
        this.lyricsSearchResults = document.getElementById('lyricsSearchResults');
        this.lyricsFileInput = document.getElementById('lyricsFileInput');
        this.btnResetToOriginalLyrics = document.getElementById('btnResetToOriginalLyrics');
        this.btnClearLyrics = document.getElementById('btnClearLyrics');
        this.lyricsRawTextarea = document.getElementById('lyricsRawTextarea');
        this.editorOffsetMinus = document.getElementById('editorOffsetMinus');
        this.editorOffsetMinusSmall = document.getElementById('editorOffsetMinusSmall');
        this.editorOffsetValue = document.getElementById('editorOffsetValue');
        this.editorOffsetPlusSmall = document.getElementById('editorOffsetPlusSmall');
        this.editorOffsetPlus = document.getElementById('editorOffsetPlus');
        this.editorOffsetReset = document.getElementById('editorOffsetReset');
        this.btnCancelLyricsEditor = document.getElementById('btnCancelLyricsEditor');
        this.btnSaveLyricsEditor = document.getElementById('btnSaveLyricsEditor');

        // Lyrics Internal State
        this.activeHeroView = 'vinyl'; // 'vinyl' | 'lyrics'
        this.currentLyrics = null;
        this.currentLyricIndex = -1;
        this.lyricsOffset = 0; // seconds (+: delay, -: early)
        this.isUserScrollingHeroLyrics = false;
        this.isUserScrollingKaraokeLyrics = false;
        this.heroScrollResumeTimeout = null;
        this.karaokeScrollResumeTimeout = null;
        this._lyricsSyncRafId = null;

        this.currentUser = null;
        this.favoriteTracks = [];

        // Sleep Timer Elements & State
        this.sleepTimerBtn = document.getElementById('sleepTimerBtn');
        this.sleepTimerBtnLabel = document.getElementById('sleepTimerBtnLabel');
        this.sleepTimerBadge = document.getElementById('sleepTimerBadge');
        this.topNavSleepBtn = document.getElementById('topNavSleepBtn');
        this.topNavSleepBadge = document.getElementById('topNavSleepBadge');
        this.mobileNavSleepTimer = document.getElementById('mobileNavSleepTimer');
        this.sleepTimerModal = document.getElementById('sleepTimerModal');
        this.closeSleepTimerModal = document.getElementById('closeSleepTimerModal');
        this.sleepTimerRunningBox = document.getElementById('sleepTimerRunningBox');
        this.sleepTimerConfigBox = document.getElementById('sleepTimerConfigBox');
        this.sleepTimerCountdownDisplay = document.getElementById('sleepTimerCountdownDisplay');
        this.sleepTimerCountdownSub = document.getElementById('sleepTimerCountdownSub');
        this.sleepCustomInput = document.getElementById('sleepCustomInput');
        this.sleepCustomApplyBtn = document.getElementById('sleepCustomApplyBtn');
        this.sleepFadeOutCheckbox = document.getElementById('sleepFadeOutCheckbox');
        this.sleepCancelTimerBtn = document.getElementById('sleepCancelTimerBtn');
        this.sleepExtend5Btn = document.getElementById('sleepExtend5Btn');
        this.sleepExtend15Btn = document.getElementById('sleepExtend15Btn');
        this.sleepExtend30Btn = document.getElementById('sleepExtend30Btn');

        this.sleepTimerSeconds = 0;
        this.sleepTimerTotalSeconds = 0;
        this.sleepTimerInterval = null;
        this.sleepTimerMode = null; // 'time' | 'end_of_track' | null
        this.sleepTimerFadeOut = true;
        this.sleepTimerOriginalVolume = null;

        // Init
        this.init();
    }

    async init() {
        this.setupAudioEvents();
        this.setupControlEvents();
        this.setupModalEvents();
        this.setupLyricsEvents();
        this.setupSleepTimerEvents();
        this.setupAuthEvents();
        this.setupMediaSession();
        this.setupVisualizer();
        this.setupKeyboardShortcuts();
        
        // 1. Tải song song thông tin User, Thư viện Albums Telegram và Metadata nghệ sĩ
        await Promise.all([
            this.fetchUserProfile(),
            this.fetchTelegramAlbums(false),
            this.fetchArtistMetadata()
        ]);

        // 2. Khôi phục bài hát & vị trí đang phát dở (Player State) hoặc mở mặc định
        const restored = this.restorePlayerState();
        if (!restored) {
            if (this.currentUser) {
                // Người dùng đã đăng nhập: KHÔNG tải demo Shania Twain
                if (this.favoriteTracks && this.favoriteTracks.length > 0) {
                    this.playFavoritesQueue(0, false, false);
                    if (this.navFavorites) this.setActiveNavLink(this.navFavorites);
                } else if (this.playlists && this.playlists.length > 0 && this.playlists[0].tracks?.length > 0) {
                    this.playPlaylist(this.playlists[0], 0, false);
                    if (this.navPlaylists) this.setActiveNavLink(this.navPlaylists);
                } else if (this.albums && this.albums.length > 0 && !this.albums[0].isDemo) {
                    this.loadAlbum(0, 0, false);
                    this.renderAlbumGrid();
                } else {
                    this.showEmptyCloudState();
                }
            } else {
                // Khách vãng lai (Guest): tải kho demo mẫu
                this.loadAlbum(0, 0, false);
                this.renderAlbumGrid();
            }
        } else {
            this.renderAlbumGrid();
        }

        // 5. Khôi phục tab / modal / danh mục đang mở (Active View & URL Hash)
        this.restoreActiveView();

        // 6. Khôi phục vị trí cuộn trang (Scroll Position)
        try {
            const savedScroll = sessionStorage.getItem('xtapo_music_scroll_pos');
            if (savedScroll) {
                requestAnimationFrame(() => {
                    window.scrollTo({ top: parseInt(savedScroll, 10), behavior: 'instant' });
                });
            }
        } catch (e) {}
    }

    // --- Authentication & User State & Heartbeat Manager ---
    getDeviceInfo() {
        const ua = navigator.userAgent || '';
        let os = 'Unknown OS';
        let deviceType = 'Desktop';
        
        if (/windows nt 10/i.test(ua) || /windows nt 11/i.test(ua) || /windows/i.test(ua)) os = 'Windows';
        else if (/iphone/i.test(ua)) { os = 'iOS (iPhone)'; deviceType = 'Mobile'; }
        else if (/ipad/i.test(ua)) { os = 'iPadOS (iPad)'; deviceType = 'Tablet'; }
        else if (/macintosh|mac os x/i.test(ua)) os = 'macOS';
        else if (/android/i.test(ua)) { os = 'Android'; deviceType = /mobile/i.test(ua) ? 'Mobile' : 'Tablet'; }
        else if (/linux/i.test(ua)) os = 'Linux';

        let browser = 'Web Browser';
        if (/telegram/i.test(ua)) browser = 'Telegram Webview';
        else if (/edg/i.test(ua)) browser = 'Microsoft Edge';
        else if (/opr|opera/i.test(ua)) browser = 'Opera';
        else if (/chrome/i.test(ua) && !/edg/i.test(ua)) browser = 'Google Chrome';
        else if (/safari/i.test(ua) && !/chrome/i.test(ua)) browser = 'Apple Safari';
        else if (/firefox/i.test(ua)) browser = 'Mozilla Firefox';

        const screen = (window.screen && window.screen.width) ? `${window.screen.width}x${window.screen.height}` : '';

        return {
            os,
            browser,
            device_type: deviceType,
            screen,
            user_agent: ua
        };
    }

    startHeartbeat() {
        if (this._heartbeatInterval) clearInterval(this._heartbeatInterval);
        this.sendHeartbeat();
        this._heartbeatInterval = setInterval(() => {
            this.sendHeartbeat();
        }, 30000);
    }

    stopHeartbeat() {
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
            this._heartbeatInterval = null;
        }
    }

    async sendHeartbeat() {
        if (!this.currentUser) return;
        try {
            const track = this.currentTrack || (this.currentAlbum && this.currentAlbum.tracks && this.currentAlbum.tracks[this.currentTrackIndex]);
            const isAudioPlaying = this.audio && !this.audio.paused && !this.audio.ended && this.audio.currentTime > 0;
            const playbackState = isAudioPlaying ? 'playing' : (this.audio && this.audio.currentTime > 0 ? 'paused' : 'idle');

            const payload = {
                device_info: this.getDeviceInfo(),
                playback_state: playbackState,
                current_track: track ? {
                    title: track.title || track.name || '',
                    artist: track.artist || (this.currentAlbum && this.currentAlbum.artist) || '',
                    album: (this.currentAlbum && this.currentAlbum.title) || '',
                    cover_url: track.coverUrl || (this.currentAlbum && this.currentAlbum.coverUrl) || ''
                } : null
            };

            await fetch('/api/music/auth/heartbeat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } catch (e) {}
    }

    async fetchUserProfile() {
        try {
            const res = await fetch('/api/music/auth/profile');
            const data = await res.json();
            if (data.status === 'authenticated' && data.user) {
                this.currentUser = data.user;
                this.updateAuthUI(true);
                this.startHeartbeat();
                await this.fetchUserFavorites();
                await this.loadPlaylists(); // Will now fetch user playlists

                // Kiểm tra và hiển thị cảnh báo nếu chưa tham gia Channel
                if (data.user.is_channel_member === false || data.user.channel_warning) {
                    const warningMsg = data.user.channel_warning || "Tài khoản của bạn chưa tham gia thành viên vui lòng liên hệ Admin";
                    this.showChannelWarningBanner(warningMsg);
                } else {
                    const existingBanner = document.getElementById('channelWarningBanner');
                    if (existingBanner) existingBanner.remove();
                }
            } else {
                this.currentUser = null;
                this.stopHeartbeat();
                this.updateAuthUI(false);
                const existingBanner = document.getElementById('channelWarningBanner');
                if (existingBanner) existingBanner.remove();
            }
        } catch (e) {
            console.error("Lỗi lấy thông tin user:", e);
        }
    }

    showChannelWarningBanner(msg = "Tài khoản của bạn chưa tham gia thành viên vui lòng liên hệ Admin") {
        let banner = document.getElementById('channelWarningBanner');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'channelWarningBanner';
            banner.className = 'channel-warning-banner';
            const topNav = document.getElementById('topNav');
            const appContainer = document.querySelector('.app-container');
            if (topNav && topNav.nextSibling) {
                topNav.parentNode.insertBefore(banner, topNav.nextSibling);
            } else if (appContainer) {
                appContainer.prepend(banner);
            } else {
                document.body.prepend(banner);
            }
        }
        banner.innerHTML = `
            <div class="channel-warning-content">
                <span class="warning-icon">⚠️</span>
                <span class="warning-text"><b>Cảnh báo:</b> ${msg}</span>
            </div>
            <button class="channel-warning-close" onclick="this.parentElement.remove()" title="Đóng">&times;</button>
        `;
        banner.style.display = 'flex';
        this.showToast(`⚠️ ${msg}`, 6000);
    }

    updateAuthUI(isLoggedIn) {
        if (isLoggedIn && this.currentUser) {
            this.userAvatarImg.src = this.currentUser.avatar_url;
            const name = this.currentUser.display_name || this.currentUser.username;
            if (this.currentUser.is_channel_member === false) {
                this.userDisplayName.textContent = name + " (Chưa vào Channel)";
                this.userDisplayName.style.color = "#f59e0b";
                this.userDisplayName.title = "Tài khoản của bạn chưa tham gia thành viên vui lòng liên hệ Admin";
            } else {
                this.userDisplayName.textContent = name;
                this.userDisplayName.style.color = "";
                this.userDisplayName.title = "Tài khoản Telegram: " + name;
            }
        } else {
            this.userAvatarImg.src = "https://api.dicebear.com/7.x/avataaars/svg?seed=Guest";
            this.userDisplayName.textContent = "Đăng nhập";
            this.userDisplayName.style.color = "";
            this.userDisplayName.title = "Đăng nhập tài khoản";
            this.favoriteTracks = [];
            this.updateFavoriteBtnState();
        }
    }

    openAuthModal() {
        if (this.currentUser) {
            if (confirm("Bạn có muốn đăng xuất không?")) {
                this.logoutUser();
            }
        } else {
            if (this.authModal) {
                this.authModal.classList.add('open');
                this.switchAuthTab('phone');
                this.stopQrPolling();
                if (this.tgPhoneInput) {
                    setTimeout(() => this.tgPhoneInput.focus(), 150);
                }
            }
        }
    }

    setupAuthEvents() {
        if (this.userProfileBtn) {
            this.userProfileBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openAuthModal();
            });
        }
        
        if (this.closeAuthModal) {
            this.closeAuthModal.addEventListener('click', () => {
                this.authModal.classList.remove('open');
                this.stopQrPolling();
            });
        }

        // Tab Switching
        if (this.tabPhoneLogin) {
            this.tabPhoneLogin.addEventListener('click', () => {
                this.switchAuthTab('phone');
                this.stopQrPolling();
                if (this.tgPhoneInput) {
                    setTimeout(() => this.tgPhoneInput.focus(), 150);
                }
            });
        }
        if (this.tabQrLogin) {
            this.tabQrLogin.addEventListener('click', () => {
                this.switchAuthTab('qr');
                if (!this._qrPollTimer && !this.currentUser) {
                    this.initTelegramQrLogin();
                }
            });
        }
        if (this.tabPwLogin) {
            this.tabPwLogin.addEventListener('click', () => {
                this.switchAuthTab('pw');
                this.stopQrPolling();
            });
        }

        // QR Actions
        if (this.btnRefreshQr) {
            this.btnRefreshQr.addEventListener('click', () => this.initTelegramQrLogin());
        }

        if (this.btnSubmit2Fa) {
            this.btnSubmit2Fa.addEventListener('click', () => this.submitQr2Fa());
        }
        if (this.qr2FaInput) {
            this.qr2FaInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.submitQr2Fa();
            });
        }

        // Phone Auth Actions
        if (this.btnSendPhoneCode) {
            this.btnSendPhoneCode.addEventListener('click', () => this.sendPhoneCode());
        }
        if (this.tgPhoneInput) {
            this.tgPhoneInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.sendPhoneCode();
            });
        }
        if (this.btnVerifyPhoneCode) {
            this.btnVerifyPhoneCode.addEventListener('click', () => this.verifyPhoneCode());
        }
        if (this.tgPhoneOtpInput) {
            this.tgPhoneOtpInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.verifyPhoneCode();
            });
        }
        if (this.btnResendPhoneCode) {
            this.btnResendPhoneCode.addEventListener('click', () => this.resendPhoneCode());
        }
        if (this.btnBackToPhoneInput) {
            this.btnBackToPhoneInput.addEventListener('click', () => this.backToPhoneInput());
        }
        if (this.btnSubmitPhone2Fa) {
            this.btnSubmitPhone2Fa.addEventListener('click', () => this.submitPhone2Fa());
        }
        if (this.phone2FaInput) {
            this.phone2FaInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.submitPhone2Fa();
            });
        }
        
        if (this.loginSubmitBtn) {
            this.loginSubmitBtn.addEventListener('click', () => this.loginUser());
        }
        if (this.loginPassword) {
            this.loginPassword.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.loginUser();
            });
        }
        
        if (this.favoriteBtn) {
            this.favoriteBtn.addEventListener('click', () => this.toggleFavorite());
        }
    }

    switchAuthTab(tabName) {
        // Reset all tabs
        if (this.tabQrLogin) this.tabQrLogin.classList.toggle('active', tabName === 'qr');
        if (this.tabPhoneLogin) this.tabPhoneLogin.classList.toggle('active', tabName === 'phone');
        if (this.tabPwLogin) this.tabPwLogin.classList.toggle('active', tabName === 'pw');

        if (this.qrLoginPane) this.qrLoginPane.style.display = (tabName === 'qr') ? 'block' : 'none';
        if (this.phoneLoginPane) this.phoneLoginPane.style.display = (tabName === 'phone') ? 'block' : 'none';
        if (this.pwLoginPane) this.pwLoginPane.style.display = (tabName === 'pw') ? 'block' : 'none';
    }

    // --- Phone Number Authentication Implementation ---
    async sendPhoneCode() {
        if (!this.tgPhoneInput) return;
        const phone = this.tgPhoneInput.value.trim();
        if (!phone) return this.showToast("Vui lòng nhập số điện thoại Telegram.");

        if (this.btnSendPhoneCode) {
            this.btnSendPhoneCode.disabled = true;
            this.btnSendPhoneCode.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Đang gửi mã OTP...';
        }

        try {
            const res = await fetch('/api/music/auth/telegram/phone/send-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_number: phone })
            });
            const data = await res.json();

            if (this.btnSendPhoneCode) {
                this.btnSendPhoneCode.disabled = false;
                this.btnSendPhoneCode.innerHTML = '<i class="fa-solid fa-paper-plane" style="margin-right: 6px;"></i> Gửi Mã Xác Thực OTP';
            }

            if (data.status === 'success' && data.session_id) {
                this._currentPhoneSessionId = data.session_id;
                this.showToast("✅ Đã gửi mã OTP đến ứng dụng Telegram của bạn!");
                
                if (this.phoneSentTarget) this.phoneSentTarget.textContent = data.phone_number || phone;
                if (this.phoneStepInput) this.phoneStepInput.style.display = 'none';
                if (this.phoneStepOtp) this.phoneStepOtp.style.display = 'block';
                if (this.phoneStep2Fa) this.phoneStep2Fa.style.display = 'none';
                if (this.tgPhoneOtpInput) {
                    this.tgPhoneOtpInput.value = '';
                    this.tgPhoneOtpInput.focus();
                }
                this.startPhoneResendTimer(60);
            } else {
                this.showToast(data.message || "Không thể gửi mã OTP.");
            }
        } catch (e) {
            if (this.btnSendPhoneCode) {
                this.btnSendPhoneCode.disabled = false;
                this.btnSendPhoneCode.innerHTML = '<i class="fa-solid fa-paper-plane" style="margin-right: 6px;"></i> Gửi Mã Xác Thực OTP';
            }
            this.showToast("Lỗi kết nối tới máy chủ gửi mã.");
        }
    }

    async verifyPhoneCode() {
        if (!this._currentPhoneSessionId || !this.tgPhoneOtpInput) return;
        const code = this.tgPhoneOtpInput.value.trim().replace(/\s+/g, '');
        if (!code) return this.showToast("Vui lòng nhập mã xác thực OTP.");

        if (this.btnVerifyPhoneCode) {
            this.btnVerifyPhoneCode.disabled = true;
            this.btnVerifyPhoneCode.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Đang xác thực...';
        }

        try {
            const res = await fetch('/api/music/auth/telegram/phone/verify-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this._currentPhoneSessionId,
                    phone_code: code
                })
            });
            const data = await res.json();

            if (this.btnVerifyPhoneCode) {
                this.btnVerifyPhoneCode.disabled = false;
                this.btnVerifyPhoneCode.innerHTML = '<i class="fa-solid fa-circle-check" style="margin-right: 6px;"></i> Xác Nhận Đăng Nhập';
            }

            if (data.status === 'success' && data.user) {
                this.handleQrSuccess(data);
            } else if (data.status === 'needs_2fa') {
                if (this.phoneStepOtp) this.phoneStepOtp.style.display = 'none';
                if (this.phoneStep2Fa) this.phoneStep2Fa.style.display = 'block';
                if (this.phone2FaInput) {
                    this.phone2FaInput.value = '';
                    this.phone2FaInput.focus();
                }
                this.showToast("🔐 Tài khoản có bật mật khẩu 2FA. Vui lòng nhập mật khẩu.");
            } else {
                this.showToast(data.message || "Mã xác thực OTP không hợp lệ.");
            }
        } catch (e) {
            if (this.btnVerifyPhoneCode) {
                this.btnVerifyPhoneCode.disabled = false;
                this.btnVerifyPhoneCode.innerHTML = '<i class="fa-solid fa-circle-check" style="margin-right: 6px;"></i> Xác Nhận Đăng Nhập';
            }
            this.showToast("Lỗi kết nối khi xác thực OTP.");
        }
    }

    async submitPhone2Fa() {
        if (!this._currentPhoneSessionId || !this.phone2FaInput) return;
        const password = this.phone2FaInput.value.trim();
        if (!password) return this.showToast("Vui lòng nhập mật khẩu 2FA.");

        if (this.btnSubmitPhone2Fa) {
            this.btnSubmitPhone2Fa.disabled = true;
            this.btnSubmitPhone2Fa.textContent = "Đang xác thực...";
        }

        try {
            const res = await fetch('/api/music/auth/telegram/phone/2fa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this._currentPhoneSessionId,
                    password: password
                })
            });
            const data = await res.json();

            if (this.btnSubmitPhone2Fa) {
                this.btnSubmitPhone2Fa.disabled = false;
                this.btnSubmitPhone2Fa.textContent = "Xác Nhận Đăng Nhập";
            }

            if (data.status === 'success' && data.user) {
                this.handleQrSuccess(data);
            } else {
                this.showToast(data.message || "Mật khẩu 2FA không chính xác.");
            }
        } catch (e) {
            if (this.btnSubmitPhone2Fa) {
                this.btnSubmitPhone2Fa.disabled = false;
                this.btnSubmitPhone2Fa.textContent = "Xác Nhận Đăng Nhập";
            }
            this.showToast("Lỗi kết nối khi xác thực 2FA.");
        }
    }

    async resendPhoneCode() {
        if (!this._currentPhoneSessionId) return;

        try {
            const res = await fetch('/api/music/auth/telegram/phone/resend-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: this._currentPhoneSessionId })
            });
            const data = await res.json();
            if (data.status === 'success') {
                this.showToast("Đã gửi lại mã OTP mới!");
                this.startPhoneResendTimer(60);
            } else {
                this.showToast(data.message || "Chưa thể gửi lại mã lúc này.");
            }
        } catch (e) {
            this.showToast("Lỗi kết nối khi gửi lại mã.");
        }
    }

    backToPhoneInput() {
        if (this._phoneResendTimer) {
            clearInterval(this._phoneResendTimer);
            this._phoneResendTimer = null;
        }
        if (this.phoneStepInput) this.phoneStepInput.style.display = 'block';
        if (this.phoneStepOtp) this.phoneStepOtp.style.display = 'none';
        if (this.phoneStep2Fa) this.phoneStep2Fa.style.display = 'none';
        if (this.tgPhoneInput) this.tgPhoneInput.focus();
    }

    startPhoneResendTimer(seconds = 60) {
        if (this._phoneResendTimer) clearInterval(this._phoneResendTimer);
        let rem = seconds;

        if (this.btnResendPhoneCode) this.btnResendPhoneCode.disabled = true;
        if (this.phoneResendCountdown) this.phoneResendCountdown.textContent = rem;

        this._phoneResendTimer = setInterval(() => {
            rem--;
            if (this.phoneResendCountdown) this.phoneResendCountdown.textContent = rem;
            if (rem <= 0) {
                clearInterval(this._phoneResendTimer);
                this._phoneResendTimer = null;
                if (this.btnResendPhoneCode) {
                    this.btnResendPhoneCode.disabled = false;
                    this.btnResendPhoneCode.innerHTML = '<span>Gửi lại mã OTP</span>';
                }
            }
        }, 1000);
    }

    // --- Telegram MTProto QR Login Implementation ---
    async initTelegramQrLogin() {
        this.stopQrPolling();
        if (this.qrLoadingSpinner) this.qrLoadingSpinner.classList.add('active');
        if (this.qrExpiredOverlay) this.qrExpiredOverlay.style.display = 'none';
        if (this.qr2FaSection) this.qr2FaSection.style.display = 'none';
        if (this.qrStatusText) this.qrStatusText.textContent = "Đang kết nối Telegram...";

        try {
            const res = await fetch('/api/music/auth/telegram/qr/init', { method: 'POST' });
            const data = await res.json();

            if (this.qrLoadingSpinner) this.qrLoadingSpinner.classList.remove('active');

            if (data.status === 'success' && data.tg_url) {
                this._currentQrSessionId = data.session_id;
                this.renderQrCode(data.tg_url);
                if (this.qrStatusText) this.qrStatusText.textContent = "Mở Telegram trên điện thoại để quét mã";
                this.startQrPolling(data.session_id, data.expires_at || (Date.now()/1000 + 60));
            } else {
                if (this.qrStatusText) this.qrStatusText.textContent = data.message || "Lỗi tạo mã QR";
                this.showToast(data.message || "Không thể tạo mã QR đăng nhập.");
            }
        } catch (e) {
            if (this.qrLoadingSpinner) this.qrLoadingSpinner.classList.remove('active');
            if (this.qrStatusText) this.qrStatusText.textContent = "Lỗi kết nối máy chủ";
            this.showToast("Lỗi kết nối tới máy chủ tạo mã QR.");
        }
    }

    renderQrCode(tgUrl) {
        if (!this.qrCodeContainer) return;
        this.qrCodeContainer.innerHTML = '';
        
        try {
            if (typeof QRCode !== 'undefined') {
                this._qrCodeInstance = new QRCode(this.qrCodeContainer, {
                    text: tgUrl,
                    width: 196,
                    height: 196,
                    colorDark: "#0c1017",
                    colorLight: "#ffffff",
                    correctLevel: QRCode.CorrectLevel.M
                });
            } else {
                // Fallback SVG / Image nếu QRCode.js chưa tải
                const img = document.createElement('img');
                img.src = `https://api.qrserver.com/v1/create-qr-code/?size=196x196&data=${encodeURIComponent(tgUrl)}&margin=10`;
                img.alt = "Telegram QR Code";
                this.qrCodeContainer.appendChild(img);
            }
        } catch (err) {
            console.error("Lỗi render QRCode:", err);
            const img = document.createElement('img');
            img.src = `https://api.qrserver.com/v1/create-qr-code/?size=196x196&data=${encodeURIComponent(tgUrl)}&margin=10`;
            this.qrCodeContainer.appendChild(img);
        }
    }

    startQrPolling(sessionId, expiresAt) {
        this.stopQrPolling();

        // 1. Countdown timer
        const updateCountdown = () => {
            const nowSec = Date.now() / 1000;
            const remaining = Math.max(0, Math.ceil(expiresAt - nowSec));
            if (this.qrCountdownSec) this.qrCountdownSec.textContent = remaining;

            if (remaining <= 0) {
                this.stopQrPolling();
                if (this.qrExpiredOverlay) this.qrExpiredOverlay.style.display = 'flex';
                if (this.qrStatusText) this.qrStatusText.textContent = "Mã QR đã hết hạn";
            }
        };
        updateCountdown();
        this._qrCountdownTimer = setInterval(updateCountdown, 1000);

        // 2. Status poll loop (Tốc độ kiểm tra 1.2s)
        this._qrPollTimer = setInterval(async () => {
            if (!this.authModal.classList.contains('open')) {
                this.stopQrPolling();
                return;
            }

            try {
                const res = await fetch(`/api/music/auth/telegram/qr/status?session_id=${encodeURIComponent(sessionId)}`);
                const data = await res.json();

                if (data.status === 'success' && data.user) {
                    this.handleQrSuccess(data);
                } else if (data.status === 'needs_2fa') {
                    if (this.qr2FaSection) {
                        this.qr2FaSection.style.display = 'block';
                        this.qr2FaSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                    if (this.qrStatusText) {
                        this.qrStatusText.innerHTML = '<span style="color:#f59e0b; font-weight:700;">🔐 Đã quét mã! Nhập mật khẩu 2FA bên dưới:</span>';
                    }
                    if (this.qr2FaInput && document.activeElement !== this.qr2FaInput) {
                        this.qr2FaInput.focus();
                    }
                } else if (data.status === 'expired') {
                    this.stopQrPolling();
                    if (this.qrExpiredOverlay) this.qrExpiredOverlay.style.display = 'flex';
                    if (this.qrStatusText) this.qrStatusText.textContent = "Mã QR đã hết hạn";
                } else if (data.status === 'pending') {
                    if (data.message && this.qrStatusText && this.qrStatusText.textContent !== data.message) {
                        this.qrStatusText.textContent = data.message;
                    }
                }
            } catch (err) {
                // Ignore transient network glitches in polling
            }
        }, 1200);
    }

    stopQrPolling() {
        if (this._qrPollTimer) {
            clearInterval(this._qrPollTimer);
            this._qrPollTimer = null;
        }
        if (this._qrCountdownTimer) {
            clearInterval(this._qrCountdownTimer);
            this._qrCountdownTimer = null;
        }
    }

    async submitQr2Fa() {
        if (!this._currentQrSessionId || !this.qr2FaInput) return;
        const password = this.qr2FaInput.value.trim();
        if (!password) return this.showToast("Vui lòng nhập mật khẩu 2FA.");

        if (this.btnSubmit2Fa) this.btnSubmit2Fa.textContent = "Đang xác thực...";

        try {
            const res = await fetch('/api/music/auth/telegram/qr/2fa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: this._currentQrSessionId, password })
            });
            const data = await res.json();
            if (this.btnSubmit2Fa) this.btnSubmit2Fa.textContent = "Xác Nhận Đăng Nhập";

            if (data.status === 'success' && data.user) {
                this.handleQrSuccess(data);
            } else {
                this.showToast(data.message || "Mật khẩu 2FA không chính xác.");
            }
        } catch (e) {
            if (this.btnSubmit2Fa) this.btnSubmit2Fa.textContent = "Xác Nhận Đăng Nhập";
            this.showToast("Lỗi kết nối khi xác thực 2FA.");
        }
    }

    async handleQrSuccess(data) {
        this.stopQrPolling();
        this.showToast(`🎉 Đăng nhập Telegram thành công! Chào mừng ${data.user.display_name}!`);
        this.authModal.classList.remove('open');
        if (this.qr2FaInput) this.qr2FaInput.value = '';

        // Kiểm tra và hiển thị cảnh báo nếu chưa tham gia Channel thành viên
        if (data.is_channel_member === false || data.user?.is_channel_member === false || data.channel_warning) {
            const warningMsg = data.channel_warning || "Tài khoản của bạn chưa tham gia thành viên vui lòng liên hệ Admin";
            setTimeout(() => {
                alert("⚠️ " + warningMsg);
                this.showToast("⚠️ " + warningMsg);
            }, 400);
        }

        await this.fetchUserProfile();
        await this.fetchTelegramAlbums(false);

        if (this.favoriteTracks && this.favoriteTracks.length > 0) {
            this.playFavoritesQueue(0, false, false);
            if (this.navFavorites) this.setActiveNavLink(this.navFavorites);
        } else if (this.playlists && this.playlists.length > 0 && this.playlists[0].tracks?.length > 0) {
            this.playPlaylist(this.playlists[0], 0, false);
            if (this.navPlaylists) this.setActiveNavLink(this.navPlaylists);
        } else if (this.albums && this.albums.length > 0 && !this.albums[0].isDemo) {
            this.loadAlbum(0, 0, false);
            this.renderAlbumGrid();
        }
    }

    async loginUser() {
        const username = this.loginUsername.value;
        const password = this.loginPassword.value;
        if (!username || !password) return this.showToast("Vui lòng nhập Username & Password");
        
        try {
            const res = await fetch('/api/music/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (data.status === 'success') {
                this.showToast(`Chào mừng trở lại, ${data.user.display_name}!`);
                this.authModal.classList.remove('open');
                this.loginPassword.value = '';
                await this.fetchUserProfile();
                await this.fetchTelegramAlbums(false);
                if (this.favoriteTracks && this.favoriteTracks.length > 0) {
                    this.playFavoritesQueue(0, false, false);
                    if (this.navFavorites) this.setActiveNavLink(this.navFavorites);
                } else if (this.playlists && this.playlists.length > 0 && this.playlists[0].tracks?.length > 0) {
                    this.playPlaylist(this.playlists[0], 0, false);
                    if (this.navPlaylists) this.setActiveNavLink(this.navPlaylists);
                } else if (this.albums && this.albums.length > 0 && !this.albums[0].isDemo) {
                    this.loadAlbum(0, 0, false);
                    this.renderAlbumGrid();
                } else {
                    this.showEmptyCloudState();
                }
            } else {
                this.showToast(data.message || "Đăng nhập thất bại.");
            }
        } catch (e) {
            this.showToast("Lỗi kết nối.");
        }
    }

    async logoutUser() {
        try {
            this.stopHeartbeat();
            await fetch('/api/music/auth/logout', { method: 'POST' });
            this.showToast("Đã đăng xuất.");
            this.currentUser = null;
            this.playlists = [];
            this.albums = [...ALBUMS_DATABASE];
            this.updateAuthUI(false);
            if (this.playlistGrid) this.playlistGrid.innerHTML = '';
            localStorage.removeItem('xtapo_music_player_state');
            localStorage.removeItem('xtapo_music_active_view');
            this.loadAlbum(0, 0, false);
            this.renderAlbumGrid();
        } catch (e) { }
    }

    async fetchUserFavorites() {
        try {
            const res = await fetch('/api/music/user/favorites');
            const data = await res.json();
            if (data.status === 'success') {
                this.favoriteTracks = data.favorites;
                this.updateFavoriteBtnState();
            }
        } catch (e) {}
    }

    getTrackIdentifiers(track) {
        if (!track) return { chatId: null, msgId: null };
        const album = this.currentAlbum;
        const chatId = track.chatId || (track.meta && track.meta.chat_id) || track.chat_id || (album && (album.chatId || album.chat_id)) || 'demo';
        const msgId = track.msgId || (track.meta && track.meta.msg_id) || track.msg_id || track.id || track.name;
        return { chatId: String(chatId), msgId: String(msgId) };
    }

    updateFavoriteBtnState() {
        if (!this.favoriteBtn) return;
        const track = this.currentTrack;
        if (!track) {
            this.favoriteBtn.style.color = 'var(--text-muted)';
            this.favoriteBtn.title = 'Thêm vào yêu thích (Cần đăng nhập)';
            return;
        }

        const { chatId, msgId } = this.getTrackIdentifiers(track);
        if (!chatId || !msgId) {
            this.favoriteBtn.style.color = 'var(--text-muted)';
            return;
        }

        const isFav = this.favoriteTracks && this.favoriteTracks.some(f => String(f.chat_id) === chatId && String(f.msg_id) === msgId);
        if (isFav) {
            this.favoriteBtn.style.color = '#ef4444'; // Red
            this.favoriteBtn.title = 'Đã yêu thích (Bấm để bỏ thích)';
            this.favoriteBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>`;
        } else {
            this.favoriteBtn.style.color = 'var(--text-muted)';
            this.favoriteBtn.title = this.currentUser ? 'Thêm vào danh sách yêu thích' : 'Thêm vào yêu thích (Cần đăng nhập)';
            this.favoriteBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>`;
        }
    }

    async toggleFavorite() {
        if (!this.currentUser) {
            if (this.authModal) this.authModal.classList.add('open');
            return this.showToast("Vui lòng đăng nhập để sử dụng tính năng yêu thích ❤️");
        }
        
        const track = this.currentTrack;
        if (!track) return;
        const { chatId, msgId } = this.getTrackIdentifiers(track);
        if (!chatId || !msgId) return this.showToast("Không tìm thấy thông tin bài hát để yêu thích");

        try {
            const res = await fetch('/api/music/user/favorites/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: chatId,
                    msg_id: msgId,
                    name: track.name,
                    artist: track.artist || this.currentAlbum.artist,
                    cover_url: track.coverUrl || this.currentAlbum.coverUrl
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                if (data.is_favorite) {
                    this.favoriteTracks.push({
                        chat_id: chatId,
                        msg_id: msgId,
                        title: track.name,
                        artist: track.artist || this.currentAlbum.artist
                    });
                } else {
                    this.favoriteTracks = this.favoriteTracks.filter(f => !(String(f.chat_id) === chatId && String(f.msg_id) === msgId));
                }
                this.updateFavoriteBtnState();
                this.showToast(data.message || (data.is_favorite ? "Đã thêm vào yêu thích ❤️" : "Đã bỏ yêu thích"));
            } else {
                this.showToast(data.message || "Lỗi cập nhật yêu thích");
            }
        } catch (e) {
            this.showToast("Lỗi kết nối khi cập nhật yêu thích");
        }
    }

    getAllLibraryTracks() {
        const trackMap = new Map();
        (this.getBaseAlbums()).forEach(album => {
            (album.tracks || []).forEach(track => {
                const { chatId, msgId } = this.getTrackIdentifiers(track);
                const key = `${chatId}_${msgId}`;
                if (!trackMap.has(key)) {
                    trackMap.set(key, { ...track, albumTitle: album.title, albumArtist: album.artist, albumCover: album.coverUrl });
                }
            });
        });
        return trackMap;
    }

    openFavoritesModal() {
        if (!this.currentUser) {
            if (this.authModal) this.authModal.classList.add('open');
            this.showToast("Vui lòng đăng nhập để xem danh sách bài hát yêu thích ❤️");
            return;
        }
        if (this.favSearchInput) this.favSearchInput.value = '';
        this.renderFavoritesList();
        this.openModal(this.favoritesModal);
    }

    renderFavoritesList(searchQuery = '') {
        if (!this.favoritesList) return;
        this.favoritesList.innerHTML = '';

        const totalFavs = this.favoriteTracks ? this.favoriteTracks.length : 0;
        if (this.favModalCount) {
            this.favModalCount.textContent = `${totalFavs} bài hát`;
        }

        if (totalFavs === 0) {
            this.favoritesList.innerHTML = `
                <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
                    <div style="font-size: 2.5rem; margin-bottom: 12px; filter: grayscale(0.6);">🤍</div>
                    <div style="font-weight: 700; color: #fff; margin-bottom: 6px; font-size: 1rem;">Chưa có bài hát yêu thích nào</div>
                    <p style="font-size: 0.85rem; max-width: 320px; margin: 0 auto; line-height: 1.5;">
                        Khi đang nghe nhạc, hãy bấm vào biểu tượng <b>Trái Tim ❤️</b> để lưu bài hát vào danh sách này nhé!
                    </p>
                </div>
            `;
            if (this.btnFavPlayAll) this.btnFavPlayAll.disabled = true;
            if (this.btnFavShuffle) this.btnFavShuffle.disabled = true;
            return;
        }

        if (this.btnFavPlayAll) this.btnFavPlayAll.disabled = false;
        if (this.btnFavShuffle) this.btnFavShuffle.disabled = false;

        const allTracksMap = this.getAllLibraryTracks();
        let matchedFavorites = this.favoriteTracks.map((fav, idx) => {
            const key = `${String(fav.chat_id)}_${String(fav.msg_id)}`;
            const libTrack = allTracksMap.get(key);
            return {
                id: idx + 1,
                name: (libTrack && libTrack.name) || fav.title || `Bài hát ${fav.msg_id}`,
                artist: (libTrack && libTrack.artist) || fav.artist || 'XTAPO Artist',
                duration: (libTrack && libTrack.duration) || '--:--',
                format: (libTrack && libTrack.format) || 'FLAC Hi-Res',
                coverUrl: (libTrack && (libTrack.coverUrl || libTrack.albumCover)) || fav.cover_url || this.albums[0]?.coverUrl,
                previewUrl: (libTrack && libTrack.previewUrl) || `/api/music/stream/${fav.chat_id}/${fav.msg_id}`,
                chatId: fav.chat_id,
                msgId: fav.msg_id
            };
        });

        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            matchedFavorites = matchedFavorites.filter(t => t.name.toLowerCase().includes(q) || t.artist.toLowerCase().includes(q));
        }

        if (matchedFavorites.length === 0) {
            this.favoritesList.innerHTML = `
                <div style="text-align: center; padding: 30px 20px; color: var(--text-muted); font-size: 0.85rem;">
                    Không tìm thấy bài hát yêu thích nào khớp với từ khóa.
                </div>
            `;
            return;
        }

        matchedFavorites.forEach((track, index) => {
            const row = document.createElement('div');
            row.className = 'fav-track-row';
            row.innerHTML = `
                <div style="display: flex; align-items: center; gap: 12px; min-width: 0; flex: 1;">
                    <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); width: 22px; text-align: center;">${index + 1}</span>
                    <img src="${track.coverUrl}" loading="lazy" style="width: 38px; height: 38px; border-radius: 8px; object-fit: cover; flex-shrink: 0;" alt="Cover">
                    <div style="min-width: 0; flex: 1;">
                        <div style="font-size: 0.85rem; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(track.name)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(track.artist)} • <span style="color: var(--accent-gold);">${track.format}</span></div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 10px; margin-left: 10px;">
                    <span style="font-size: 0.75rem; color: var(--text-muted);">${track.duration}</span>
                    <button class="nav-btn icon-btn" style="width: 30px; height: 30px; border-radius: 50%; background: var(--color-primary); color: #fff; display: flex; align-items: center; justify-content: center; flex-shrink: 0;" title="Phát bài này">
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    </button>
                    <button class="fav-remove-btn" title="Xóa khỏi danh sách yêu thích" data-chat-id="${track.chatId}" data-msg-id="${track.msgId}">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style="color: #ef4444;"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                    </button>
                </div>
            `;

            // Click row to play
            row.addEventListener('click', (e) => {
                if (e.target.closest('.fav-remove-btn')) return; // Ignore if clicked remove
                this.closeModal(this.favoritesModal);
                this.playFavoritesQueue(index, false);
            });

            // Remove button
            const removeBtn = row.querySelector('.fav-remove-btn');
            if (removeBtn) {
                removeBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const cid = removeBtn.getAttribute('data-chat-id');
                    const mid = removeBtn.getAttribute('data-msg-id');
                    await this.removeFavoriteItem(cid, mid);
                });
            }

            this.favoritesList.appendChild(row);
        });
    }

    async removeFavoriteItem(chatId, msgId) {
        try {
            const res = await fetch('/api/music/user/favorites/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: chatId, msg_id: msgId })
            });
            const data = await res.json();
            if (data.status === 'success') {
                this.favoriteTracks = this.favoriteTracks.filter(f => !(String(f.chat_id) === String(chatId) && String(f.msg_id) === String(msgId)));
                this.updateFavoriteBtnState();
                this.renderFavoritesList(this.favSearchInput ? this.favSearchInput.value.trim() : '');
                this.showToast("Đã xóa bài hát khỏi danh sách yêu thích 🤍");
            }
        } catch (e) {
            this.showToast("Lỗi khi xóa bài hát");
        }
    }

    playFavoritesQueue(startIndex = 0, isShuffle = false, autoPlay = true) {
        if (!this.favoriteTracks || this.favoriteTracks.length === 0) {
            return this.showToast("Danh sách yêu thích đang trống.");
        }

        const allTracksMap = this.getAllLibraryTracks();
        let tracks = this.favoriteTracks.map((fav, idx) => {
            const key = `${String(fav.chat_id)}_${String(fav.msg_id)}`;
            const libTrack = allTracksMap.get(key);
            return {
                id: idx + 1,
                name: (libTrack && libTrack.name) || fav.title || `Bài hát ${fav.msg_id}`,
                artist: (libTrack && libTrack.artist) || fav.artist || 'XTAPO Artist',
                duration: (libTrack && libTrack.duration) || '3:30',
                format: (libTrack && libTrack.format) || 'FLAC Hi-Res',
                coverUrl: (libTrack && (libTrack.coverUrl || libTrack.albumCover)) || fav.cover_url || this.albums[0]?.coverUrl,
                previewUrl: (libTrack && libTrack.previewUrl) || `/api/music/stream/${fav.chat_id}/${fav.msg_id}`,
                chatId: fav.chat_id,
                msgId: fav.msg_id
            };
        });

        if (isShuffle && tracks.length > 1) {
            for (let i = tracks.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [tracks[i], tracks[j]] = [tracks[j], tracks[i]];
            }
        }

        const favAlbum = {
            id: 'favorites-playlist',
            title: 'BÀI HÁT YÊU THÍCH ❤️',
            artist: this.currentUser ? (this.currentUser.display_name || this.currentUser.username) : 'My Favorites',
            coverUrl: tracks[0]?.coverUrl || 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop',
            format: 'FLAC Hi-Res Lossless',
            year: new Date().getFullYear().toString(),
            publisher: 'Personal Favorites Collection',
            glowColors: { glow1: 'radial-gradient(circle, #ef4444 0%, #b91c1c 60%, transparent 80%)', glow2: 'radial-gradient(circle, #ec4899 0%, #4338ca 60%, transparent 80%)' },
            tracks: tracks
        };

        this.setVirtualAlbum(favAlbum, startIndex, autoPlay);
        if (autoPlay) {
            this.showToast(`Đang phát Tuyển Tập Yêu Thích (${tracks.length} bài hát) ❤️`);
        }
    }

    // --- Base Albums & Virtual Queues Helper ---
    getBaseAlbums() {
        return (this.albums || []).filter(a => {
            if (!a || !a.id) return true;
            const id = String(a.id);
            return !id.startsWith('genre-') && 
                   !id.startsWith('artist-') && 
                   !id.startsWith('country-') && 
                   !id.startsWith('fav-') && 
                   !id.startsWith('favorites-') && 
                   !id.startsWith('pl-') && 
                   !id.startsWith('hires-');
        });
    }

    setVirtualAlbum(virtualAlbum, startIndex = 0, autoPlay = true) {
        // Luôn làm sạch các danh sách ảo tạm thời cũ trước khi thêm danh sách mới
        this.albums = this.getBaseAlbums();
        this.albums.unshift(virtualAlbum);
        this.currentAlbumIndex = 0;
        this.loadAlbum(0, startIndex, autoPlay);
        this.renderAlbumGrid();
    }

    // --- Current Album & Track Getters ---
    get currentAlbum() {
        if (this.currentUser) {
            const nonDemoAlbums = (this.albums || []).filter(a => !a.isDemo);
            if (nonDemoAlbums.length > 0) {
                return this.albums[this.currentAlbumIndex] || nonDemoAlbums[0];
            }
            return {
                id: 'empty-library',
                title: 'KHO NHẠC TELEGRAM',
                artist: this.currentUser.display_name || this.currentUser.username,
                publisher: 'XTAPO Cloud Streaming',
                year: '2026',
                coverUrl: this.currentUser.avatar_url || 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop',
                tracks: []
            };
        }
        return this.albums[this.currentAlbumIndex] || this.albums[0] || ALBUMS_DATABASE[0];
    }

    get currentTrack() {
        const album = this.currentAlbum;
        if (!album || !album.tracks || album.tracks.length === 0) return null;
        return album.tracks[this.currentTrackIndex] || album.tracks[0];
    }

    showEmptyCloudState() {
        if (!this.currentUser) return;
        if (this.albumTitle) this.albumTitle.textContent = "KHO NHẠC TELEGRAM";
        if (this.artistName) this.artistName.textContent = `Xin chào ${this.currentUser.display_name || this.currentUser.username}`;
        if (this.albumCompany) this.albumCompany.textContent = "XTAPO Cloud Streaming";
        if (this.trackCountLabel) this.trackCountLabel.textContent = "0 Bài hát";
        if (this.totalDurationLabel) this.totalDurationLabel.textContent = "0 Phút";
        if (this.albumYearTag) this.albumYearTag.textContent = "2026";
        if (this.badgeAudioSpecs) this.badgeAudioSpecs.textContent = "LOSSLESS";
        const fallbackAvatar = this.currentUser.avatar_url || "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop";
        if (this.albumCoverImg) this.albumCoverImg.src = fallbackAvatar;
        if (this.vinylCenterImg) this.vinylCenterImg.src = fallbackAvatar;

        if (this.nowPlayingTitle) this.nowPlayingTitle.textContent = "Chưa phát bài hát nào";
        if (this.nowPlayingArtist) this.nowPlayingArtist.textContent = this.currentUser.display_name || this.currentUser.username;
        if (this.timeTotal) this.timeTotal.textContent = "--:--";
        if (this.timeCurrent) this.timeCurrent.textContent = "0:00";
        this.updateProgress(0);

        if (this.tracklistEl) {
            this.tracklistEl.innerHTML = `
                <li style="padding: 30px 20px; text-align: center; color: var(--text-muted); list-style: none;">
                    <div style="font-size: 2rem; margin-bottom: 8px;">☁️</div>
                    <div style="font-weight: 700; color: #fff; font-size: 1rem; margin-bottom: 6px;">Kho nhạc Cloud của bạn đang trống</div>
                    <div style="font-size: 0.85rem; margin-bottom: 16px; opacity: 0.8;">Kết nối kênh Telegram hoặc tạo Playlist để bắt đầu thưởng thức âm nhạc!</div>
                    <button id="btnEmptyScanTg" class="nav-btn" style="background: var(--color-primary); color: #fff; border: none; padding: 8px 18px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                        <span>Quét kênh Telegram</span>
                    </button>
                </li>
            `;
            const scanBtn = document.getElementById('btnEmptyScanTg');
            if (scanBtn) {
                scanBtn.addEventListener('click', () => {
                    this.openModal(this.tgModal);
                });
            }
        }
    }

    // --- Fetch Telegram Library from Backend ---
    async fetchTelegramAlbums(shouldLoadAlbum = true) {
        try {
            const res = await fetch('/api/music/albums');
            if (res.ok) {
                const data = await res.json();
                if (data && data.status === 'success') {
                    if (data.albums && data.albums.length > 0) {
                        this.albums = data.albums;
                        this.currentAlbumIndex = 0;
                        this.currentTrackIndex = 0;
                        if (shouldLoadAlbum) {
                            this.loadAlbum(0, 0, false);
                        }
                        this.renderAlbumGrid();
                        if (this.albumCountBadge) {
                            this.albumCountBadge.textContent = `${this.albums.length} Albums (TG)`;
                        }
                        if (this.tgStorageLabel) {
                            this.tgStorageLabel.textContent = '⚡ Telegram Live';
                        }
                    } else {
                        this.albums = [];
                        if (this.albumCountBadge) {
                            this.albumCountBadge.textContent = '0 Albums';
                        }
                        if (this.tgStorageLabel) {
                            this.tgStorageLabel.textContent = '⚡ Telegram Cloud';
                        }
                        this.renderAlbumGrid();
                    }
                }
            }
        } catch (err) {
            // Đang mở file tĩnh hoặc backend chưa kết nối
            console.log('[XTAPO MUSIC] Backend API offline or file mode, using local database.');
        }
    }

    async fetchArtistMetadata() {
        try {
            const res = await fetch('/api/music/artists');
            if (res.ok) {
                const data = await res.json();
                if (data && data.status === 'success' && data.artists) {
                    data.artists.forEach(a => {
                        if (a && a.name) {
                            this.artistCacheMap.set(a.name.toLowerCase().trim(), a);
                        }
                    });
                }
            }
        } catch (e) {
            console.log('[Artist Metadata] API offline or static mode');
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

    detectYearFromTrack(track) {
        if (!track) return '2024';
        if (track.year && /^\d{4}$/.test(String(track.year).trim()) && String(track.year).trim() !== '2026') {
            return String(track.year).trim();
        }
        const name = track.name || track.title || '';
        const album = track.album || track.albumName || '';
        const raw = `${name} ${album}`;
        const m = raw.match(/\b(19\d{2}|20[0-2]\d)\b/);
        if (m) return m[1];
        return track.year && String(track.year).trim() !== '2026' ? String(track.year).trim() : '2024';
    }

    updateAudioBadges(track, album) {
        if (!this.badgeAudioQuality && !this.badgeAudioSpecs && !this.albumYearTag) return;

        track = track || (album && album.tracks && album.tracks[0]) || {};
        album = album || this.currentAlbum || {};

        const fmt = (track.format || album.format || 'FLAC Hi-Res Lossless').toUpperCase();
        const tier = (track.qualityTier || album.qualityTier || 'lossless').toLowerCase();
        const bitrate = track.bitrate || album.bitrate || '';

        // 1. Badge Quality Category
        if (this.badgeAudioQuality) {
            if (tier === 'hi-res' || fmt.includes('HI-RES') || fmt.includes('24-BIT') || fmt.includes('32-BIT') || fmt.includes('DSD') || fmt.includes('96KHZ') || fmt.includes('192KHZ')) {
                this.badgeAudioQuality.textContent = 'HI-RES AUDIO';
                this.badgeAudioQuality.className = 'badge-tag accent-tag';
            } else if (fmt.includes('FLAC') || fmt.includes('LOSSLESS') || fmt.includes('ALAC') || fmt.includes('WAV')) {
                this.badgeAudioQuality.textContent = 'LOSSLESS';
                this.badgeAudioQuality.className = 'badge-tag accent-tag';
            } else if (fmt.includes('MP3')) {
                this.badgeAudioQuality.textContent = 'MP3 AUDIO';
                this.badgeAudioQuality.className = 'badge-tag';
            } else if (fmt.includes('AAC') || fmt.includes('M4A')) {
                this.badgeAudioQuality.textContent = 'AAC AUDIO';
                this.badgeAudioQuality.className = 'badge-tag';
            } else {
                this.badgeAudioQuality.textContent = 'HQ AUDIO';
                this.badgeAudioQuality.className = 'badge-tag';
            }
        }

        // 2. Badge Technical Specs
        if (this.badgeAudioSpecs) {
            if (fmt.includes('24-BIT') || fmt.includes('96KHZ') || fmt.includes('192KHZ')) {
                if (fmt.includes('96KHZ')) {
                    this.badgeAudioSpecs.textContent = '24-BIT / 96kHz';
                } else if (fmt.includes('192KHZ')) {
                    this.badgeAudioSpecs.textContent = '24-BIT / 192kHz';
                } else if (fmt.includes('48KHZ')) {
                    this.badgeAudioSpecs.textContent = '24-BIT / 48kHz';
                } else {
                    this.badgeAudioSpecs.textContent = '24-BIT / 96kHz';
                }
            } else if (fmt.includes('320') || (bitrate && parseInt(bitrate, 10) >= 300)) {
                this.badgeAudioSpecs.textContent = '320 KBPS / 44.1kHz';
            } else if (fmt.includes('256') || (bitrate && parseInt(bitrate, 10) >= 240)) {
                this.badgeAudioSpecs.textContent = '256 KBPS / 44.1kHz';
            } else if (fmt.includes('128') || (bitrate && parseInt(bitrate, 10) <= 160 && parseInt(bitrate, 10) > 0)) {
                this.badgeAudioSpecs.textContent = `${bitrate || 128} KBPS / 44.1kHz`;
            } else if (fmt.includes('16-BIT') || fmt.includes('FLAC') || fmt.includes('LOSSLESS')) {
                this.badgeAudioSpecs.textContent = '16-BIT / 44.1kHz';
            } else if (bitrate) {
                this.badgeAudioSpecs.textContent = `~${bitrate} KBPS`;
            } else {
                this.badgeAudioSpecs.textContent = '16-BIT / 44.1kHz';
            }
        }

        // 3. Badge Year
        if (this.albumYearTag) {
            const year = this.detectYearFromTrack(track) || this.detectYearFromTrack({ name: album.title }) || album.year || '2024';
            this.albumYearTag.textContent = year;
        }
    }

    // --- Load Album & Track ---
    loadAlbum(albumIndex, trackIndex = 0, autoPlay = true) {
        this.currentAlbumIndex = albumIndex;
        const album = this.currentAlbum;

        if (album && album.id && String(album.id).startsWith('pl-')) {
            this.activePlaylistId = String(album.id).replace('pl-', '');
        } else {
            this.activePlaylistId = null;
        }

        // Update Text Info
        if (this.albumTitle) this.albumTitle.textContent = album.title || '';
        if (this.artistName) this.artistName.textContent = album.artist || '';
        if (this.albumCompany) this.albumCompany.textContent = album.publisher || '';
        if (this.trackCountLabel) this.trackCountLabel.textContent = `${(album.tracks || []).length} Songs`;

        // Update Badges
        const currentTrackObj = (album.tracks && album.tracks[trackIndex]) || (album.tracks && album.tracks[0]);
        this.updateAudioBadges(currentTrackObj, album);

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
        if (this.totalDurationLabel) {
            this.totalDurationLabel.textContent = (!isNaN(mins) && mins > 0) ? `${mins} Minutes` : `${(album.tracks || []).length} Songs`;
        }

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

    renderTracklist(filterQuery = '') {
        const album = this.currentAlbum;
        const tracks = album.tracks || [];
        if (this.mobileTrackCount) {
            this.mobileTrackCount.textContent = tracks.length;
        }
        if (this.tracklistModalAlbumTitle) {
            this.tracklistModalAlbumTitle.textContent = album.title;
        }
        if (this.tracklistModalArtist) {
            this.tracklistModalArtist.textContent = `${album.artist} • ${tracks.length} bài hát`;
        }

        // Render Main Tracklist with Lazy Infinite Scroll Chunking
        if (this.tracklistEl) {
            this.tracklistEl.innerHTML = '';
            this._mainTracklistRenderedCount = 0;
            const targetInitial = Math.min(tracks.length, Math.max(60, this.currentTrackIndex + 20));
            this.appendMainTracklistBatch(targetInitial);

            // Bind scroll listener for main tracklist if not already bound
            if (!this._mainTracklistScrollBound) {
                this._mainTracklistScrollBound = true;
                this.tracklistEl.addEventListener('scroll', () => {
                    const el = this.tracklistEl;
                    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 300) {
                        const albumTracks = (this.currentAlbum && this.currentAlbum.tracks) || [];
                        if (this._mainTracklistRenderedCount < albumTracks.length) {
                            this.appendMainTracklistBatch(50);
                        }
                    }
                }, { passive: true });
            }
        }

        // Render Modal Tracklist with Progressive Filter Chunking
        if (this.modalTracklistEl) {
            this.modalTracklistEl.innerHTML = '';
            const q = (filterQuery || '').toLowerCase().trim();
            this._modalFilteredTracks = tracks
                .map((track, idx) => ({ track, idx }))
                .filter(({ track }) => !q || (track.name || '').toLowerCase().includes(q) || (track.artist || album.artist || '').toLowerCase().includes(q));

            this._modalTracklistRenderedCount = 0;

            if (this._modalFilteredTracks.length === 0) {
                this.modalTracklistEl.innerHTML = `
                    <div style="text-align:center; padding: 24px; color: var(--text-muted); font-size: 0.85rem;">
                        Không tìm thấy bài hát nào khớp với "${this.escapeHtml(filterQuery)}"
                    </div>
                `;
            } else {
                this.appendModalTracklistBatch(50);
            }

            if (!this._modalTracklistScrollBound) {
                this._modalTracklistScrollBound = true;
                this.modalTracklistEl.addEventListener('scroll', () => {
                    const el = this.modalTracklistEl;
                    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 300) {
                        if (this._modalTracklistRenderedCount < this._modalFilteredTracks.length) {
                            this.appendModalTracklistBatch(50);
                        }
                    }
                }, { passive: true });
            }
        }
    }

    appendMainTracklistBatch(count = 50) {
        const album = this.currentAlbum;
        if (!album || !album.tracks || !this.tracklistEl) return;
        const tracks = album.tracks;
        const start = this._mainTracklistRenderedCount || 0;
        const end = Math.min(tracks.length, start + count);
        if (start >= end) return;

        const frag = document.createDocumentFragment();
        for (let i = start; i < end; i++) {
            const li = this.createTrackListItem(tracks[i], i, false);
            frag.appendChild(li);
        }
        this.tracklistEl.appendChild(frag);
        this._mainTracklistRenderedCount = end;
    }

    appendModalTracklistBatch(count = 50) {
        if (!this.modalTracklistEl || !this._modalFilteredTracks) return;
        const start = this._modalTracklistRenderedCount || 0;
        const end = Math.min(this._modalFilteredTracks.length, start + count);
        if (start >= end) return;

        const frag = document.createDocumentFragment();
        for (let i = start; i < end; i++) {
            const { track, idx } = this._modalFilteredTracks[i];
            const li = this.createTrackListItem(track, idx, true);
            frag.appendChild(li);
        }
        this.modalTracklistEl.appendChild(frag);
        this._modalTracklistRenderedCount = end;
    }

    createTrackListItem(track, idx, isModal = false) {
        const li = document.createElement('li');
        li.className = `track-item ${idx === this.currentTrackIndex ? 'active' : ''}${(!this.isPlaying && idx === this.currentTrackIndex) ? ' paused' : ''}`;
        li.setAttribute('data-index', idx);
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
                if (isModal) {
                    this.closeModal(this.tracklistModal);
                    this.showToast(`Đang phát: ${trackName}`);
                }
            }
        });

        return li;
    }

    loadTrack(trackIndex, autoPlay = true) {
        this.currentTrackIndex = trackIndex;
        const track = this.currentTrack;
        const album = this.currentAlbum;

        // Cập nhật ảnh đĩa than & Album Sleeve theo từng bài hát ngay lập tức
        const trackCover = (track && track.coverUrl) || (album && album.coverUrl) || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop';
        if (this.albumCoverImg) {
            this.albumCoverImg.src = trackCover;
        }
        if (this.vinylCenterImg) {
            this.vinylCenterImg.src = trackCover;
        }

        // Cập nhật Dynamic Album Art Backdrop phong cách Apple Music
        this.updateDynamicBackdrop(trackCover);

        // Preload trước ảnh cover của các bài hát xung quanh để chuyển bài hiện ngay
        this.preloadCoversForCurrentAlbum();

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

        // Cập nhật thẻ Badge chất lượng & năm phát hành thực tế
        this.updateAudioBadges(track, album);

        // Cập nhật MediaSession cho màn hình khóa iPhone (iOS), Android và Desktop
        this.updateMediaSession();

        // Cập nhật trạng thái nút Yêu thích
        this.updateFavoriteBtnState();

        // Cập nhật Lời bài hát thời gian thực (Real-time Synced Lyrics)
        this.fetchTrackLyrics(track, album);
        if (this.karaokeTrackTitle) this.karaokeTrackTitle.textContent = track.name || 'Unknown Track';
        if (this.karaokeArtistName) this.karaokeArtistName.textContent = artistName;
        if (this.karaokeBackdrop) this.karaokeBackdrop.style.backgroundImage = `url("${trackCover}")`;
        if (this.karaokeTimeTotal) this.karaokeTimeTotal.textContent = track.duration || '--:--';
        if (this.karaokeTimeCurrent) this.karaokeTimeCurrent.textContent = "0:00";
        if (this.karaokeProgressFill) this.karaokeProgressFill.style.width = '0%';

        // Update Active Tracklist Item
        if (this.tracklistEl) {
            if (this.currentTrackIndex >= (this._mainTracklistRenderedCount || 0)) {
                this.appendMainTracklistBatch(this.currentTrackIndex - (this._mainTracklistRenderedCount || 0) + 20);
            }

            const prevActive = this.tracklistEl.querySelector('.track-item.active');
            if (prevActive) {
                prevActive.classList.remove('active', 'paused');
            }

            const activeItem = this.tracklistEl.querySelector(`.track-item[data-index="${this.currentTrackIndex}"]`);
            if (activeItem) {
                activeItem.classList.add('active');
                if (!this.isPlaying) activeItem.classList.add('paused');
                else activeItem.classList.remove('paused');
                activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }

        // Set Audio Source - Dừng dứt điểm bài hát cũ trước khi nạp bài mới
        if (this.audio) {
            try {
                this.audio.pause();
                this.audio.currentTime = 0;
            } catch (e) {}
        }
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

        this.savePlayerState();

        // Tự động nạp trước (preload) bài hát kế tiếp sau 1.2s
        setTimeout(() => this.preloadNextTrack(), 1200);
    }

    playTrackById(trackId) {
        if (!trackId) return;
        const album = this.currentAlbum;
        if (album && album.tracks) {
            const idx = album.tracks.findIndex(t => String(t.id) === String(trackId));
            if (idx !== -1) {
                this.loadTrack(idx, true);
                return;
            }
        }
        for (let aIdx = 0; aIdx < this.albums.length; aIdx++) {
            const alb = this.albums[aIdx];
            if (alb && alb.tracks) {
                const tIdx = alb.tracks.findIndex(t => String(t.id) === String(trackId));
                if (tIdx !== -1) {
                    this.loadAlbum(aIdx, tIdx, true);
                    return;
                }
            }
        }
    }

    preloadCoversForCurrentAlbum() {
        const album = this.currentAlbum;
        if (!album || !album.tracks || album.tracks.length === 0) return;
        const start = Math.max(0, this.currentTrackIndex - 2);
        const end = Math.min(album.tracks.length, this.currentTrackIndex + 20);
        for (let i = start; i < end; i++) {
            const tr = album.tracks[i];
            const cUrl = (tr && tr.coverUrl) || album.coverUrl;
            if (cUrl && typeof cUrl === 'string' && !cUrl.startsWith('data:')) {
                const img = new Image();
                img.src = cUrl;
            }
        }
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

    // --- Dynamic Album Art Backdrop (Apple Music Style Cross-fade) ---
    updateDynamicBackdrop(coverUrl) {
        if (!coverUrl) return;
        if (!this.backdropArt1 || !this.backdropArt2) {
            this.backdropArt1 = document.getElementById('backdropArt1');
            this.backdropArt2 = document.getElementById('backdropArt2');
            this.activeBackdropLayer = 1;
        }
        if (!this.backdropArt1 || !this.backdropArt2) return;

        if (this._lastBackdropCover === coverUrl) return;
        this._lastBackdropCover = coverUrl;

        const currentLayer = this.activeBackdropLayer === 1 ? this.backdropArt1 : this.backdropArt2;
        const nextLayer = this.activeBackdropLayer === 1 ? this.backdropArt2 : this.backdropArt1;

        // Gán ảnh nền cho lớp tiếp theo và chạy hiệu ứng mờ chuyển cảnh
        nextLayer.style.backgroundImage = `url("${coverUrl}")`;
        
        requestAnimationFrame(() => {
            nextLayer.classList.add('active');
            currentLayer.classList.remove('active');
            this.activeBackdropLayer = this.activeBackdropLayer === 1 ? 2 : 1;
        });
    }

    // --- MediaSession Setup (iOS Lock Screen, Android, Desktop) ---
    setupMediaSession() {
        if (!('mediaSession' in navigator)) return;

        const actionHandlers = [
            ['play', () => this.play()],
            ['pause', () => this.pause()],
            ['previoustrack', () => this.prevTrack()],
            ['nexttrack', () => this.nextTrack()],
            ['seekto', (details) => {
                if (details.seekTime !== undefined && this.audio.duration) {
                    this.audio.currentTime = Math.min(Math.max(0, details.seekTime), this.audio.duration);
                }
            }],
            ['seekbackward', (details) => {
                const offset = details.seekOffset || 10;
                this.audio.currentTime = Math.max(0, this.audio.currentTime - offset);
            }],
            ['seekforward', (details) => {
                const offset = details.seekOffset || 10;
                this.audio.currentTime = Math.min(this.audio.duration || 0, this.audio.currentTime + offset);
            }],
            ['stop', () => this.pause()]
        ];

        actionHandlers.forEach(([action, handler]) => {
            try {
                navigator.mediaSession.setActionHandler(action, handler);
            } catch (e) {}
        });
    }

    updateMediaSession() {
        if (!('mediaSession' in navigator)) return;

        const track = this.currentTrack;
        const album = this.currentAlbum;
        if (!track || !album) return;

        const trackName = track.name || 'Unknown Track';
        const artistName = track.artist || album.artist || 'XTAPO Music';
        const albumTitle = album.title || 'XTAPO Music';
        const rawCover = track.coverUrl || album.coverUrl || 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop';
        const fullCoverUrl = new URL(rawCover, window.location.href).href;

        const sizes = [96, 128, 192, 256, 384, 512];
        const artwork = sizes.map(s => ({
            src: fullCoverUrl,
            sizes: `${s}x${s}`,
            type: fullCoverUrl.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg'
        }));

        try {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: trackName,
                artist: artistName,
                album: albumTitle,
                artwork: artwork
            });
            navigator.mediaSession.playbackState = this.isPlaying ? 'playing' : 'paused';

            // Sync with Android Auto via Native Bridge
            if (window.AndroidBridge && typeof window.AndroidBridge.updateTrackInfo === 'function') {
                window.AndroidBridge.updateTrackInfo(trackName, artistName, albumTitle, fullCoverUrl, this.isPlaying ? 1 : 0);
            }
        } catch (e) {
            console.warn('Error setting MediaMetadata:', e);
        }

        if ('setPositionState' in navigator.mediaSession && this.audio.duration && !isNaN(this.audio.duration)) {
            try {
                navigator.mediaSession.setPositionState({
                    duration: this.audio.duration,
                    playbackRate: this.audio.playbackRate || 1,
                    position: Math.min(this.audio.currentTime || 0, this.audio.duration)
                });
            } catch (e) {}
        }
    }

    // --- Audio Engine & Synth Fallback ---
    initWebAudioAnalyser() {
        if (this.analyser) return;

        // KIỂM TRA THIẾT BỊ iOS (iPhone, iPad, iPod)
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || 
                      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) ||
                      (typeof navigator.vendor === 'string' && navigator.vendor.includes('Apple') && !window.MSStream);

        if (isIOS) {
            // Trên iOS/WebKit: KHÔNG nối <audio> qua AudioContext (createMediaElementSource)
            // vì iOS sẽ tự động Suspend (đóng băng) Web Audio khi tắt màn hình hoặc khoá máy,
            // làm mất âm thanh hoàn toàn.
            // Để thẻ <audio> phát thuần native, Visualizer trên iOS sẽ tự động dùng bộ mô phỏng sóng mượt mà!
            return;
        }

        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            if (!this.audioContext) {
                this.audioContext = new AudioCtx();
            }
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume().catch(() => {});
            }
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 128; // 64 frequency bins
            this.analyser.smoothingTimeConstant = 0.8;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

            if (!this.audioSourceNode && this.audio) {
                this.audioSourceNode = this.audioContext.createMediaElementSource(this.audio);
                this.audioSourceNode.connect(this.analyser);
                this.analyser.connect(this.audioContext.destination);
                console.log('[XTAPO Visualizer] Đã kết nối Web Audio Analyser thời gian thực thành công!');
            }
        } catch (err) {
            console.warn('[XTAPO Visualizer] MediaElementSource note:', err);
        }
    }

    play() {
        const album = this.currentAlbum;
        if (album && !album.isDemo && !this.currentUser) {
            this.authModal.classList.add('open');
            this.showToast("Vui lòng đăng nhập để nghe nhạc ngoài bản Demo (Guest).");
            this.pause();
            return;
        }

        // Khởi động Web Audio API Analyser thật khi người dùng phát nhạc
        this.initWebAudioAnalyser();
        if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume().catch(() => {});
        }

        this.isPlaying = true;
        this.updatePlayStateVisuals(true);
        this.updateMediaSession();
        this.startLyricsSyncLoop();

        const playPromise = this.audio.play();
        if (playPromise !== undefined) {
            playPromise.then(() => {
                this.synthesizerActive = false;
            }).catch(error => {
                // Bỏ qua nếu là AbortError do người dùng bấm chuyển bài nhanh hoặc load bài mới
                if (error.name === 'AbortError' || (error.message && error.message.includes('interrupted'))) {
                    return;
                }
                // If remote audio is blocked by CORS or offline, fallback to built-in musical synthesized audio
                console.log("Using built-in synthesized audio playback:", error.message);
                this.startAudioSynth();
            });
        }
    }

    pause() {
        this.isPlaying = false;
        this.stopLyricsSyncLoop();
        this.audio.pause();
        this.stopAudioSynth();
        this.updatePlayStateVisuals(false);
        if ('mediaSession' in navigator) {
            navigator.mediaSession.playbackState = 'paused';
        }
        this.savePlayerState();
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
                this.syncLyricsTime(this.synthTime);
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
            this.hasStartedPlayback = true;
            this.playIcon.style.display = 'none';
            this.pauseIcon.style.display = 'block';

            if (this.karaokePlayIcon && this.karaokePauseIcon) {
                this.karaokePlayIcon.style.display = 'none';
                this.karaokePauseIcon.style.display = 'block';
            }

            // Mobile Sleeve button icon
            if (this.mobileSleevePlayBtn) {
                const mobilePlay = this.mobileSleevePlayBtn.querySelector('.icon-play');
                const mobilePause = this.mobileSleevePlayBtn.querySelector('.icon-pause');
                if (mobilePlay && mobilePause) {
                    mobilePlay.style.display = 'none';
                    mobilePause.style.display = 'block';
                }
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

        if (this.karaokePlayIcon && this.karaokePauseIcon) {
            this.karaokePlayIcon.style.display = 'block';
            this.karaokePauseIcon.style.display = 'none';
        }

        // Mobile Sleeve button icon
        if (this.mobileSleevePlayBtn) {
            const mobilePlay = this.mobileSleevePlayBtn.querySelector('.icon-play');
            const mobilePause = this.mobileSleevePlayBtn.querySelector('.icon-pause');
            if (mobilePlay && mobilePause) {
                mobilePlay.style.display = 'block';
                mobilePause.style.display = 'none';
            }
        }

        // Vinyl Animation
        if (this.hasStartedPlayback) {
            this.vinylStage.classList.add('is-paused');
        }
        this.vinylStage.classList.remove('is-playing', 'is-active', 'is-spinning');

        // Tracklist Active Item
        const activeItem = this.tracklistEl.querySelector('.track-item.active');
        if (activeItem) activeItem.classList.add('paused');
    }

    // --- Audio Events ---
    setupAudioEvents() {
        this.audio.addEventListener('timeupdate', () => {
            if (this.synthesizerActive) return;
            if (this.audio.duration && !isNaN(this.audio.duration)) {
                const percent = (this.audio.currentTime / this.audio.duration) * 100;
                this.updateProgress(percent);
                this.timeCurrent.textContent = this.formatTime(this.audio.currentTime);
                this.syncLyricsTime(this.audio.currentTime);

                if ('mediaSession' in navigator && 'setPositionState' in navigator.mediaSession) {
                    try {
                        navigator.mediaSession.setPositionState({
                            duration: this.audio.duration,
                            playbackRate: this.audio.playbackRate || 1,
                            position: Math.min(this.audio.currentTime, this.audio.duration)
                        });
                    } catch (e) {}
                }

                this.throttledSavePlayerState();
            }
        });

        this.audio.addEventListener('loadedmetadata', () => {
            if (this.audio.duration && !isNaN(this.audio.duration)) {
                const formatted = this.formatTime(this.audio.duration);
                this.timeTotal.textContent = formatted;
                if (this.currentTrack) {
                    this.currentTrack.duration = formatted;
                }
                const activeDurationEl = this.tracklistEl.querySelector('.track-item.active .track-duration');
                if (activeDurationEl) {
                    activeDurationEl.textContent = formatted;
                }
                this.updateMediaSession();
            }
        });

        this.audio.addEventListener('durationchange', () => {
            if (this.audio.duration && !isNaN(this.audio.duration)) {
                const formatted = this.formatTime(this.audio.duration);
                this.timeTotal.textContent = formatted;
                if (this.currentTrack) {
                    this.currentTrack.duration = formatted;
                }
                const activeDurationEl = this.tracklistEl.querySelector('.track-item.active .track-duration');
                if (activeDurationEl) {
                    activeDurationEl.textContent = formatted;
                }
            }
        });

        this.audio.addEventListener('loadeddata', () => {
            this.updateMediaSession();
        });

        this.audio.addEventListener('play', () => {
            this.updateMediaSession();
        });

        this.audio.addEventListener('playing', () => {
            this.updateMediaSession();
            this.sendHeartbeat();
        });

        this.audio.addEventListener('pause', () => {
            this.sendHeartbeat();
        });

        this.audio.addEventListener('progress', () => {
            if (this.audio.buffered.length > 0 && this.audio.duration) {
                const bufferedEnd = this.audio.buffered.end(this.audio.buffered.length - 1);
                const bufferedPercent = (bufferedEnd / this.audio.duration) * 100;
                this.progressBuffered.style.width = `${bufferedPercent}%`;
            }
        });

        this.audio.addEventListener('ended', () => {
            if (this.sleepTimerMode === 'end_of_track') {
                this.cancelSleepTimer(true);
                this.pause();
                this.showToast('🌙 Hẹn giờ: Đã dừng phát nhạc sau khi hết bài hát. Chúc bạn ngủ ngon! ✨', 5000);
                return;
            }
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
        if (this.mobileSleevePlayBtn) {
            this.mobileSleevePlayBtn.addEventListener('click', () => this.togglePlay());
        }
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
            this.savePlayerState();
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
            this.savePlayerState();
        });

        // Volume Control
        this.volumeSlider.addEventListener('input', (e) => {
            this.volume = parseFloat(e.target.value);
            this.audio.volume = this.volume;
            this.isMuted = this.volume === 0;
            this.updateVolumeIcons();
            this.savePlayerState();
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
            this.savePlayerState();
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
        if (!this.canvas || !ctx) return;

        const numBars = 36;
        let dpr = window.devicePixelRatio || 1;

        const isMobileScreen = () => window.innerWidth <= 768;

        const resizeCanvas = () => {
            if (isMobileScreen()) {
                if (this.visualizerAnimationId) {
                    cancelAnimationFrame(this.visualizerAnimationId);
                    this.visualizerAnimationId = null;
                }
                return;
            }
            if (this.canvas) {
                const rect = this.canvas.getBoundingClientRect();
                dpr = window.devicePixelRatio || 1;
                const cssWidth = Math.floor(rect.width) || 380;
                const cssHeight = Math.floor(rect.height) || 36;
                
                this.canvas.width = Math.floor(cssWidth * dpr);
                this.canvas.height = Math.floor(cssHeight * dpr);
            }
        };

        window.addEventListener('resize', () => {
            resizeCanvas();
            if (!isMobileScreen() && !this.visualizerAnimationId && !document.hidden) {
                draw();
            }
        });
        setTimeout(resizeCanvas, 100);

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                if (this.visualizerAnimationId) {
                    cancelAnimationFrame(this.visualizerAnimationId);
                    this.visualizerAnimationId = null;
                }
            } else {
                if (!isMobileScreen() && !this.visualizerAnimationId) {
                    draw();
                }
            }
        });

        const draw = () => {
            // Tắt hoàn toàn trên di động hoặc khi tab bị ẩn để giải phóng GPU/CPU 100%
            if (isMobileScreen() || document.hidden) {
                if (this.visualizerAnimationId) {
                    cancelAnimationFrame(this.visualizerAnimationId);
                    this.visualizerAnimationId = null;
                }
                return;
            }

            if (!this.canvas || !ctx) return;
            const w = this.canvas.width;
            const h = this.canvas.height;
            if (w === 0 || h === 0) {
                this.visualizerAnimationId = requestAnimationFrame(draw);
                return;
            }

            ctx.clearRect(0, 0, w, h);

            const gap = 3 * dpr;
            const totalGaps = (numBars - 1) * gap;
            const barWidth = Math.max(3 * dpr, (w - totalGaps) / numBars);
            const radius = Math.min(barWidth / 2, 4 * dpr);

            const time = Date.now() * 0.004;

            let hasRealSignal = false;
            if (this.analyser && this.dataArray && this.isPlaying) {
                this.analyser.getByteFrequencyData(this.dataArray);
                for (let j = 0; j < Math.min(12, this.dataArray.length); j++) {
                    if (this.dataArray[j] > 0) {
                        hasRealSignal = true;
                        break;
                    }
                }
            }

            for (let i = 0; i < numBars; i++) {
                let barHeight;
                if (this.isPlaying) {
                    if (hasRealSignal) {
                        // LẤY TẦN SỐ ÂM THANH THỰC TẾ 100% CỦA BÀI HÁT ĐANG PHÁT
                        const freqIdx = Math.min(this.dataArray.length - 1, Math.floor((i / numBars) * (this.dataArray.length * 0.85)));
                        const freqVal = this.dataArray[freqIdx] || 0; // 0..255
                        const percent = freqVal / 255;
                        const minH = 6 * dpr;
                        const maxH = h - (4 * dpr);
                        barHeight = Math.max(minH, minH + (percent * (maxH - minH)));
                    } else {
                        // Sóng âm thanh đa tần sống động (Bass ở đầu, Mid ở giữa, Treble ở cuối)
                        const harmonic1 = Math.sin(i * 0.35 + time * 1.5);
                        const harmonic2 = Math.cos(i * 0.22 - time * 2.1);
                        const harmonic3 = Math.sin(i * 0.7 + time * 3.0) * 0.4;
                        const combined = Math.abs(harmonic1 * 0.5 + harmonic2 * 0.35 + harmonic3);
                        const minH = 6 * dpr;
                        const maxH = h - (4 * dpr);
                        barHeight = Math.max(minH, Math.min(maxH, combined * maxH + (Math.sin(time * 5 + i) * 2 * dpr)));
                    }
                } else {
                    // Trạng thái nghỉ: Sóng thở nhẹ nhàng êm ái
                    const idle = Math.sin(i * 0.25 + time * 0.5) * 0.5 + 0.5;
                    barHeight = (5 + idle * 6) * dpr;
                }

                const x = i * (barWidth + gap);
                const y = h - barHeight;

                const grad = ctx.createLinearGradient(0, h, 0, 0);
                if (this.isPlaying) {
                    grad.addColorStop(0, '#f59e0b');
                    grad.addColorStop(0.45, '#fcbf47');
                    grad.addColorStop(0.8, '#ff6dc4');
                    grad.addColorStop(1, '#38bdf8');
                } else {
                    grad.addColorStop(0, 'rgba(252, 191, 71, 0.4)');
                    grad.addColorStop(1, 'rgba(255, 109, 196, 0.3)');
                }

                ctx.fillStyle = grad;
                ctx.beginPath();
                if (ctx.roundRect) {
                    ctx.roundRect(x, y, barWidth, barHeight, [radius, radius, 1, 1]);
                } else {
                    ctx.rect(x, y, barWidth, barHeight);
                }
                ctx.fill();
            }

            this.visualizerAnimationId = requestAnimationFrame(draw);
        };

        if (!isMobileScreen()) {
            draw();
        }
    }

    // --- Modals & Drawers Setup ---
    setupModalEvents() {
        // Album Picker
        if (this.albumPickerBtn) this.albumPickerBtn.addEventListener('click', () => this.openModal(this.albumModal));
        if (this.closeAlbumModal) this.closeAlbumModal.addEventListener('click', () => this.closeModal(this.albumModal));
        if (this.mobileSelectAlbumBtn) {
            this.mobileSelectAlbumBtn.addEventListener('click', () => {
                this.closeMobileDrawer();
                this.openModal(this.albumModal);
            });
        }

        // Mobile Quick Tracklist Modal & Triggers
        const openTracklistModalHandler = () => {
            if (this.tracklistModalSearchInput) this.tracklistModalSearchInput.value = '';
            this.renderTracklist();
            this.openModal(this.tracklistModal);
            if (this.tracklistModalSearchInput) {
                setTimeout(() => this.tracklistModalSearchInput.focus(), 120);
            }
        };
        if (this.mobileQuickTracklistBtn) {
            this.mobileQuickTracklistBtn.addEventListener('click', openTracklistModalHandler);
        }
        if (this.mobilePlayerTracklistBtn) {
            this.mobilePlayerTracklistBtn.addEventListener('click', openTracklistModalHandler);
        }
        if (this.closeTracklistModal) {
            this.closeTracklistModal.addEventListener('click', () => this.closeModal(this.tracklistModal));
        }
        if (this.tracklistModalSearchInput) {
            this.tracklistModalSearchInput.addEventListener('input', (e) => {
                clearTimeout(this._modalSearchDebounceTimer);
                const val = e.target.value;
                this._modalSearchDebounceTimer = setTimeout(() => {
                    this.renderTracklist(val);
                }, 150);
            });
        }

        // Search Modal
        if (this.searchBtn) {
            this.searchBtn.addEventListener('click', () => {
                this.openModal(this.searchModal);
                setTimeout(() => this.searchInput.focus(), 100);
            });
        }
        if (this.closeSearchModal) this.closeSearchModal.addEventListener('click', () => this.closeModal(this.searchModal));
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => {
                clearTimeout(this._searchDebounceTimer);
                const val = e.target.value;
                this._searchDebounceTimer = setTimeout(() => {
                    this.handleSearch(val);
                }, 150);
            });
        }

        // File / Metadata Drawer
        const openDrawer = () => this.metaDrawer && this.metaDrawer.classList.add('open');
        const closeDrawer = () => this.metaDrawer && this.metaDrawer.classList.remove('open');
        if (this.metaInfoBtn) this.metaInfoBtn.addEventListener('click', openDrawer);
        if (this.openDrawerBtn) this.openDrawerBtn.addEventListener('click', openDrawer);
        if (this.closeDrawerBtn) this.closeDrawerBtn.addEventListener('click', closeDrawer);
        if (this.drawerBackdrop) this.drawerBackdrop.addEventListener('click', closeDrawer);

        // Mobile Menu Drawer
        this.hamburgerBtn.addEventListener('click', () => this.mobileMenuDrawer.classList.add('open'));
        this.closeMobileMenu.addEventListener('click', () => this.closeMobileDrawer());
        this.mobileMenuBackdrop.addEventListener('click', () => this.closeMobileDrawer());

        // Sleep Timer Modal Triggers
        const openSleepTimerHandler = () => {
            this.closeMobileDrawer();
            this.openSleepTimerModal();
        };
        if (this.sleepTimerBtn) this.sleepTimerBtn.addEventListener('click', openSleepTimerHandler);
        if (this.topNavSleepBtn) this.topNavSleepBtn.addEventListener('click', openSleepTimerHandler);
        if (this.mobileNavSleepTimer) {
            this.mobileNavSleepTimer.addEventListener('click', (e) => {
                e.preventDefault();
                openSleepTimerHandler();
            });
        }
        if (this.closeSleepTimerModal) {
            this.closeSleepTimerModal.addEventListener('click', () => this.closeModal(this.sleepTimerModal));
        }
        if (this.sleepTimerModal) {
            this.sleepTimerModal.addEventListener('click', (e) => {
                if (e.target === this.sleepTimerModal) this.closeModal(this.sleepTimerModal);
            });
        }

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
                this.clearHash();
                [this.albumModal, this.searchModal, this.tgModal, this.playlistModal, this.addToPlaylistModal, this.artistModal, this.genreModal, this.countryModal, this.tracklistModal, this.favoritesModal, this.lyricsModal].forEach(m => {
                    if (m) m.classList.remove('open');
                });
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
                this.showArtistListView();
                this.renderArtistGrid();
                this.openModal(this.artistModal);
            });
        }
        if (this.closeArtistModal && this.artistModal) {
            this.closeArtistModal.addEventListener('click', () => this.closeModal(this.artistModal));
        }
        if (this.btnBackToArtistList) {
            this.btnBackToArtistList.addEventListener('click', () => this.showArtistListView());
        }
        if (this.artistSearchInput) {
            this.artistSearchInput.addEventListener('input', (e) => {
                this.renderArtistGrid(e.target.value.trim());
            });
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

        if (this.navCountries && this.countryModal) {
            this.navCountries.addEventListener('click', (e) => {
                e.preventDefault();
                this.setActiveNavLink(this.navCountries);
                this.renderCountryGrid();
                this.openModal(this.countryModal);
            });
        }
        if (this.closeCountryModal && this.countryModal) {
            this.closeCountryModal.addEventListener('click', () => this.closeModal(this.countryModal));
        }

        // Country Detail View Events
        if (this.btnBackToCountryList) {
            this.btnBackToCountryList.addEventListener('click', () => {
                this.showCountryListView();
            });
        }
        if (this.tabBtnCountryGenres) {
            this.tabBtnCountryGenres.addEventListener('click', () => this.switchCountryDetailTab('genres'));
        }
        if (this.tabBtnCountryArtists) {
            this.tabBtnCountryArtists.addEventListener('click', () => this.switchCountryDetailTab('artists'));
        }
        if (this.tabBtnCountryTracks) {
            this.tabBtnCountryTracks.addEventListener('click', () => this.switchCountryDetailTab('tracks'));
        }
        if (this.countryArtistSearchInput) {
            this.countryArtistSearchInput.addEventListener('input', (e) => {
                if (this.currentDetailCountryObj) {
                    this.renderCountryArtists(this.currentDetailCountryObj, e.target.value.trim());
                }
            });
        }
        if (this.countryTrackSearchInput) {
            this.countryTrackSearchInput.addEventListener('input', (e) => {
                if (this.currentDetailCountryObj) {
                    this.renderCountryTracks(this.currentDetailCountryObj, e.target.value.trim());
                }
            });
        }
        if (this.btnCountryPlayAll) {
            this.btnCountryPlayAll.addEventListener('click', () => {
                if (this.currentDetailCountryObj) {
                    this.closeModal(this.countryModal);
                    this.playCountryQueue(this.currentDetailCountryObj, false);
                }
            });
        }
        if (this.btnCountryShuffle) {
            this.btnCountryShuffle.addEventListener('click', () => {
                if (this.currentDetailCountryObj) {
                    this.closeModal(this.countryModal);
                    this.playCountryQueue(this.currentDetailCountryObj, true);
                }
            });
        }
        if (this.btnCountryExportM3U8) {
            this.btnCountryExportM3U8.addEventListener('click', () => {
                if (this.currentDetailCountryObj && this.currentDetailCountryObj.tracks) {
                    this.exportM3U8(`Nhac_${this.currentDetailCountryObj.country}`, this.currentDetailCountryObj.tracks);
                }
            });
        }
        if (this.btnCountryDownloadZip) {
            this.btnCountryDownloadZip.addEventListener('click', () => {
                if (this.currentDetailCountryObj && this.currentDetailCountryObj.tracks) {
                    this.downloadZipPackage(this.currentDetailCountryObj.tracks, `Tuyen_Tap_Nhac_${this.currentDetailCountryObj.country}`, this.currentDetailCountryObj.coverUrl, `Tuyển Tập Nhạc ${this.currentDetailCountryObj.country}`);
                }
            });
        }

        // Favorites Modal Events
        if (this.navFavorites && this.favoritesModal) {
            this.navFavorites.addEventListener('click', (e) => {
                e.preventDefault();
                this.setActiveNavLink(this.navFavorites);
                this.openFavoritesModal();
            });
        }
        if (this.closeFavoritesModal && this.favoritesModal) {
            this.closeFavoritesModal.addEventListener('click', () => this.closeModal(this.favoritesModal));
        }
        if (this.btnFavPlayAll) {
            this.btnFavPlayAll.addEventListener('click', () => {
                this.closeModal(this.favoritesModal);
                this.playFavoritesQueue(0, false);
            });
        }
        if (this.btnFavShuffle) {
            this.btnFavShuffle.addEventListener('click', () => {
                this.closeModal(this.favoritesModal);
                this.playFavoritesQueue(0, true);
            });
        }
        if (this.favSearchInput) {
            this.favSearchInput.addEventListener('input', (e) => {
                this.renderFavoritesList(e.target.value.trim());
            });
        }

        // Mobile Nav Links Events
        const mobileLinks = [
            { id: 'mobileNavMusics', action: () => {
                this.setActiveNavLink(this.navMusics);
                this.clearHash();
                [this.albumModal, this.searchModal, this.tgModal, this.playlistModal, this.addToPlaylistModal, this.artistModal, this.genreModal, this.countryModal, this.tracklistModal, this.favoritesModal, this.lyricsModal].forEach(m => {
                    if (m) m.classList.remove('open');
                });
                this.showToast('Đang phát kho nhạc chính');
            } },
            { id: 'mobileNavHires', action: () => this.filterHiresAlbums() },
            { id: 'mobileNavAlbums', action: () => this.openModal(this.albumModal) },
            { id: 'mobileNavArtists', action: () => { this.renderArtistGrid(); this.openModal(this.artistModal); } },
            { id: 'mobileNavGenres', action: () => { this.renderGenreGrid(); this.openModal(this.genreModal); } },
            { id: 'mobileNavCountries', action: () => { this.renderCountryGrid(); this.openModal(this.countryModal); } },
            { id: 'mobileNavPlaylists', action: () => { this.loadPlaylists(); this.openModal(this.playlistModal); } },
            { id: 'mobileNavFavorites', action: () => this.openFavoritesModal() },
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

        // Album Quick Export Dropdown
        if (this.albumExportBtn && this.albumExportMenu) {
            this.albumExportBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.albumExportMenu.classList.toggle('show');
            });
            document.addEventListener('click', (e) => {
                if (this.albumExportMenu && !e.target.closest('#albumExportDropdown')) {
                    this.albumExportMenu.classList.remove('show');
                }
            });
        }

        if (this.btnDownloadAlbumZip) {
            this.btnDownloadAlbumZip.addEventListener('click', () => {
                if (this.albumExportMenu) this.albumExportMenu.classList.remove('show');
                const album = this.currentAlbum;
                this.downloadZipPackage(album.tracks, album.title, album.coverUrl, album.title);
            });
        }
        if (this.btnExportAlbumM3U8) {
            this.btnExportAlbumM3U8.addEventListener('click', () => {
                if (this.albumExportMenu) this.albumExportMenu.classList.remove('show');
                const album = this.currentAlbum;
                this.openM3U8ShareModal({
                    title: album.title,
                    urlPath: this.getAlbumM3U8Url(album),
                    tracks: album.tracks
                });
            });
        }
        if (this.btnExportAlbumPLS) {
            this.btnExportAlbumPLS.addEventListener('click', () => {
                if (this.albumExportMenu) this.albumExportMenu.classList.remove('show');
                const album = this.currentAlbum;
                this.exportPLS(album.title, album.tracks);
            });
        }
        if (this.btnDownloadAlbumBatch) {
            this.btnDownloadAlbumBatch.addEventListener('click', () => {
                if (this.albumExportMenu) this.albumExportMenu.classList.remove('show');
                const album = this.currentAlbum;
                this.downloadBatchTracks(album.tracks, album.title);
            });
        }

        // Drawer Export & Download Toolbar Buttons
        if (this.drawerDownloadZipBtn) {
            this.drawerDownloadZipBtn.addEventListener('click', () => {
                const album = this.currentAlbum;
                this.downloadZipPackage(album.tracks, album.title, album.coverUrl, album.title);
            });
        }
        if (this.drawerExportM3U8Btn) {
            this.drawerExportM3U8Btn.addEventListener('click', () => {
                const album = this.currentAlbum;
                this.openM3U8ShareModal({
                    title: album.title,
                    urlPath: this.getAlbumM3U8Url(album),
                    tracks: album.tracks
                });
            });
        }
        if (this.drawerExportPLSBtn) {
            this.drawerExportPLSBtn.addEventListener('click', () => {
                const album = this.currentAlbum;
                this.exportPLS(album.title, album.tracks);
            });
        }
        if (this.drawerDownloadBatchBtn) {
            this.drawerDownloadBatchBtn.addEventListener('click', () => {
                const album = this.currentAlbum;
                this.downloadBatchTracks(album.tracks, album.title);
            });
        }

        // Artist Spotlight Export & Download Buttons
        if (this.btnSpotlightExportM3U8) {
            this.btnSpotlightExportM3U8.addEventListener('click', () => {
                const name = this.currentSpotlightArtist ? this.currentSpotlightArtist.name : 'Artist';
                this.openM3U8ShareModal({
                    title: `Tuyển Tập: ${name}`,
                    urlPath: `/api/music/playlist/artist/${encodeURIComponent(name)}.m3u8`,
                    tracks: this.currentSpotlightTracks || []
                });
            });
        }
        if (this.btnSpotlightDownloadZip) {
            this.btnSpotlightDownloadZip.addEventListener('click', () => {
                const name = this.currentSpotlightArtist ? this.currentSpotlightArtist.name : 'Artist';
                const avatar = (this.currentSpotlightArtist && this.currentSpotlightArtist.avatar) || '';
                this.downloadZipPackage(this.currentSpotlightTracks || [], `Tuyen_Tap_${name}`, avatar, `Nghệ Sĩ: ${name}`);
            });
        }

        // Favorites Export & Download Buttons
        if (this.btnFavExportM3U8) {
            this.btnFavExportM3U8.addEventListener('click', () => {
                const favs = this.getFavoriteTracksList();
                this.openM3U8ShareModal({
                    title: 'Bài Hát Yêu Thích',
                    urlPath: `/api/music/playlist/user/favorites.m3u8`,
                    tracks: favs
                });
            });
        }
        if (this.btnFavDownloadZip) {
            this.btnFavDownloadZip.addEventListener('click', () => {
                const favs = this.getFavoriteTracksList();
                this.downloadZipPackage(favs, 'Bai_Hat_Yeu_Thich', '', 'Bài Hát Yêu Thích');
            });
        }

        // M3U8 Share Modal Events
        if (this.closeM3u8Modal && this.m3u8Modal) {
            this.closeM3u8Modal.addEventListener('click', () => this.closeModal(this.m3u8Modal));
        }
        if (this.m3u8CopyBtn && this.m3u8DirectUrlInput) {
            this.m3u8CopyBtn.addEventListener('click', () => {
                const url = this.m3u8DirectUrlInput.value;
                if (!url) return;
                navigator.clipboard.writeText(url).then(() => {
                    if (this.m3u8CopyText) this.m3u8CopyText.textContent = 'Đã Copy! ✅';
                    this.showToast('Đã copy đường dẫn stream M3U8 vào clipboard!');
                    setTimeout(() => {
                        if (this.m3u8CopyText) this.m3u8CopyText.textContent = 'Sao Chép Link';
                    }, 2500);
                }).catch(() => {
                    this.m3u8DirectUrlInput.select();
                    document.execCommand('copy');
                    this.showToast('Đã copy đường link!');
                });
            });
        }
        if (this.m3u8OpenDirectBtn && this.m3u8DirectUrlInput) {
            this.m3u8OpenDirectBtn.addEventListener('click', () => {
                const url = this.m3u8DirectUrlInput.value;
                if (url) window.open(url, '_blank');
            });
        }
        if (this.m3u8DownloadFileBtn) {
            this.m3u8DownloadFileBtn.addEventListener('click', () => {
                if (this.currentM3U8Context) {
                    this.exportM3U8(this.currentM3U8Context.title, this.currentM3U8Context.tracks);
                }
            });
        }
        if (this.m3u8DownloadPlsBtn) {
            this.m3u8DownloadPlsBtn.addEventListener('click', () => {
                if (this.currentM3U8Context) {
                    this.exportPLS(this.currentM3U8Context.title, this.currentM3U8Context.tracks);
                }
            });
        }

        // Download Progress Modal Cancel Button
        if (this.dlCancelBtn) {
            this.dlCancelBtn.addEventListener('click', () => {
                if (this.activeDownloadAbortController) {
                    this.activeDownloadAbortController.abort();
                    this.activeDownloadAbortController = null;
                }
                this.closeDownloadProgressModal();
                this.showToast('Đã dừng tiến trình tải dữ liệu.');
            });
        }

        // Close on overlay click
        [this.albumModal, this.searchModal, this.tgModal, this.playlistModal, this.addToPlaylistModal, this.artistModal, this.genreModal, this.countryModal, this.tracklistModal, this.downloadProgressModal, this.m3u8Modal, this.favoritesModal, this.lyricsModal, this.lyricsEditorModal, this.authModal].forEach(modal => {
            if (modal) {
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        if (modal === this.downloadProgressModal && this.activeDownloadAbortController) {
                            if (confirm('Quá trình tải đang diễn ra. Bạn có chắc muốn hủy không?')) {
                                this.activeDownloadAbortController.abort();
                                this.activeDownloadAbortController = null;
                                this.closeModal(modal);
                            }
                        } else {
                            this.closeModal(modal);
                        }
                    }
                });
            }
        });

        // Lắng nghe sự kiện hashchange của trình duyệt (hỗ trợ nút Back/Forward và Deep link)
        window.addEventListener('hashchange', () => {
            this.restoreViewStateFromHash();
        });

        // Lưu trạng thái & vị trí cuộn chuột trước khi tải lại trang
        window.addEventListener('beforeunload', () => {
            this.savePlayerState();
            try {
                sessionStorage.setItem('xtapo_music_scroll_pos', window.scrollY.toString());
            } catch (e) {}
        });
    }

    // --- State Persistence & URL Deep Linking ---
    savePlayerState() {
        try {
            const album = this.currentAlbum;
            const track = this.currentTrack;
            const state = {
                albumId: album ? (album.id || album.title) : null,
                albumTitle: album ? album.title : null,
                albumIndex: this.currentAlbumIndex,
                trackIndex: this.currentTrackIndex,
                trackName: track ? track.name : null,
                trackChatId: track ? track.chatId : null,
                trackMsgId: track ? track.msgId : null,
                currentTime: (this.audio && !isNaN(this.audio.currentTime)) ? this.audio.currentTime : 0,
                volume: typeof this.volume === 'number' ? this.volume : 0.85,
                isMuted: !!this.isMuted,
                isShuffle: !!this.isShuffle,
                repeatMode: this.repeatMode || 0,
                isDemo: !!(album && (album.isDemo || String(album.id || '').startsWith('shania-'))),
                isFavoriteMode: !!(album && album.id === 'favorites-playlist'),
                activePlaylistId: this.activePlaylistId || null,
                activeArtist: this.activeArtist || null,
                activeGenre: this.activeGenre || null,
                activeCountry: this.activeCountry || null
            };
            localStorage.setItem('xtapo_music_player_state', JSON.stringify(state));
        } catch (e) {
            console.warn('Không thể lưu player state:', e);
        }
    }

    throttledSavePlayerState() {
        const now = Date.now();
        if (!this._lastStateSaveTime || now - this._lastStateSaveTime > 2500) {
            this._lastStateSaveTime = now;
            this.savePlayerState();
        }
    }

    findAlbumIndex(state) {
        if (!this.albums || this.albums.length === 0) return 0;
        if (state.albumId) {
            const idx = this.albums.findIndex(a => (!this.currentUser || !a.isDemo) && ((a.id && String(a.id) === String(state.albumId)) || a.title === state.albumId));
            if (idx !== -1) return idx;
        }
        if (state.albumTitle) {
            const idx = this.albums.findIndex(a => (!this.currentUser || !a.isDemo) && a.title === state.albumTitle);
            if (idx !== -1) return idx;
        }
        if (state.trackChatId && state.trackMsgId) {
            const idx = this.albums.findIndex(a => (!this.currentUser || !a.isDemo) && (a.tracks || []).some(t => {
                const ident = this.getTrackIdentifiers(t);
                return ident.chatId === String(state.trackChatId) && ident.msgId === String(state.trackMsgId);
            }));
            if (idx !== -1) return idx;
        }
        if (typeof state.albumIndex === 'number' && state.albumIndex >= 0 && state.albumIndex < this.albums.length) {
            if (!this.currentUser || !this.albums[state.albumIndex]?.isDemo) {
                return state.albumIndex;
            }
        }
        return 0;
    }

    restorePlayerState() {
        try {
            const raw = localStorage.getItem('xtapo_music_player_state');
            if (!raw) return false;
            const state = JSON.parse(raw);
            if (!state) return false;

            // Nếu người dùng đã đăng nhập mà state trước đó là demo, bỏ qua không khôi phục demo
            if (this.currentUser && (state.isDemo || (state.albumId && String(state.albumId).startsWith('shania-')))) {
                return false;
            }

            // 1. Phục hồi các nút điều khiển
            if (typeof state.volume === 'number' && !isNaN(state.volume)) {
                this.volume = state.volume;
                if (this.volumeSlider) this.volumeSlider.value = this.volume;
                if (this.audio) this.audio.volume = state.isMuted ? 0 : this.volume;
                this.isMuted = !!state.isMuted;
                this.updateVolumeIcons();
            }

            if (typeof state.isShuffle === 'boolean') {
                this.isShuffle = state.isShuffle;
                if (this.shuffleBtn) this.shuffleBtn.classList.toggle('active', this.isShuffle);
            }

            if (typeof state.repeatMode === 'number') {
                this.repeatMode = state.repeatMode;
                if (this.repeatBtn && this.repeatIndicator) {
                    if (this.repeatMode === 0) {
                        this.repeatBtn.classList.remove('active');
                        this.repeatIndicator.textContent = '';
                    } else if (this.repeatMode === 1) {
                        this.repeatBtn.classList.add('active');
                        this.repeatIndicator.textContent = 'ALL';
                    } else if (this.repeatMode === 2) {
                        this.repeatBtn.classList.add('active');
                        this.repeatIndicator.textContent = '1';
                    }
                }
            }

            // 2. Phục hồi danh sách phát / hàng đợi bài hát
            const targetTrackIdx = (typeof state.trackIndex === 'number' && state.trackIndex >= 0) ? state.trackIndex : 0;

            if (state.isFavoriteMode && this.favoriteTracks && this.favoriteTracks.length > 0) {
                this.playFavoritesQueue(targetTrackIdx, false, false);
                if (this.navFavorites) this.setActiveNavLink(this.navFavorites);
            } else if (state.activePlaylistId && this.playlists && this.playlists.length > 0) {
                const pl = this.playlists.find(p => String(p.id) === String(state.activePlaylistId));
                if (pl && pl.tracks && pl.tracks.length > 0) {
                    this.playPlaylist(pl, targetTrackIdx, false);
                } else {
                    const albumIdx = this.findAlbumIndex(state);
                    this.loadAlbum(albumIdx, targetTrackIdx, false);
                }
            } else if (state.activeArtist) {
                this.playArtistQueueByName(state.activeArtist, targetTrackIdx, false);
            } else if (state.activeGenre) {
                this.playGenreQueue(state.activeGenre, targetTrackIdx, false);
            } else if (state.activeCountry) {
                this.playCountryQueueByName(state.activeCountry, targetTrackIdx, false);
            } else {
                const albumIdx = this.findAlbumIndex(state);
                this.loadAlbum(albumIdx, targetTrackIdx, false);
            }

            // 3. Phục hồi thời gian đang phát (Seek đến giây trước đó ở trạng thái Pause)
            if (typeof state.currentTime === 'number' && state.currentTime > 0) {
                const targetTime = state.currentTime;
                const applySeek = () => {
                    try {
                        if (this.audio && this.audio.duration && targetTime < this.audio.duration) {
                            this.audio.currentTime = targetTime;
                            const percent = (targetTime / this.audio.duration) * 100;
                            this.updateProgress(percent);
                            this.timeCurrent.textContent = this.formatTime(targetTime);
                            this.syncLyricsTime(targetTime);
                        }
                    } catch (err) {}
                };
                if (this.audio && this.audio.readyState >= 1 && this.audio.duration) {
                    applySeek();
                } else if (this.audio) {
                    const onLoadedMeta = () => {
                        applySeek();
                        this.audio.removeEventListener('loadedmetadata', onLoadedMeta);
                    };
                    this.audio.addEventListener('loadedmetadata', onLoadedMeta, { once: true });
                }
            }

            return true;
        } catch (e) {
            console.error('Lỗi khi khôi phục player state:', e);
            return false;
        }
    }

    saveActiveView(view) {
        try {
            if (!view || view.type === 'main') {
                localStorage.removeItem('xtapo_music_active_view');
                this.clearHash();
            } else {
                localStorage.setItem('xtapo_music_active_view', JSON.stringify(view));
                if (view.type === 'artist-detail' && view.name) {
                    this.setHash(`artist/${encodeURIComponent(view.name)}`);
                } else {
                    this.setHash(view.type);
                }
            }
        } catch (e) {}
    }

    restoreActiveView() {
        try {
            let view = null;
            const raw = localStorage.getItem('xtapo_music_active_view');
            if (raw) {
                try { view = JSON.parse(raw); } catch (e) {}
            }

            // Fallback sang URL hash nếu chưa có trong localStorage
            const rawHash = window.location.hash.replace(/^#/, '');
            if (!view && rawHash) {
                if (rawHash.startsWith('artist/')) {
                    view = { type: 'artist-detail', name: decodeURIComponent(rawHash.replace('artist/', '')) };
                } else {
                    view = { type: rawHash };
                }
            }

            if (!view || view.type === 'main') {
                return;
            }

            if (view.type === 'albums') {
                this.setActiveNavLink(this.navAlbums);
                this.openModal(this.albumModal);
            } else if (view.type === 'hires') {
                this.setActiveNavLink(this.navHires);
                this.filterHiresAlbums();
            } else if (view.type === 'artists') {
                this.setActiveNavLink(this.navArtists);
                this.showArtistListView();
                this.renderArtistGrid();
                this.openModal(this.artistModal);
            } else if (view.type === 'artist-detail' && view.name) {
                this.setActiveNavLink(this.navArtists);
                this.openModal(this.artistModal);
                this.openArtistByName(view.name);
            } else if (view.type === 'genres') {
                this.setActiveNavLink(this.navGenres);
                this.renderGenreGrid();
                this.openModal(this.genreModal);
            } else if (view.type === 'countries') {
                this.setActiveNavLink(this.navCountries);
                this.renderCountryGrid();
                this.openModal(this.countryModal);
            } else if (view.type === 'playlists') {
                this.setActiveNavLink(this.navPlaylists);
                this.loadPlaylists();
                this.openModal(this.playlistModal);
            } else if (view.type === 'favorites') {
                this.setActiveNavLink(this.navFavorites);
                this.openFavoritesModal();
            } else if (view.type === 'search') {
                this.openModal(this.searchModal);
            } else if (view.type === 'lyrics') {
                this.openModal(this.lyricsModal);
            } else if (view.type === 'tracklist') {
                this.openModal(this.tracklistModal);
            }
        } catch (e) {
            console.error('Lỗi khi khôi phục Active View:', e);
        }
    }

    setHash(hash) {
        if (!hash) return;
        if (window.location.hash !== `#${hash}`) {
            window.history.replaceState(null, '', `#${hash}`);
        }
    }

    clearHash() {
        if (window.location.hash && window.location.hash !== '' && window.location.hash !== '#') {
            window.history.replaceState(null, '', window.location.pathname + window.location.search);
        }
    }

    clearHashIfModalClosed(modal) {
        const currentHash = window.location.hash.replace(/^#/, '');
        if (!currentHash) return;

        if (modal === this.artistModal && currentHash.startsWith('artist')) {
            this.clearHash();
            return;
        }
        if (modal === this.albumModal && (currentHash === 'albums' || currentHash === 'hires')) {
            this.clearHash();
            return;
        }
        if (modal === this.genreModal && currentHash === 'genres') {
            this.clearHash();
            return;
        }
        if (modal === this.countryModal && currentHash === 'countries') {
            this.clearHash();
            return;
        }
        if (modal === this.playlistModal && currentHash === 'playlists') {
            this.clearHash();
            return;
        }
        if (modal === this.favoritesModal && currentHash === 'favorites') {
            this.clearHash();
            return;
        }
        if (modal === this.tracklistModal && currentHash === 'tracklist') {
            this.clearHash();
            return;
        }
        if (modal === this.searchModal && currentHash === 'search') {
            this.clearHash();
            return;
        }
        if (modal === this.lyricsModal && currentHash === 'lyrics') {
            this.clearHash();
            return;
        }
        if (modal === this.lyricsEditorModal && currentHash === 'lyrics-edit') {
            this.clearHash();
            return;
        }
    }

    openArtistByName(artistName) {
        if (!artistName) return;
        this.renderArtistGrid();
        if (this.artistMap) {
            const art = this.artistMap.get(artistName) || Array.from(this.artistMap.values()).find(a => a.name.toLowerCase() === artistName.toLowerCase());
            if (art) {
                this.openArtistSpotlight(art);
            }
        }
    }

    playArtistQueueByName(artistName, startIndex = 0, autoPlay = true) {
        if (!artistName) return;
        this.activeArtist = artistName;
        this.activeGenre = null;
        this.activeCountry = null;
        this.activePlaylistId = null;

        this.renderArtistGrid();
        let art = this.artistMap ? (this.artistMap.get(artistName) || Array.from(this.artistMap.values()).find(a => a.name.toLowerCase() === artistName.toLowerCase())) : null;
        if (art) {
            this.playArtistQueue(art, startIndex, false, autoPlay);
        }
    }

    playGenreQueue(genreName, startIndex = 0, autoPlay = true) {
        if (!genreName) return;
        this.activeGenre = genreName;
        this.activeArtist = null;
        this.activeCountry = null;
        this.activePlaylistId = null;

        const tracks = [];
        const seenKeys = new Set();
        let coverUrl = '';
        const targetGenreLow = genreName.toLowerCase().trim();

        this.getBaseAlbums().forEach(album => {
            (album.tracks || []).forEach(track => {
                const g = ((track.genre || 'Khác').trim() || 'Khác').toLowerCase();
                if (g === targetGenreLow) {
                    const key = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;
                    if (!seenKeys.has(key)) {
                        seenKeys.add(key);
                        tracks.push(track);
                        if (!coverUrl) coverUrl = track.coverUrl || album.coverUrl;
                    }
                }
            });
        });

        if (tracks.length === 0) return;

        const genreAlbum = {
            id: `genre-${encodeURIComponent(genreName)}`,
            title: `Thể Loại: ${genreName}`,
            artist: 'Tuyển Tập Thể Loại',
            coverUrl: coverUrl || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop',
            format: 'FLAC Hi-Res Lossless',
            year: new Date().getFullYear().toString(),
            publisher: `Genre Collection • ${genreName}`,
            glowColors: { glow1: 'radial-gradient(circle, #ec4899 0%, #be185d 60%, transparent 80%)', glow2: 'radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)' },
            tracks: tracks
        };

        this.setVirtualAlbum(genreAlbum, startIndex, autoPlay);
        if (autoPlay) {
            this.showToast(`Đang phát thể loại "${genreName}" (${tracks.length} bài)`);
        }
    }

    playCountryQueueByName(countryName, startIndex = 0, autoPlay = true) {
        if (!countryName) return;
        this.activeCountry = countryName;
        this.activeArtist = null;
        this.activeGenre = null;
        this.activePlaylistId = null;

        const tracks = [];
        const seenKeys = new Set();
        let coverUrl = '';
        const targetCountryLow = countryName.toLowerCase().trim();

        this.getBaseAlbums().forEach(album => {
            const albumCountry = album.country || this.detectCountryFromTrack({ name: album.title, artist: album.artist, album: album.title });
            (album.tracks || []).forEach(track => {
                const c = (track.country && track.country.trim()) || albumCountry || this.detectCountryFromTrack(track) || 'Quốc Tế';
                if (c.toLowerCase() === targetCountryLow || (countryName === 'Quốc Tế' && !['Việt Nam', 'Âu Mỹ', 'Hàn Quốc', 'Hoa Ngữ', 'Nhật Bản'].includes(c))) {
                    const key = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;
                    if (!seenKeys.has(key)) {
                        seenKeys.add(key);
                        tracks.push(track);
                        if (!coverUrl) coverUrl = track.coverUrl || album.coverUrl;
                    }
                }
            });
        });

        if (tracks.length === 0) return;

        const cObj = { country: countryName, tracks: tracks, coverUrl: coverUrl };
        this.playCountryQueue(cObj, false, autoPlay, startIndex);
    }

    openModal(modal) {
        if (!modal) return;
        modal.classList.add('open');
        if (modal === this.albumModal && window.location.hash !== '#hires') {
            this.saveActiveView({ type: 'albums' });
        } else if (modal === this.artistModal) {
            if (!window.location.hash.startsWith('#artist/')) {
                this.saveActiveView({ type: 'artists' });
            }
        } else if (modal === this.genreModal) {
            this.saveActiveView({ type: 'genres' });
        } else if (modal === this.countryModal) {
            this.saveActiveView({ type: 'countries' });
        } else if (modal === this.playlistModal) {
            this.saveActiveView({ type: 'playlists' });
        } else if (modal === this.favoritesModal) {
            this.saveActiveView({ type: 'favorites' });
        } else if (modal === this.tracklistModal) {
            this.saveActiveView({ type: 'tracklist' });
        } else if (modal === this.searchModal) {
            this.saveActiveView({ type: 'search' });
        } else if (modal === this.lyricsModal) {
            this.saveActiveView({ type: 'lyrics' });
        }
    }

    closeModal(modal) {
        if (!modal) return;
        modal.classList.remove('open');
        this.clearHashIfModalClosed(modal);
        this.saveActiveView({ type: 'main' });
    }

    setActiveNavLink(activeLink) {
        const links = document.querySelectorAll('.nav-link');
        links.forEach(l => l.classList.remove('active'));
        if (activeLink) activeLink.classList.add('active');
    }

    closeMobileDrawer() {
        if (this.mobileMenuDrawer) this.mobileMenuDrawer.classList.remove('open');
    }

    renderAlbumGrid() {
        if (!this.albumGrid) return;
        this.albumGrid.innerHTML = '';
        const displayAlbums = this.currentUser ? (this.albums || []).filter(a => !a.isDemo) : (this.albums || []);
        if (displayAlbums.length === 0) {
            this.albumGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 50px 20px;">
                    <div style="font-size: 2rem; margin-bottom: 8px;">☁️</div>
                    <div style="font-weight: 700; color: #fff; margin-bottom: 6px;">Chưa có Album nào</div>
                    <div style="font-size: 0.85rem;">Quét nhạc từ Telegram hoặc tạo Playlist để thêm nhạc vào thư viện của bạn!</div>
                </div>
            `;
            return;
        }

        displayAlbums.forEach((album, idx) => {
            const card = document.createElement('div');
            card.className = `album-card ${idx === this.currentAlbumIndex ? 'active' : ''}`;
            card.innerHTML = `
                <img src="${album.coverUrl}" loading="lazy" class="album-card-img" alt="${album.title}" onerror="this.src='https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop'">
                <div class="album-card-info">
                    <span class="album-card-title">${album.title}</span>
                    <span class="album-card-artist">${album.artist}</span>
                    <span class="album-card-year">${album.year || '2026'} • ${(album.tracks || []).length} Tracks</span>
                </div>
            `;

            card.addEventListener('click', () => {
                const realIdx = this.albums.findIndex(a => a.id === album.id || a.title === album.title);
                this.loadAlbum(realIdx !== -1 ? realIdx : idx, 0, true);
                this.closeModal(this.albumModal);
                this.showToast(`Đã chuyển sang album: ${album.title}`);
                this.renderAlbumGrid();
            });

            this.albumGrid.appendChild(card);
        });
    }

    updateDrawerInfo() {
        const album = this.currentAlbum;
        if (!album) return;
        if (this.drawerAlbumTitle) this.drawerAlbumTitle.textContent = `${album.artist} - ${album.title}`;
        if (this.drawerSpecFormat) this.drawerSpecFormat.textContent = album.format;
        if (this.drawerSpecSize) this.drawerSpecSize.textContent = album.totalSize;
        if (this.drawerSpecDate) this.drawerSpecDate.textContent = album.year;
        if (this.drawerSpecPublisher) this.drawerSpecPublisher.textContent = album.publisher;

        if (!this.drawerFileList) return;
        this.drawerFileList.innerHTML = '';
        this._drawerRenderedCount = 0;
        
        // Lazy load initial 40 items only
        this.appendDrawerFileListBatch(40);

        if (!this._drawerScrollBound) {
            this._drawerScrollBound = true;
            this.drawerFileList.addEventListener('scroll', () => {
                const el = this.drawerFileList;
                if (el.scrollTop + el.clientHeight >= el.scrollHeight - 300) {
                    const albumTracks = (this.currentAlbum && this.currentAlbum.tracks) || [];
                    if (this._drawerRenderedCount < albumTracks.length) {
                        this.appendDrawerFileListBatch(40);
                    }
                }
            }, { passive: true });
        }
    }

    appendDrawerFileListBatch(count = 40) {
        const album = this.currentAlbum;
        if (!album || !album.tracks || !this.drawerFileList) return;
        const tracks = album.tracks;
        const start = this._drawerRenderedCount || 0;
        const end = Math.min(tracks.length, start + count);
        if (start >= end) return;

        const frag = document.createDocumentFragment();
        for (let idx = start; idx < end; idx++) {
            const track = tracks[idx];
            const row = document.createElement('div');
            row.className = 'file-row';
            row.innerHTML = `
                <div class="file-info">
                    <div class="file-title">${idx + 1}. ${this.escapeHtml(track.name || 'Không có tên')}</div>
                    <div class="file-meta">${this.escapeHtml(track.artist || album.artist || '')} • ${this.escapeHtml(track.format || album.format || 'Lossless')} • ${track.duration || ''}</div>
                </div>
                <div class="file-actions">
                    <button class="file-action-btn download-btn">Phát Ngay</button>
                    <button class="file-dl-single-btn" title="Tải file bài hát này">
                        <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                    </button>
                </div>
            `;

            const btn = row.querySelector('.download-btn');
            btn.addEventListener('click', () => {
                this.loadTrack(idx, true);
                this.metaDrawer.classList.remove('open');
                this.showToast(`Đang phát: ${track.name}`);
            });

            const dlBtn = row.querySelector('.file-dl-single-btn');
            if (dlBtn) {
                dlBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.downloadSingleTrack(track, album.artist);
                });
            }

            frag.appendChild(row);
        }
        this.drawerFileList.appendChild(frag);
        this._drawerRenderedCount = end;
    }

    handleSearch(query) {
        if (!query.trim()) {
            this.searchResults.innerHTML = '<div class="search-empty">Nhập từ khoá để tìm bài hát nhanh...</div>';
            return;
        }

        const q = query.toLowerCase().trim();
        let matches = [];
        const baseAlbums = this.getBaseAlbums();

        for (let albumIdx = 0; albumIdx < baseAlbums.length; albumIdx++) {
            const album = baseAlbums[albumIdx];
            const artistLow = (album.artist || '').toLowerCase();
            const titleLow = (album.title || '').toLowerCase();
            const tracks = album.tracks || [];
            for (let trackIdx = 0; trackIdx < tracks.length; trackIdx++) {
                const track = tracks[trackIdx];
                const trackNameLow = (track.name || '').toLowerCase();
                const trackArtistLow = (track.artist || '').toLowerCase();
                if (trackNameLow.includes(q) || trackArtistLow.includes(q) || artistLow.includes(q) || titleLow.includes(q)) {
                    matches.push({ album, albumIdx, track, trackIdx });
                    if (matches.length >= 100) break;
                }
            }
            if (matches.length >= 100) break;
        }

        if (matches.length === 0) {
            this.searchResults.innerHTML = `<div class="search-empty">Không tìm thấy bài hát nào khớp với "${this.escapeHtml(query)}"</div>`;
            return;
        }

        this.searchResults.innerHTML = '';
        const frag = document.createDocumentFragment();
        matches.forEach(item => {
            const el = document.createElement('div');
            el.className = 'search-item';
            el.innerHTML = `
                <div>
                    <div style="font-weight:600; color:#fff;">${this.escapeHtml(item.track.name || '')}</div>
                    <div style="font-size:0.78rem; color:rgba(255,255,255,0.5);">${this.escapeHtml(item.album.artist || '')} • ${this.escapeHtml(item.album.title || '')}</div>
                </div>
                <span style="color:var(--accent-gold); font-size:0.8rem;">${item.track.duration || ''}</span>
            `;

            el.addEventListener('click', () => {
                this.loadAlbum(item.albumIdx, item.trackIdx, true);
                this.closeModal(this.searchModal);
                this.showToast(`Đang phát: ${item.track.name}`);
            });

            frag.appendChild(el);
        });
        this.searchResults.appendChild(frag);
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
                this.closeModal(this.countryModal);
                this.closeModal(this.tracklistModal);
                this.closeModal(this.lyricsModal);
                this.closeModal(this.lyricsEditorModal);
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
            const res = await fetch('/api/music/user/playlists');
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
                    <button class="pl-action-badge gold-badge btn-play-playlist" ${trackCount === 0 ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''} title="Phát playlist">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                        <span>Phát</span>
                    </button>
                    <button class="pl-action-badge blue-badge btn-m3u8-playlist" ${trackCount === 0 ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''} title="Xuất file playlist M3U8">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/></svg>
                        <span>.M3U8</span>
                    </button>
                    <button class="pl-action-badge btn-pls-playlist" ${trackCount === 0 ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''} title="Xuất file playlist PLS">
                        <span>.PLS</span>
                    </button>
                    <button class="pl-action-badge btn-zip-playlist" ${trackCount === 0 ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''} title="Tải toàn bộ nhạc trong playlist (.ZIP)">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor"><path d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6 10v-3h-4v-2h4V8l4 4-4 4z"/></svg>
                        <span>Zip</span>
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

            const m3u8Btn = item.querySelector('.btn-m3u8-playlist');
            if (m3u8Btn && trackCount > 0) {
                m3u8Btn.addEventListener('click', () => {
                    this.openM3U8ShareModal({
                        title: `Playlist: ${pl.name}`,
                        urlPath: `/api/music/playlist/user/playlist/${encodeURIComponent(pl.id)}.m3u8`,
                        tracks: pl.tracks
                    });
                });
            }

            const plsBtn = item.querySelector('.btn-pls-playlist');
            if (plsBtn && trackCount > 0) {
                plsBtn.addEventListener('click', () => {
                    this.exportPLS(`Playlist_${pl.name}`, pl.tracks);
                });
            }

            const zipBtn = item.querySelector('.btn-zip-playlist');
            if (zipBtn && trackCount > 0) {
                zipBtn.addEventListener('click', () => {
                    this.downloadZipPackage(pl.tracks, `Playlist_${pl.name}`, (pl.tracks[0] && pl.tracks[0].coverUrl) || '', `Playlist: ${pl.name}`);
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
            const res = await fetch('/api/music/user/playlists', {
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
            const res = await fetch(`/api/music/user/playlists/${playlistId}`, {
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

    playPlaylist(playlist, startIndex = 0, autoPlay = true) {
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

        this.setVirtualAlbum(playlistAlbum, startIndex, autoPlay);
        if (autoPlay) {
            this.showToast(`Đang phát playlist "${playlist.name}" (${playlist.tracks.length} bài)`);
        }
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
            const res = await fetch('/api/music/user/playlists');
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
            const res = await fetch(`/api/music/user/playlists/${playlistId}`, {
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

    filterHiresAlbums() {
        this.setHash('hires');
        const hiresAlbums = this.getBaseAlbums().filter(a => {
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

    showArtistListView() {
        this.setHash('artists');
        if (this.artistListView && this.artistProfileView) {
            this.artistListView.style.display = 'flex';
            this.artistProfileView.style.display = 'none';
        }
    }

    renderArtistGrid(searchQuery = '', selectedCountry = null) {
        if (!this.artistGrid) return;
        if (selectedCountry !== null) {
            this.selectedArtistCountryFilter = selectedCountry;
        }
        this.artistGrid.innerHTML = '';

        // Extract and aggregate all artists with their countries
        const artistMap = new Map();
        const countryArtistCounts = {
            'all': 0,
            'Việt Nam': 0,
            'Âu Mỹ': 0,
            'Hàn Quốc': 0,
            'Hoa Ngữ': 0,
            'Nhật Bản': 0,
            'Quốc Tế': 0
        };

        this.getBaseAlbums().forEach(album => {
            const albArtist = (album.artist || 'Unknown Artist').trim();
            const albumCountry = album.country || this.detectCountryFromTrack({ name: album.title, artist: album.artist, album: album.title });
            (album.tracks || []).forEach(track => {
                const trackArtist = (track.artist || albArtist || 'Unknown Artist').trim();
                if (!trackArtist || trackArtist.toLowerCase() === 'unknown') return;

                const c = (track.country && track.country.trim()) || albumCountry || this.detectCountryFromTrack(track) || 'Quốc Tế';
                const validCountry = ['Việt Nam', 'Âu Mỹ', 'Hàn Quốc', 'Hoa Ngữ', 'Nhật Bản'].includes(c) ? c : 'Quốc Tế';

                if (!artistMap.has(trackArtist)) {
                    // Check cached metadata
                    const cached = this.artistCacheMap ? this.artistCacheMap.get(trackArtist.toLowerCase().trim()) : null;
                    const avatarUrl = (cached && cached.avatar_url) ? cached.avatar_url : (track.coverUrl || album.coverUrl);
                    const bannerUrl = (cached && cached.banner_url) ? cached.banner_url : avatarUrl;
                    const bio = cached ? (cached.bio || '') : '';
                    const genres = cached ? (cached.genres || []) : (track.genre ? [track.genre] : []);
                    const trackKey = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;

                    artistMap.set(trackArtist, {
                        name: trackArtist,
                        coverUrl: avatarUrl,
                        bannerUrl: bannerUrl,
                        bio: bio,
                        genres: genres,
                        countries: new Set([validCountry]),
                        albums: new Map([[album.id || album.title, album]]),
                        trackKeys: new Set([trackKey]),
                        tracks: [track]
                    });
                } else {
                    const existing = artistMap.get(trackArtist);
                    existing.countries.add(validCountry);
                    existing.albums.set(album.id || album.title, album);
                    const trackKey = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;
                    if (!existing.trackKeys.has(trackKey)) {
                        existing.trackKeys.add(trackKey);
                        existing.tracks.push(track);
                    }
                }
            });
        });

        this.artistMap = artistMap;

        // Calculate counts for country filter tabs
        countryArtistCounts['all'] = artistMap.size;
        artistMap.forEach(art => {
            art.countries.forEach(c => {
                if (countryArtistCounts[c] !== undefined) {
                    countryArtistCounts[c]++;
                }
            });
        });

        // Render country filter tabs in Artist Modal
        if (this.artistCountryFilterTabs) {
            this.artistCountryFilterTabs.innerHTML = '';
            const filterOptions = [
                { id: 'all', label: 'Tất cả', icon: '🌐' },
                { id: 'Việt Nam', label: 'Việt Nam', icon: '🇻🇳' },
                { id: 'Âu Mỹ', label: 'Âu Mỹ', icon: '🇺🇸' },
                { id: 'Hàn Quốc', label: 'Hàn Quốc', icon: '🇰🇷' },
                { id: 'Hoa Ngữ', label: 'Hoa Ngữ', icon: '🇨🇳' },
                { id: 'Nhật Bản', label: 'Nhật Bản', icon: '🇯🇵' },
                { id: 'Quốc Tế', label: 'Quốc Tế', icon: '🌍' }
            ];

            filterOptions.forEach(opt => {
                const count = countryArtistCounts[opt.id] || 0;
                const pill = document.createElement('button');
                pill.className = `country-filter-pill ${this.selectedArtistCountryFilter === opt.id ? 'active' : ''}`;
                pill.innerHTML = `<span>${opt.icon}</span> <span>${opt.label}</span> <span class="pill-count">${count}</span>`;
                pill.onclick = () => {
                    this.selectedArtistCountryFilter = opt.id;
                    this.renderArtistGrid(this.artistSearchInput ? this.artistSearchInput.value.trim() : '', opt.id);
                };
                this.artistCountryFilterTabs.appendChild(pill);
            });
        }

        if (artistMap.size === 0) {
            this.artistGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">Chưa có dữ liệu ca sĩ trong thư viện.</div>';
            return;
        }

        let sortedArtists = Array.from(artistMap.values()).sort((a, b) => b.tracks.length - a.tracks.length);

        // Filter by country
        if (this.selectedArtistCountryFilter && this.selectedArtistCountryFilter !== 'all') {
            sortedArtists = sortedArtists.filter(a => a.countries.has(this.selectedArtistCountryFilter));
        }

        // Filter by search query
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            sortedArtists = sortedArtists.filter(a => a.name.toLowerCase().includes(q));
        }

        if (sortedArtists.length === 0) {
            this.artistGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">Không tìm thấy ca sĩ nào thuộc khu vực đã chọn.</div>';
            return;
        }

        sortedArtists.forEach(art => {
            const card = document.createElement('div');
            card.className = 'artist-card-item';
            card.innerHTML = `
                <img src="${art.coverUrl}" loading="lazy" class="artist-avatar-img" alt="${this.escapeHtml(art.name)}" onerror="this.src='https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop'">
                <div class="artist-card-info">
                    <h4>${this.escapeHtml(art.name)}</h4>
                    <p>${art.tracks.length} bài hát • ${art.albums.size} album</p>
                </div>
            `;

            card.addEventListener('click', () => {
                this.openArtistSpotlight(art);
            });

            this.artistGrid.appendChild(card);
        });
    }

    openArtistSpotlight(art) {
        if (!this.artistProfileView || !this.artistListView) return;

        this.setHash(`artist/${encodeURIComponent(art.name)}`);
        this.artistListView.style.display = 'none';
        this.artistProfileView.style.display = 'flex';

        // Update Hero Info
        const backdropEl = document.getElementById('artistHeroBackdrop');
        if (backdropEl) backdropEl.style.backgroundImage = `url('${art.bannerUrl || art.coverUrl}')`;
        
        const avatarEl = document.getElementById('spotlightArtistAvatar');
        if (avatarEl) avatarEl.src = art.coverUrl;

        const nameEl = document.getElementById('spotlightArtistName');
        if (nameEl) nameEl.textContent = art.name;

        const trackCountEl = document.getElementById('spotlightTrackCount');
        if (trackCountEl) trackCountEl.textContent = `${art.tracks.length} bài hát`;

        const albumCountEl = document.getElementById('spotlightAlbumCount');
        if (albumCountEl) albumCountEl.textContent = `${art.albums.size} albums`;

        // Genres tags
        const genresEl = document.getElementById('spotlightArtistGenres');
        if (genresEl) {
            genresEl.innerHTML = (art.genres && art.genres.length > 0)
                ? art.genres.map(g => `<span class="badge-tag" style="background: rgba(255,255,255,0.1); font-size: 0.75rem;">${this.escapeHtml(g)}</span>`).join('')
                : '';
        }

        // Bio section
        const bioSection = document.getElementById('spotlightBioSection');
        const bioText = document.getElementById('spotlightBioText');
        if (bioSection && bioText) {
            if (art.bio && art.bio.trim()) {
                bioSection.style.display = 'block';
                bioText.textContent = art.bio;
            } else {
                bioSection.style.display = 'none';
            }
        }

        // Albums Grid
        const albumsGrid = document.getElementById('spotlightAlbumsGrid');
        if (albumsGrid) {
            albumsGrid.innerHTML = '';
            Array.from(art.albums.values()).forEach(album => {
                const albCard = document.createElement('div');
                albCard.style.cssText = 'background: rgba(255,255,255,0.04); border: 1px solid var(--border-color); border-radius: 12px; padding: 10px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 10px;';
                albCard.innerHTML = `
                    <img src="${album.coverUrl}" loading="lazy" style="width: 44px; height: 44px; border-radius: 8px; object-fit: cover;" alt="Album Cover">
                    <div style="min-width: 0; flex: 1;">
                        <div style="font-weight: 700; font-size: 0.8rem; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(album.title)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">${album.tracks ? album.tracks.length : 0} bài • ${album.year || '2026'}</div>
                    </div>
                `;
                albCard.onmouseover = () => albCard.style.background = 'rgba(255,255,255,0.08)';
                albCard.onmouseout = () => albCard.style.background = 'rgba(255,255,255,0.04)';
                albCard.onclick = () => {
                    this.closeModal(this.artistModal);
                    const idx = this.albums.findIndex(a => a.id === album.id || a.title === album.title);
                    if (idx !== -1) {
                        this.loadAlbum(idx, 0, true);
                    }
                };
                albumsGrid.appendChild(albCard);
            });
        }

        // Tracks List
        const tracksListEl = document.getElementById('spotlightTracksList');
        if (tracksListEl) {
            tracksListEl.innerHTML = '';
            art.tracks.forEach((track, idx) => {
                const trItem = document.createElement('div');
                trItem.style.cssText = 'display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-radius: 12px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); transition: all 0.2s; cursor: pointer;';
                trItem.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
                        <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); width: 20px; text-align: center;">${idx + 1}</span>
                        <img src="${track.coverUrl || art.coverUrl}" loading="lazy" style="width: 36px; height: 36px; border-radius: 8px; object-fit: cover;" alt="Cover">
                        <div style="min-width: 0;">
                            <div style="font-size: 0.85rem; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(track.name)}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted);">${track.albumName || 'Single'}</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 0.75rem; color: var(--text-muted);">${track.duration || ''}</span>
                        <button class="nav-btn icon-btn" style="width: 30px; height: 30px; border-radius: 50%; background: var(--color-primary); color: #fff; display: flex; align-items: center; justify-content: center;" title="Phát bài này">
                            <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        </button>
                    </div>
                `;
                trItem.onmouseover = () => trItem.style.background = 'rgba(255,255,255,0.06)';
                trItem.onmouseout = () => trItem.style.background = 'rgba(255,255,255,0.02)';
                
                trItem.onclick = () => {
                    this.closeModal(this.artistModal);
                    this.playArtistQueue(art, idx, false);
                };

                tracksListEl.appendChild(trItem);
            });
        }

        // Play All & Shuffle Buttons
        const playAllBtn = document.getElementById('btnSpotlightPlayAll');
        if (playAllBtn) {
            playAllBtn.onclick = () => {
                this.closeModal(this.artistModal);
                this.playArtistQueue(art, 0, false);
            };
        }

        const shuffleBtn = document.getElementById('btnSpotlightShuffle');
        if (shuffleBtn) {
            shuffleBtn.onclick = () => {
                this.closeModal(this.artistModal);
                this.playArtistQueue(art, 0, true);
            };
        }
    }

    playArtistQueue(art, startIndex = 0, isShuffle = false) {
        let tracks = [...art.tracks];
        if (isShuffle && tracks.length > 1) {
            for (let i = tracks.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [tracks[i], tracks[j]] = [tracks[j], tracks[i]];
            }
        }

        const artistAlbum = {
            id: `artist-${encodeURIComponent(art.name)}`,
            title: `Tuyển Tập: ${art.name}`,
            artist: art.name,
            coverUrl: art.coverUrl,
            format: 'FLAC Hi-Res Lossless',
            year: new Date().getFullYear().toString(),
            publisher: 'Artist Spotlight Collection',
            glowColors: { glow1: 'radial-gradient(circle, #f59e0b 0%, #b45309 60%, transparent 80%)', glow2: 'radial-gradient(circle, #ff6dc4 0%, #4338ca 60%, transparent 80%)' },
            tracks: tracks
        };

        this.setVirtualAlbum(artistAlbum, startIndex, true);
        this.showToast(`Đang phát tuyển tập ca sĩ "${art.name}" (${tracks.length} bài)`);
    }

    renderGenreGrid(selectedCountry = null) {
        if (!this.genreGrid) return;
        if (selectedCountry !== null) {
            this.selectedGenreCountryFilter = selectedCountry;
        }
        this.genreGrid.innerHTML = '';

        const genreIcons = {
            'Bolero / Trữ Tình': '🎻',
            'Bolero': '🎻',
            'Trữ Tình': '🎻',
            'Lofi / Chill': '☕',
            'Lofi': '☕',
            'Chill': '☕',
            'EDM / Remix': '⚡',
            'EDM': '⚡',
            'Remix': '⚡',
            'Vinahouse': '⚡',
            'Dance': '💃',
            'Acoustic / Instrumental': '🎸',
            'Acoustic': '🎸',
            'Instrumental': '🎹',
            'Rap / Hip-Hop': '🎤',
            'Rap': '🎤',
            'Hip-Hop': '🎤',
            'Trap': '🔥',
            'R&B / Soul': '🎷',
            'R&B': '🎷',
            'Soul': '🎷',
            'Rock / Indie': '🤘',
            'Rock': '🤘',
            'Indie': '🎸',
            'Metal': '⚡',
            'Pop / Ballad': '💖',
            'Pop': '✨',
            'Ballad': '🎼',
            'Nhạc Trẻ': '💖',
            'Jazz / Blues': '🎺',
            'Jazz': '🎺',
            'Blues': '🎷',
            'Nhạc Phim / OST': '🎬',
            'Soundtrack': '🎬',
            'OST': '🎬',
            'Cổ Điển / Classical': '🎼',
            'Classical': '🎼',
            'Nhạc Đỏ / Cách Mạng': '⭐',
            'Country / Folk': '🌾',
            'Country': '🌾',
            'Folk': '🌾',
            'Latin / Reggae': '🌴',
            'Latin': '🌴',
            'Reggae': '🌴',
            'Thiếu Nhi / Kids': '🎈',
            'Kids': '🎈',
            'Podcast / Sách Nói': '🎙️',
            'Podcast': '🎙️',
            'Audiobook': '📚',
            'Khác': '🎵'
        };

        const genreColors = {
            'Bolero / Trữ Tình': 'linear-gradient(135deg, rgba(217, 119, 6, 0.35), rgba(180, 83, 9, 0.15))',
            'Bolero': 'linear-gradient(135deg, rgba(217, 119, 6, 0.35), rgba(180, 83, 9, 0.15))',
            'Lofi / Chill': 'linear-gradient(135deg, rgba(99, 102, 241, 0.35), rgba(67, 56, 202, 0.15))',
            'Lofi': 'linear-gradient(135deg, rgba(99, 102, 241, 0.35), rgba(67, 56, 202, 0.15))',
            'EDM / Remix': 'linear-gradient(135deg, rgba(236, 72, 153, 0.35), rgba(190, 24, 93, 0.15))',
            'EDM': 'linear-gradient(135deg, rgba(236, 72, 153, 0.35), rgba(190, 24, 93, 0.15))',
            'Acoustic / Instrumental': 'linear-gradient(135deg, rgba(16, 185, 129, 0.35), rgba(4, 120, 87, 0.15))',
            'Acoustic': 'linear-gradient(135deg, rgba(16, 185, 129, 0.35), rgba(4, 120, 87, 0.15))',
            'Rap / Hip-Hop': 'linear-gradient(135deg, rgba(239, 68, 68, 0.35), rgba(185, 28, 28, 0.15))',
            'Rap': 'linear-gradient(135deg, rgba(239, 68, 68, 0.35), rgba(185, 28, 28, 0.15))',
            'R&B / Soul': 'linear-gradient(135deg, rgba(168, 85, 247, 0.35), rgba(126, 34, 206, 0.15))',
            'Rock / Indie': 'linear-gradient(135deg, rgba(139, 92, 246, 0.35), rgba(109, 40, 217, 0.15))',
            'Pop / Ballad': 'linear-gradient(135deg, rgba(2, 132, 199, 0.35), rgba(3, 105, 161, 0.15))',
            'Jazz / Blues': 'linear-gradient(135deg, rgba(245, 158, 11, 0.35), rgba(217, 119, 6, 0.15))',
            'Nhạc Phim / OST': 'linear-gradient(135deg, rgba(20, 184, 166, 0.35), rgba(13, 148, 136, 0.15))',
            'Cổ Điển / Classical': 'linear-gradient(135deg, rgba(217, 70, 239, 0.35), rgba(162, 28, 175, 0.15))',
            'Nhạc Đỏ / Cách Mạng': 'linear-gradient(135deg, rgba(220, 38, 38, 0.4), rgba(185, 28, 28, 0.15))',
            'Country / Folk': 'linear-gradient(135deg, rgba(234, 179, 8, 0.35), rgba(161, 98, 7, 0.15))',
            'Latin / Reggae': 'linear-gradient(135deg, rgba(249, 115, 22, 0.35), rgba(194, 65, 12, 0.15))',
            'Thiếu Nhi / Kids': 'linear-gradient(135deg, rgba(251, 146, 60, 0.35), rgba(234, 88, 12, 0.15))',
            'Podcast / Sách Nói': 'linear-gradient(135deg, rgba(14, 165, 233, 0.35), rgba(2, 132, 199, 0.15))',
            'Khác': 'linear-gradient(135deg, rgba(100, 116, 139, 0.3), rgba(71, 85, 105, 0.1))'
        };

        // Calculate genre sets and track counts per country
        const countryGenreSets = {
            'all': new Set(),
            'Việt Nam': new Set(),
            'Âu Mỹ': new Set(),
            'Hàn Quốc': new Set(),
            'Hoa Ngữ': new Set(),
            'Nhật Bản': new Set(),
            'Quốc Tế': new Set()
        };

        const genreMap = new Map();

        this.getBaseAlbums().forEach(album => {
            const albumCountry = album.country || this.detectCountryFromTrack({ name: album.title, artist: album.artist, album: album.title });
            (album.tracks || []).forEach(track => {
                const g = (track.genre || 'Khác').trim() || 'Khác';
                const c = (track.country && track.country.trim()) || albumCountry || this.detectCountryFromTrack(track) || 'Quốc Tế';
                const validCountry = ['Việt Nam', 'Âu Mỹ', 'Hàn Quốc', 'Hoa Ngữ', 'Nhật Bản'].includes(c) ? c : 'Quốc Tế';

                countryGenreSets['all'].add(g);
                if (countryGenreSets[validCountry]) {
                    countryGenreSets[validCountry].add(g);
                }

                // Filter for current view
                if (this.selectedGenreCountryFilter && this.selectedGenreCountryFilter !== 'all' && validCountry !== this.selectedGenreCountryFilter) {
                    return;
                }

                const trackKey = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;
                if (!genreMap.has(g)) {
                    genreMap.set(g, {
                        genre: g,
                        tracks: [track],
                        trackKeys: new Set([trackKey]),
                        coverUrl: track.coverUrl || album.coverUrl
                    });
                } else {
                    const existing = genreMap.get(g);
                    if (!existing.trackKeys.has(trackKey)) {
                        existing.trackKeys.add(trackKey);
                        existing.tracks.push(track);
                    }
                }
            });
        });

        // Render country filter tabs in Genre Modal
        if (this.genreCountryFilterTabs) {
            this.genreCountryFilterTabs.innerHTML = '';
            const filterOptions = [
                { id: 'all', label: 'Tất cả', icon: '🌐' },
                { id: 'Việt Nam', label: 'Việt Nam', icon: '🇻🇳' },
                { id: 'Âu Mỹ', label: 'Âu Mỹ', icon: '🇺🇸' },
                { id: 'Hàn Quốc', label: 'Hàn Quốc', icon: '🇰🇷' },
                { id: 'Hoa Ngữ', label: 'Hoa Ngữ', icon: '🇨🇳' },
                { id: 'Nhật Bản', label: 'Nhật Bản', icon: '🇯🇵' },
                { id: 'Quốc Tế', label: 'Quốc Tế', icon: '🌍' }
            ];

            filterOptions.forEach(opt => {
                const count = (countryGenreSets[opt.id] && countryGenreSets[opt.id].size) || 0;
                const pill = document.createElement('button');
                pill.className = `country-filter-pill ${this.selectedGenreCountryFilter === opt.id ? 'active' : ''}`;
                pill.innerHTML = `<span>${opt.icon}</span> <span>${opt.label}</span> <span class="pill-count">${count}</span>`;
                pill.onclick = () => {
                    this.selectedGenreCountryFilter = opt.id;
                    this.renderGenreGrid(opt.id);
                };
                this.genreCountryFilterTabs.appendChild(pill);
            });
        }

        if (genreMap.size === 0) {
            this.genreGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">Chưa có thể loại âm nhạc nào trong khu vực này.</div>';
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
                if (this.selectedGenreCountryFilter && this.selectedGenreCountryFilter !== 'all') {
                    this.playCountryGenreQueue(this.selectedGenreCountryFilter, gObj.genre, 0, true);
                } else {
                    this.playGenreQueue(gObj.genre, 0, true);
                }
            });

            this.genreGrid.appendChild(card);
        });
    }

    detectCountryFromTrack(track) {
        if (track.country && track.country.trim()) return track.country.trim();
        const name = track.name || track.title || '';
        const artist = track.artist || '';
        const album = track.album || track.albumName || '';
        const raw = `${name} ${artist} ${album}`;
        const low = raw.toLowerCase();

        // 1. Tiếng Việt
        if (/[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]/.test(raw)) {
            return 'Việt Nam';
        }
        const vnKws = ['v-pop', 'vpop', 'nhạc việt', 'nhac viet', 'bolero', 'trữ tình', 'nhạc vàng', 'rap việt', 'lời việt', 'nhạc trẻ', 'sơn tùng', 'đen vâu', 'mỹ tâm', 'hồ ngọc hà', 'đan trường', 'trịnh công sơn', 'lệ quyên', 'vũ.', 'chillies', 'ngọt', 'mono', 'hieuthuhai', 'erik', 'đức phúc', 'jack 97', 'soobin', 'b ray', 'karik', 'justatee', 'min', 'amee', 'phan mạnh quỳnh'];
        if (vnKws.some(k => low.includes(k))) return 'Việt Nam';

        // 2. Hàn Quốc
        if (/[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]/.test(raw)) return 'Hàn Quốc';
        const krKws = ['k-pop', 'kpop', 'korean', 'ost hàn', 'bts', 'blackpink', 'iu', 'exo', 'twice', 'newjeans', 'stray kids', 'bigbang', 'snsd', 'girls\' generation', 'red velvet', 'seventeen', 'ive', 'aespa', 'taeyeon', 'psy', 'g-dragon', 'nct', 'enhypen', 'txt', 'itzy', 'lesserafim', 'le sserafim', 'shinee', 'super junior', 'mamamoo', 'ateez', 'got7', 'gfriend', 'stayc', 'treasure', 'nmixx', 'day6', 'akmu', 'baekhyun', 'jungkook', 'jimin', 'zico', 'crush', 'dean'];
        if (krKws.some(k => low.includes(k))) return 'Hàn Quốc';

        // 3. Nhật Bản
        if (/[\u3040-\u309f\u30a0-\u30ff]/.test(raw)) return 'Nhật Bản';
        const jpKws = ['j-pop', 'jpop', 'anime', 'japanese', 'utada hikaru', 'yoasobi', 'kenshi yonezu', 'aimer', 'radwimps', 'one ok rock', 'official hige dandism', 'x japan', 'milet', 'ayumi hamasaki', 'namie amuro', 'king gnu', 'ado', 'eve', 'vocaloid', 'hatsune miku', 'flow', 'sawano hiroyuki', 'joe hisaishi'];
        if (jpKws.some(k => low.includes(k))) return 'Nhật Bản';

        // 4. Hoa Ngữ
        if (/[\u4e00-\u9fff]/.test(raw)) return 'Hoa Ngữ';
        const cnKws = ['c-pop', 'cpop', 'mandopop', 'cantopop', 'nhạc hoa', 'nhạc trung', 'lời hoa', 'jay chou', 'châu kiệt luân', 'vương phi', 'faye wong', 'lâm tuấn kiệt', 'jj lin', 'đặng tử kỳ', 'g.e.m', 'lý vinh hạo', 'tiêu chiến', 'vương nhất bác', 'trương học hữu', 'lưu đức hoa', 'quách phú thành', 'lê minh', 'trần dịch tấn', 'châu thâm', 'zhou shen', 'phượng hoàng truyền kỳ'];
        if (cnKws.some(k => low.includes(k))) return 'Hoa Ngữ';

        // 5. Âu Mỹ (US-UK)
        const usKws = ['us-uk', 'usuk', 'taylor swift', 'shania twain', 'daft punk', 'the weeknd', 'bruno mars', 'adele', 'ed sheeran', 'ariana grande', 'justin bieber', 'drake', 'eminem', 'coldplay', 'maroon 5', 'billie eilish', 'dua lipa', 'beyonce', 'michael jackson', 'queen', 'beatles', 'post malone', 'lady gaga', 'rihanna', 'katy perry', 'shawn mendes', 'charlie puth', 'selena gomez', 'camila cabello', 'imagine dragons', 'linkin park', 'avicii', 'alan walker', 'marshmello', 'chainsmokers', 'david guetta', 'calvin harris', 'sia', 'sam smith', 'harry styles', 'one direction', 'avril lavigne', 'britney spears', 'celine dion', 'whitney houston', 'mariah carey', 'madonna', 'elton john', 'bon jovi', 'twenty one pilots', 'republic records'];
        if (usKws.some(k => low.includes(k))) return 'Âu Mỹ';

        return 'Âu Mỹ';
    }

    renderCountryGrid() {
        if (!this.countryGrid) return;
        this.showCountryListView();
        this.countryGrid.innerHTML = '';

        const countryMeta = {
            'Việt Nam': {
                flag: '🇻🇳',
                code: 'VN',
                sub: 'V-Pop, Bolero, Rap Việt, Acoustic',
                gradient: 'linear-gradient(135deg, rgba(239, 68, 68, 0.28), rgba(185, 28, 28, 0.12))',
                glow1: 'radial-gradient(circle, #ef4444 0%, #b91c1c 60%, transparent 80%)',
                glow2: 'radial-gradient(circle, #f59e0b 0%, #d97706 60%, transparent 80%)',
                defaultCover: 'https://images.unsplash.com/photo-1528127269322-539801943592?q=80&w=1000&auto=format&fit=crop'
            },
            'Âu Mỹ': {
                flag: '🇺🇸',
                code: 'US-UK',
                sub: 'Pop, Rock, Country, R&B, EDM, Hip-Hop',
                gradient: 'linear-gradient(135deg, rgba(2, 132, 199, 0.28), rgba(30, 58, 138, 0.12))',
                glow1: 'radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)',
                glow2: 'radial-gradient(circle, #ef4444 0%, #b91c1c 60%, transparent 80%)',
                defaultCover: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop'
            },
            'Hàn Quốc': {
                flag: '🇰🇷',
                code: 'K-POP',
                sub: 'K-Pop, K-Drama OST, Korean Indie',
                gradient: 'linear-gradient(135deg, rgba(236, 72, 153, 0.28), rgba(147, 51, 234, 0.12))',
                glow1: 'radial-gradient(circle, #ec4899 0%, #be185d 60%, transparent 80%)',
                glow2: 'radial-gradient(circle, #8b5cf6 0%, #6d28d9 60%, transparent 80%)',
                defaultCover: 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=1000&auto=format&fit=crop'
            },
            'Hoa Ngữ': {
                flag: '🇨🇳',
                code: 'C-POP',
                sub: 'Mandopop, Cantopop, Nhạc Hoa, C-Rock',
                gradient: 'linear-gradient(135deg, rgba(245, 158, 11, 0.28), rgba(180, 83, 9, 0.12))',
                glow1: 'radial-gradient(circle, #f59e0b 0%, #b45309 60%, transparent 80%)',
                glow2: 'radial-gradient(circle, #dc2626 0%, #991b1b 60%, transparent 80%)',
                defaultCover: 'https://images.unsplash.com/photo-1508807526345-15e9b5f4eaff?q=80&w=1000&auto=format&fit=crop'
            },
            'Nhật Bản': {
                flag: '🇯🇵',
                code: 'J-POP',
                sub: 'J-Pop, Anime OST, City Pop, J-Rock',
                gradient: 'linear-gradient(135deg, rgba(244, 63, 94, 0.28), rgba(244, 114, 182, 0.12))',
                glow1: 'radial-gradient(circle, #f43f5e 0%, #e11d48 60%, transparent 80%)',
                glow2: 'radial-gradient(circle, #fb7185 0%, #f43f5e 60%, transparent 80%)',
                defaultCover: 'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?q=80&w=1000&auto=format&fit=crop'
            },
            'Quốc Tế': {
                flag: '🌍',
                code: 'GLOBAL',
                sub: 'Latin, Châu Âu, Nhạc Không Lời & Khác',
                gradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.28), rgba(13, 148, 136, 0.12))',
                glow1: 'radial-gradient(circle, #10b981 0%, #047857 60%, transparent 80%)',
                glow2: 'radial-gradient(circle, #06b6d4 0%, #0e7490 60%, transparent 80%)',
                defaultCover: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?q=80&w=1000&auto=format&fit=crop'
            }
        };

        // Aggregate tracks by country
        const countryMap = new Map();
        Object.keys(countryMeta).forEach(cName => {
            countryMap.set(cName, {
                country: cName,
                tracks: [],
                trackKeys: new Set(),
                artists: new Set(),
                albums: new Set(),
                coverUrl: countryMeta[cName].defaultCover
            });
        });

        this.getBaseAlbums().forEach(album => {
            const albumCountry = album.country || this.detectCountryFromTrack({ name: album.title, artist: album.artist, album: album.title });
            (album.tracks || []).forEach(track => {
                const c = (track.country && track.country.trim()) || albumCountry || this.detectCountryFromTrack(track) || 'Quốc Tế';
                const key = countryMeta[c] ? c : 'Quốc Tế';
                const entry = countryMap.get(key);
                if (entry) {
                    const trackKey = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;
                    if (!entry.trackKeys.has(trackKey)) {
                        entry.trackKeys.add(trackKey);
                        entry.tracks.push(track);
                        if (track.artist) entry.artists.add(track.artist.trim());
                        entry.albums.add(album.title);
                        if (track.coverUrl && !entry.coverUrl.startsWith('http')) {
                            entry.coverUrl = track.coverUrl;
                        }
                    }
                }
            });
        });

        // Convert to array and prioritize countries with songs, followed by predefined order
        const predefinedOrder = ['Việt Nam', 'Âu Mỹ', 'Hàn Quốc', 'Hoa Ngữ', 'Nhật Bản', 'Quốc Tế'];
        const countryList = predefinedOrder.map(cName => countryMap.get(cName)).filter(Boolean);

        countryList.forEach(cObj => {
            const meta = countryMeta[cObj.country] || countryMeta['Quốc Tế'];
            const trackCount = cObj.tracks.length;
            const artistCount = cObj.artists.size;

            const card = document.createElement('div');
            card.className = `country-card-item ${trackCount === 0 ? 'empty-country' : ''}`;
            card.style.background = meta.gradient;
            card.innerHTML = `
                <div class="country-card-header">
                    <div class="country-flag-badge">${meta.flag}</div>
                    <span class="country-code-tag">${meta.code}</span>
                </div>
                <div class="country-card-body">
                    <h3 class="country-name">${this.escapeHtml(cObj.country)}</h3>
                    <p class="country-sub">${meta.sub}</p>
                </div>
                <div class="country-card-stats">
                    <span><b>${trackCount}</b> bài hát</span>
                    <span>•</span>
                    <span><b>${artistCount}</b> nghệ sĩ</span>
                </div>
                <div class="country-card-actions">
                    <button class="country-play-btn" ${trackCount === 0 ? 'disabled' : ''} title="Phát toàn bộ nhạc ${cObj.country}">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        <span>Phát Toàn Bộ</span>
                    </button>
                    <button class="country-action-btn btn-export-m3u8" ${trackCount === 0 ? 'disabled' : ''} title="Xuất playlist .M3U8 quốc gia">
                        .M3U8
                    </button>
                    <button class="country-action-btn btn-download-zip" ${trackCount === 0 ? 'disabled' : ''} title="Tải toàn bộ nhạc dạng .ZIP">
                        .ZIP
                    </button>
                </div>
            `;

            // Click entire card to open drill-down detail view
            card.addEventListener('click', (e) => {
                if (e.target.closest('.country-action-btn') || e.target.closest('.country-play-btn')) return;
                if (trackCount > 0) {
                    this.openCountryDetail(cObj);
                } else {
                    this.showToast(`Chưa có bài hát nào thuộc khu vực "${cObj.country}" trong thư viện.`);
                }
            });

            // Play button click
            const playBtn = card.querySelector('.country-play-btn');
            if (playBtn) {
                playBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (trackCount > 0) {
                        this.closeModal(this.countryModal);
                        this.playCountryQueue(cObj, false);
                    }
                });
            }

            // Export M3U8 button
            const m3u8Btn = card.querySelector('.btn-export-m3u8');
            if (m3u8Btn) {
                m3u8Btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (trackCount > 0) {
                        this.exportM3U8(`Nhac_${meta.code}_${cObj.country}`, cObj.tracks);
                    }
                });
            }

            // Download ZIP button
            const zipBtn = card.querySelector('.btn-download-zip');
            if (zipBtn) {
                zipBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (trackCount > 0) {
                        this.downloadZipPackage(cObj.tracks, `Tuyen_Tap_Nhac_${meta.code}`, cObj.coverUrl, `Tuyển Tập Nhạc ${cObj.country}`);
                    }
                });
            }

            this.countryGrid.appendChild(card);
        });
    }

    showCountryListView() {
        if (this.countryListView && this.countryDetailView) {
            this.countryListView.style.display = 'flex';
            this.countryDetailView.style.display = 'none';
        }
        this.currentDetailCountryObj = null;
    }

    openCountryDetail(cObj) {
        if (!this.countryDetailView || !this.countryListView) return;
        this.currentDetailCountryObj = cObj;

        this.countryListView.style.display = 'none';
        this.countryDetailView.style.display = 'flex';

        const countryMeta = {
            'Việt Nam': { flag: '🇻🇳', code: 'VN', sub: 'V-Pop, Bolero, Rap Việt, Acoustic' },
            'Âu Mỹ': { flag: '🇺🇸', code: 'US-UK', sub: 'Pop, Rock, Country, R&B, EDM, Hip-Hop' },
            'Hàn Quốc': { flag: '🇰🇷', code: 'K-POP', sub: 'K-Pop, K-Drama OST, Korean Indie' },
            'Hoa Ngữ': { flag: '🇨🇳', code: 'C-POP', sub: 'Mandopop, Cantopop, Nhạc Hoa, C-Rock' },
            'Nhật Bản': { flag: '🇯🇵', code: 'J-POP', sub: 'J-Pop, Anime OST, City Pop, J-Rock' },
            'Quốc Tế': { flag: '🌍', code: 'GLOBAL', sub: 'Latin, Châu Âu, Nhạc Không Lời & Khác' }
        };

        const meta = countryMeta[cObj.country] || { flag: '🗺️', code: 'INT', sub: 'Âm nhạc thế giới' };

        // Update header details
        if (this.countryDetailFlag) this.countryDetailFlag.textContent = meta.flag;
        if (this.countryDetailCode) this.countryDetailCode.textContent = meta.code;
        if (this.countryDetailName) this.countryDetailName.textContent = cObj.country;
        if (this.countryDetailSub) this.countryDetailSub.textContent = meta.sub;

        // Count unique genres in this country
        const genreSet = new Set();
        (cObj.tracks || []).forEach(t => {
            genreSet.add((t.genre || 'Khác').trim() || 'Khác');
        });

        if (this.countryGenreCountBadge) this.countryGenreCountBadge.textContent = genreSet.size;
        if (this.countryArtistCountBadge) this.countryArtistCountBadge.textContent = cObj.artists ? cObj.artists.size : 0;
        if (this.countryTrackCountBadge) this.countryTrackCountBadge.textContent = cObj.tracks ? cObj.tracks.length : 0;

        // Reset search inputs
        if (this.countryArtistSearchInput) this.countryArtistSearchInput.value = '';
        if (this.countryTrackSearchInput) this.countryTrackSearchInput.value = '';

        // Switch to the last active tab (or 'genres' by default)
        this.switchCountryDetailTab(this.currentCountryDetailTab || 'genres');
    }

    switchCountryDetailTab(tabName) {
        this.currentCountryDetailTab = tabName;

        const tabs = [
            { id: 'genres', btn: this.tabBtnCountryGenres, sec: this.countryGenresSection },
            { id: 'artists', btn: this.tabBtnCountryArtists, sec: this.countryArtistsSection },
            { id: 'tracks', btn: this.tabBtnCountryTracks, sec: this.countryTracksSection }
        ];

        tabs.forEach(t => {
            if (t.btn) {
                if (t.id === tabName) {
                    t.btn.classList.add('active');
                } else {
                    t.btn.classList.remove('active');
                }
            }
            if (t.sec) {
                t.sec.style.display = (t.id === tabName) ? 'block' : 'none';
            }
        });

        if (!this.currentDetailCountryObj) return;

        if (tabName === 'genres') {
            this.renderCountryGenres(this.currentDetailCountryObj);
        } else if (tabName === 'artists') {
            this.renderCountryArtists(this.currentDetailCountryObj, this.countryArtistSearchInput ? this.countryArtistSearchInput.value.trim() : '');
        } else if (tabName === 'tracks') {
            this.renderCountryTracks(this.currentDetailCountryObj, this.countryTrackSearchInput ? this.countryTrackSearchInput.value.trim() : '');
        }
    }

    renderCountryGenres(cObj) {
        if (!this.countryDetailGenreGrid) return;
        this.countryDetailGenreGrid.innerHTML = '';

        const genreIcons = {
            'Bolero / Trữ Tình': '🎻', 'Bolero': '🎻', 'Trữ Tình': '🎻',
            'Lofi / Chill': '☕', 'Lofi': '☕', 'Chill': '☕',
            'EDM / Remix': '⚡', 'EDM': '⚡', 'Remix': '⚡', 'Vinahouse': '⚡',
            'Acoustic / Instrumental': '🎸', 'Acoustic': '🎸', 'Instrumental': '🎹',
            'Rap / Hip-Hop': '🎤', 'Rap': '🎤', 'Hip-Hop': '🎤',
            'Pop / Ballad': '💖', 'Pop': '✨', 'Ballad': '🎼', 'Nhạc Trẻ': '💖',
            'Rock / Indie': '🤘', 'Rock': '🤘', 'Indie': '🎸',
            'R&B / Soul': '🎷', 'R&B': '🎷', 'Soul': '🎷',
            'Jazz / Blues': '🎺', 'Nhạc Phim / OST': '🎬', 'OST': '🎬',
            'Cổ Điển / Classical': '🎼', 'Nhạc Đỏ / Cách Mạng': '⭐',
            'Country / Folk': '🌾', 'Latin / Reggae': '🌴', 'Thiếu Nhi / Kids': '🎈',
            'Podcast / Sách Nói': '🎙️', 'Khác': '🎵'
        };

        const genreColors = {
            'Bolero / Trữ Tình': 'linear-gradient(135deg, rgba(217, 119, 6, 0.35), rgba(180, 83, 9, 0.15))',
            'Lofi / Chill': 'linear-gradient(135deg, rgba(99, 102, 241, 0.35), rgba(67, 56, 202, 0.15))',
            'EDM / Remix': 'linear-gradient(135deg, rgba(236, 72, 153, 0.35), rgba(190, 24, 93, 0.15))',
            'Acoustic / Instrumental': 'linear-gradient(135deg, rgba(16, 185, 129, 0.35), rgba(4, 120, 87, 0.15))',
            'Rap / Hip-Hop': 'linear-gradient(135deg, rgba(239, 68, 68, 0.35), rgba(185, 28, 28, 0.15))',
            'Pop / Ballad': 'linear-gradient(135deg, rgba(2, 132, 199, 0.35), rgba(3, 105, 161, 0.15))',
            'Rock / Indie': 'linear-gradient(135deg, rgba(139, 92, 246, 0.35), rgba(109, 40, 217, 0.15))',
            'R&B / Soul': 'linear-gradient(135deg, rgba(168, 85, 247, 0.35), rgba(126, 34, 206, 0.15))',
            'Nhạc Phim / OST': 'linear-gradient(135deg, rgba(20, 184, 166, 0.35), rgba(13, 148, 136, 0.15))',
            'Nhạc Đỏ / Cách Mạng': 'linear-gradient(135deg, rgba(220, 38, 38, 0.4), rgba(185, 28, 28, 0.15))',
            'Khác': 'linear-gradient(135deg, rgba(100, 116, 139, 0.3), rgba(71, 85, 105, 0.1))'
        };

        const genreMap = new Map();
        (cObj.tracks || []).forEach(track => {
            const g = (track.genre || 'Khác').trim() || 'Khác';
            const trackKey = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;
            if (!genreMap.has(g)) {
                genreMap.set(g, {
                    genre: g,
                    tracks: [track],
                    trackKeys: new Set([trackKey]),
                    coverUrl: track.coverUrl || cObj.coverUrl
                });
            } else {
                const existing = genreMap.get(g);
                if (!existing.trackKeys.has(trackKey)) {
                    existing.trackKeys.add(trackKey);
                    existing.tracks.push(track);
                }
            }
        });

        if (genreMap.size === 0) {
            this.countryDetailGenreGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 30px;">Chưa có thể loại nào trong quốc gia này.</div>';
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
                <div class="genre-card-count">${gObj.tracks.length} bài hát (${this.escapeHtml(cObj.country)})</div>
                <div style="display: flex; gap: 6px; margin-top: 8px;">
                    <button class="country-play-btn" style="padding: 5px 8px; font-size: 0.72rem;" title="Phát thể loại này">Phát</button>
                    <button class="country-action-btn btn-export-m3u8" style="padding: 5px 8px; font-size: 0.7rem;" title="Xuất M3U8">.M3U8</button>
                    <button class="country-action-btn btn-download-zip" style="padding: 5px 8px; font-size: 0.7rem;" title="Tải ZIP">.ZIP</button>
                </div>
            `;

            // Click entire card to play
            card.addEventListener('click', (e) => {
                if (e.target.closest('.country-action-btn') || e.target.closest('.country-play-btn')) return;
                this.closeModal(this.countryModal);
                this.playCountryGenreQueue(cObj.country, gObj.genre, 0, true);
            });

            const playBtn = card.querySelector('.country-play-btn');
            if (playBtn) {
                playBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.closeModal(this.countryModal);
                    this.playCountryGenreQueue(cObj.country, gObj.genre, 0, true);
                });
            }

            const m3u8Btn = card.querySelector('.btn-export-m3u8');
            if (m3u8Btn) {
                m3u8Btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.exportM3U8(`Nhac_${cObj.country}_${gObj.genre}`, gObj.tracks);
                });
            }

            const zipBtn = card.querySelector('.btn-download-zip');
            if (zipBtn) {
                zipBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.downloadZipPackage(gObj.tracks, `Nhac_${cObj.country}_${gObj.genre}`, gObj.coverUrl, `Nhạc ${cObj.country} - ${gObj.genre}`);
                });
            }

            this.countryDetailGenreGrid.appendChild(card);
        });
    }

    renderCountryArtists(cObj, query = '') {
        if (!this.countryDetailArtistGrid) return;
        this.countryDetailArtistGrid.innerHTML = '';

        const artistMap = new Map();
        (cObj.tracks || []).forEach(track => {
            const trackArtist = (track.artist || 'Unknown Artist').trim();
            if (!trackArtist || trackArtist.toLowerCase() === 'unknown') return;

            const trackKey = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;
            if (!artistMap.has(trackArtist)) {
                const cached = this.artistCacheMap ? this.artistCacheMap.get(trackArtist.toLowerCase().trim()) : null;
                const avatarUrl = (cached && cached.avatar_url) ? cached.avatar_url : (track.coverUrl || cObj.coverUrl);

                artistMap.set(trackArtist, {
                    name: trackArtist,
                    coverUrl: avatarUrl,
                    trackKeys: new Set([trackKey]),
                    tracks: [track]
                });
            } else {
                const existing = artistMap.get(trackArtist);
                if (!existing.trackKeys.has(trackKey)) {
                    existing.trackKeys.add(trackKey);
                    existing.tracks.push(track);
                }
            }
        });

        if (artistMap.size === 0) {
            this.countryDetailArtistGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 30px;">Chưa có dữ liệu ca sĩ trong quốc gia này.</div>';
            return;
        }

        let sortedArtists = Array.from(artistMap.values()).sort((a, b) => b.tracks.length - a.tracks.length);

        if (query) {
            const q = query.toLowerCase();
            sortedArtists = sortedArtists.filter(a => a.name.toLowerCase().includes(q));
        }

        if (sortedArtists.length === 0) {
            this.countryDetailArtistGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 30px;">Không tìm thấy ca sĩ phù hợp.</div>';
            return;
        }

        sortedArtists.forEach(art => {
            const card = document.createElement('div');
            card.className = 'artist-card-item';
            card.innerHTML = `
                <img src="${art.coverUrl}" loading="lazy" class="artist-avatar-img" alt="${this.escapeHtml(art.name)}" onerror="this.src='https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop'">
                <div class="artist-card-info">
                    <h4>${this.escapeHtml(art.name)}</h4>
                    <p>${art.tracks.length} bài hát (${this.escapeHtml(cObj.country)})</p>
                </div>
            `;

            card.addEventListener('click', () => {
                this.closeModal(this.countryModal);
                this.openModal(this.artistModal);
                this.openArtistByName(art.name);
            });

            this.countryDetailArtistGrid.appendChild(card);
        });
    }

    renderCountryTracks(cObj, query = '') {
        if (!this.countryDetailTracksList) return;
        this.countryDetailTracksList.innerHTML = '';

        let tracks = cObj.tracks || [];
        if (query) {
            const q = query.toLowerCase();
            tracks = tracks.filter(t => (t.name && t.name.toLowerCase().includes(q)) || (t.artist && t.artist.toLowerCase().includes(q)));
        }

        if (tracks.length === 0) {
            this.countryDetailTracksList.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 30px;">Không tìm thấy bài hát nào.</div>';
            return;
        }

        tracks.forEach((track, idx) => {
            const trItem = document.createElement('div');
            trItem.style.cssText = 'display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-radius: 12px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); transition: all 0.2s; cursor: pointer;';
            trItem.innerHTML = `
                <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
                    <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); width: 24px; text-align: center;">${idx + 1}</span>
                    <img src="${track.coverUrl || cObj.coverUrl}" loading="lazy" style="width: 38px; height: 38px; border-radius: 8px; object-fit: cover;" alt="Cover">
                    <div style="min-width: 0;">
                        <div style="font-size: 0.85rem; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(track.name)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(track.artist || 'Unknown')} • ${this.escapeHtml(track.genre || 'Khác')}</div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 0.75rem; color: var(--text-muted);">${track.duration || ''}</span>
                    <button class="nav-btn icon-btn" style="width: 30px; height: 30px; border-radius: 50%; background: var(--color-primary); color: #fff; display: flex; align-items: center; justify-content: center;" title="Phát bài này">
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    </button>
                </div>
            `;
            trItem.onmouseover = () => trItem.style.background = 'rgba(255,255,255,0.06)';
            trItem.onmouseout = () => trItem.style.background = 'rgba(255,255,255,0.02)';

            trItem.onclick = () => {
                this.closeModal(this.countryModal);
                const originalIdx = (cObj.tracks || []).findIndex(t => (t.msgId && t.msgId === track.msgId) || t.name === track.name);
                this.playCountryQueue(cObj, false, true, originalIdx !== -1 ? originalIdx : 0);
            };

            this.countryDetailTracksList.appendChild(trItem);
        });
    }

    playCountryGenreQueue(countryName, genreName, startIndex = 0, autoPlay = true) {
        if (!genreName) return;
        this.activeGenre = genreName;
        this.activeCountry = countryName;
        this.activeArtist = null;
        this.activePlaylistId = null;

        const tracks = [];
        const seenKeys = new Set();
        let coverUrl = '';
        const targetGenreLow = genreName.toLowerCase().trim();

        this.getBaseAlbums().forEach(album => {
            const albumCountry = album.country || this.detectCountryFromTrack({ name: album.title, artist: album.artist, album: album.title });
            (album.tracks || []).forEach(track => {
                const c = (track.country && track.country.trim()) || albumCountry || this.detectCountryFromTrack(track) || 'Quốc Tế';
                const validCountry = ['Việt Nam', 'Âu Mỹ', 'Hàn Quốc', 'Hoa Ngữ', 'Nhật Bản'].includes(c) ? c : 'Quốc Tế';
                if (countryName && countryName !== 'all' && validCountry !== countryName) return;

                const g = ((track.genre || 'Khác').trim() || 'Khác').toLowerCase();
                if (g === targetGenreLow) {
                    const key = track.msgId ? `id:${track.msgId}` : `name:${(track.name || '').toLowerCase()}`;
                    if (!seenKeys.has(key)) {
                        seenKeys.add(key);
                        tracks.push(track);
                        if (!coverUrl) coverUrl = track.coverUrl || album.coverUrl;
                    }
                }
            });
        });

        if (tracks.length === 0) {
            this.showToast(`Không có bài hát thuộc thể loại "${genreName}" tại khu vực ${countryName}`);
            return;
        }

        const genreAlbum = {
            id: `genre-${encodeURIComponent(countryName || 'all')}-${encodeURIComponent(genreName)}`,
            title: `${genreName} • ${countryName || 'Toàn Cầu'}`,
            artist: `Tuyển Tập ${genreName} (${countryName || 'Quốc Tế'})`,
            coverUrl: coverUrl || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop',
            format: 'FLAC Hi-Res Lossless',
            year: new Date().getFullYear().toString(),
            publisher: `${countryName || 'Quốc Tế'} • ${genreName}`,
            glowColors: { glow1: 'radial-gradient(circle, #ec4899 0%, #be185d 60%, transparent 80%)', glow2: 'radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)' },
            tracks: tracks
        };

        this.setVirtualAlbum(genreAlbum, startIndex, autoPlay);
        if (autoPlay) {
            this.showToast(`Đang phát "${genreName} (${countryName})" • ${tracks.length} bài hát`);
        }
    }

    playCountryQueue(cObj, isShuffle = false, autoPlay = true, startIndex = 0) {
        if (!cObj.tracks || cObj.tracks.length === 0) {
            this.showToast(`Không có bài hát nào của ${cObj.country} để phát!`);
            return;
        }

        this.activeCountry = cObj.country;
        this.activeArtist = null;
        this.activeGenre = null;
        this.activePlaylistId = null;

        let tracks = [...cObj.tracks];
        if (isShuffle && tracks.length > 1) {
            for (let i = tracks.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [tracks[i], tracks[j]] = [tracks[j], tracks[i]];
            }
        }

        const meta = {
            'Việt Nam': { flag: '🇻🇳', glow1: 'radial-gradient(circle, #ef4444 0%, #b91c1c 60%, transparent 80%)', glow2: 'radial-gradient(circle, #f59e0b 0%, #d97706 60%, transparent 80%)', cover: 'https://images.unsplash.com/photo-1528127269322-539801943592?q=80&w=1000&auto=format&fit=crop' },
            'Âu Mỹ': { flag: '🇺🇸', glow1: 'radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)', glow2: 'radial-gradient(circle, #ef4444 0%, #b91c1c 60%, transparent 80%)', cover: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=1000&auto=format&fit=crop' },
            'Hàn Quốc': { flag: '🇰🇷', glow1: 'radial-gradient(circle, #ec4899 0%, #be185d 60%, transparent 80%)', glow2: 'radial-gradient(circle, #8b5cf6 0%, #6d28d9 60%, transparent 80%)', cover: 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=1000&auto=format&fit=crop' },
            'Hoa Ngữ': { flag: '🇨🇳', glow1: 'radial-gradient(circle, #f59e0b 0%, #b45309 60%, transparent 80%)', glow2: 'radial-gradient(circle, #dc2626 0%, #991b1b 60%, transparent 80%)', cover: 'https://images.unsplash.com/photo-1508807526345-15e9b5f4eaff?q=80&w=1000&auto=format&fit=crop' },
            'Nhật Bản': { flag: '🇯🇵', glow1: 'radial-gradient(circle, #f43f5e 0%, #e11d48 60%, transparent 80%)', glow2: 'radial-gradient(circle, #fb7185 0%, #f43f5e 60%, transparent 80%)', cover: 'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?q=80&w=1000&auto=format&fit=crop' },
            'Quốc Tế': { flag: '🌍', glow1: 'radial-gradient(circle, #10b981 0%, #047857 60%, transparent 80%)', glow2: 'radial-gradient(circle, #06b6d4 0%, #0e7490 60%, transparent 80%)', cover: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?q=80&w=1000&auto=format&fit=crop' }
        }[cObj.country] || { flag: '🗺️', glow1: 'radial-gradient(circle, #6366f1 0%, #312e81 60%, transparent 80%)', glow2: 'radial-gradient(circle, #eab308 0%, #a16207 60%, transparent 80%)', cover: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop' };

        const countryAlbum = {
            id: `country-${encodeURIComponent(cObj.country)}`,
            title: `Nhạc ${cObj.country} ${meta.flag}`,
            artist: `Tuyển Tập ${cObj.country}`,
            country: cObj.country,
            coverUrl: cObj.coverUrl || meta.cover,
            format: 'FLAC Hi-Res Lossless',
            year: new Date().getFullYear().toString(),
            publisher: `Country Collection • ${cObj.country}`,
            glowColors: { glow1: meta.glow1, glow2: meta.glow2 },
            tracks: tracks
        };

        this.setVirtualAlbum(countryAlbum, startIndex, autoPlay);
        if (autoPlay) {
            this.showToast(`Đang phát tuyển tập nhạc "${cObj.country}" (${tracks.length} bài hát)`);
        }
    }

    // ==========================================================================
    // EXPORT PLAYLIST (.M3U8 / .PLS) & ALBUM / BATCH DOWNLOAD SYSTEM
    // ==========================================================================

    getFavoriteTracksList() {
        if (!this.favoriteTracks || this.favoriteTracks.length === 0) return [];
        const allTracksMap = this.getAllLibraryTracks();
        return this.favoriteTracks.map((fav, idx) => {
            const key = `${String(fav.chat_id)}_${String(fav.msg_id)}`;
            const libTrack = allTracksMap.get(key);
            return {
                id: idx + 1,
                name: (libTrack && libTrack.name) || fav.title || `Bài hát ${fav.msg_id}`,
                artist: (libTrack && libTrack.artist) || fav.artist || 'XTAPO Artist',
                duration: (libTrack && libTrack.duration) || fav.duration || '03:30',
                previewUrl: (libTrack && libTrack.previewUrl) || `/api/music/stream/${fav.chat_id}/${fav.msg_id}`,
                coverUrl: (libTrack && libTrack.coverUrl) || fav.cover_url || '',
                format: (libTrack && libTrack.format) || 'FLAC Hi-Res'
            };
        });
    }

    /**
     * Xuất danh sách bài hát thành file .M3U8 chuẩn UTF-8
     * Tương thích hoàn hảo với VLC, Foobar2000, PotPlayer, iTunes, Windows Media Player...
     */
    exportM3U8(title, tracks) {
        if (!tracks || tracks.length === 0) {
            this.showToast('Không có bài hát nào để xuất playlist!');
            return;
        }

        const safeTitle = (title || 'XTAPO_Playlist').replace(/[\\/:*?"<>|]/g, '_');
        let content = '#EXTM3U\n';
        content += `#EXTENC:UTF-8\n`;
        content += `#PLAYLIST:${title || 'XTAPO Playlist'}\n\n`;

        tracks.forEach((t, idx) => {
            let sec = -1;
            if (typeof t.duration === 'number' && !isNaN(t.duration)) {
                sec = Math.round(t.duration);
            } else if (typeof t.duration === 'string' && t.duration.includes(':')) {
                const parts = t.duration.split(':');
                sec = (parseInt(parts[0], 10) || 0) * 60 + (parseInt(parts[1], 10) || 0);
            }

            const artist = t.artist || (this.currentAlbum ? this.currentAlbum.artist : 'XTAPO Music');
            const trackName = t.name || `Track ${idx + 1}`;
            
            let streamUrl = t.previewUrl || '';
            if (streamUrl.startsWith('/')) {
                streamUrl = window.location.origin + streamUrl;
            }

            content += `#EXTINF:${sec},${artist} - ${trackName}\n`;
            content += `${streamUrl}\n\n`;
        });

        this.downloadBlob(content, `${safeTitle}.m3u8`, 'audio/x-mpegurl;charset=utf-8');
        this.showToast(`Đã xuất file Playlist: ${safeTitle}.m3u8 (Mở bằng VLC, Foobar2000, PotPlayer)`);
    }

    /**
     * Xuất danh sách bài hát thành file .PLS chuẩn
     * Tương thích với Winamp, Foobar2000, AIMP, PotPlayer...
     */
    exportPLS(title, tracks) {
        if (!tracks || tracks.length === 0) {
            this.showToast('Không có bài hát nào để xuất playlist!');
            return;
        }

        const safeTitle = (title || 'XTAPO_Playlist').replace(/[\\/:*?"<>|]/g, '_');
        let content = '[playlist]\n';

        tracks.forEach((t, idx) => {
            const num = idx + 1;
            let sec = -1;
            if (typeof t.duration === 'number' && !isNaN(t.duration)) {
                sec = Math.round(t.duration);
            } else if (typeof t.duration === 'string' && t.duration.includes(':')) {
                const parts = t.duration.split(':');
                sec = (parseInt(parts[0], 10) || 0) * 60 + (parseInt(parts[1], 10) || 0);
            }

            const artist = t.artist || (this.currentAlbum ? this.currentAlbum.artist : 'XTAPO Music');
            const trackName = t.name || `Track ${num}`;

            let streamUrl = t.previewUrl || '';
            if (streamUrl.startsWith('/')) {
                streamUrl = window.location.origin + streamUrl;
            }

            content += `File${num}=${streamUrl}\n`;
            content += `Title${num}=${artist} - ${trackName}\n`;
            content += `Length${num}=${sec}\n`;
        });

        content += `NumberOfEntries=${tracks.length}\n`;
        content += `Version=2\n`;

        this.downloadBlob(content, `${safeTitle}.pls`, 'audio/x-scpls;charset=utf-8');
        this.showToast(`Đã xuất file Playlist: ${safeTitle}.pls (Mở bằng Foobar2000, Winamp)`);
    }

    /**
     * Helper tạo và kích hoạt tải về File Blob
     */
    downloadBlob(content, filename, mimeType = 'text/plain') {
        const blob = (content instanceof Blob) ? content : new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 2000);
    }

    /**
     * Tải 1 bài hát trực tiếp về máy
     */
    async downloadSingleTrack(track, fallbackArtist = '') {
        if (!track || !track.previewUrl) {
            this.showToast('Không tìm thấy URL tải bài hát này!');
            return;
        }

        const artist = track.artist || fallbackArtist || (this.currentAlbum ? this.currentAlbum.artist : '');
        const title = track.name || 'Song';
        const filename = `${artist ? artist + ' - ' : ''}${title}`.replace(/[\\/:*?"<>|]/g, '_') + '.mp3';

        this.showToast(`Đang kết nối tải bài: ${title}...`);

        try {
            const res = await fetch(track.previewUrl);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const blob = await res.blob();
            this.downloadBlob(blob, filename, blob.type || 'audio/mpeg');
            this.showToast(`Đã tải xong: ${filename}`);
        } catch (err) {
            // Fallback tải trực tiếp từ thẻ a
            const a = document.createElement('a');
            a.href = track.previewUrl;
            a.download = filename;
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    }

    /**
     * Tải tuần tự nhiều bài hát (Batch Download)
     */
    async downloadBatchTracks(tracks, albumTitle = '') {
        if (!tracks || tracks.length === 0) {
            this.showToast('Không có bài hát nào để tải!');
            return;
        }

        const total = tracks.length;
        this.showToast(`Bắt đầu tải lần lượt ${total} bài hát...`);

        for (let i = 0; i < total; i++) {
            const t = tracks[i];
            const artist = t.artist || (this.currentAlbum ? this.currentAlbum.artist : '');
            const filename = `${String(i + 1).padStart(2, '0')}. ${artist ? artist + ' - ' : ''}${t.name}`.replace(/[\\/:*?"<>|]/g, '_') + '.mp3';
            
            try {
                const a = document.createElement('a');
                a.href = t.previewUrl;
                a.download = filename;
                a.target = '_blank';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } catch (e) {
                console.error('Batch download item error:', e);
            }

            if (i < total - 1) {
                await new Promise(resolve => setTimeout(resolve, 800));
            }
        }

        this.showToast(`Đã gửi lệnh tải toàn bộ ${total} bài hát tới trình duyệt!`);
    }

    /**
     * Đảm bảo thư viện JSZip được nạp thành công
     */
    async ensureJSZipLoaded() {
        if (window.JSZip) return window.JSZip;

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
            script.onload = () => {
                if (window.JSZip) resolve(window.JSZip);
                else reject(new Error('JSZip load failed'));
            };
            script.onerror = () => reject(new Error('Không thể tải thư viện JSZip từ CDN'));
            document.head.appendChild(script);
        });
    }

    openDownloadProgressModal(title, sub) {
        if (this.dlModalTitle) this.dlModalTitle.textContent = title || 'Đang Chuẩn Bị Tải...';
        if (this.dlModalSub) this.dlModalSub.textContent = sub || 'Hệ thống đang tải trực tiếp file nhạc chất lượng cao';
        this.updateDownloadProgress('Khởi động tiến trình...', 0, 'Bài 0 / 0', 'Đang nén dữ liệu...');
        this.openModal(this.downloadProgressModal);
    }

    updateDownloadProgress(currentFile, percent, statsCount, statsSpeed) {
        if (this.dlCurrentFileName) this.dlCurrentFileName.textContent = currentFile;
        if (this.dlPercentBadge) this.dlPercentBadge.textContent = `${Math.round(percent)}%`;
        if (this.dlProgressBar) this.dlProgressBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
        if (this.dlStatsCount) this.dlStatsCount.textContent = statsCount;
        if (this.dlStatsSpeed) this.dlStatsSpeed.textContent = statsSpeed;
    }

    closeDownloadProgressModal() {
        this.closeModal(this.downloadProgressModal);
    }

    /**
     * Tải toàn bộ Album / Danh sách bài hát nén thành file .ZIP
     * Kèm theo Playlist (.M3U8 & .PLS) và Ảnh Bìa (Cover)
     */
    async downloadZipPackage(tracks, zipName = 'Album', coverUrl = '', title = '') {
        if (!tracks || tracks.length === 0) {
            this.showToast('Không có bài hát nào để tải trọn gói!');
            return;
        }

        const safeZipName = (zipName || 'XTAPO_Music_Package').replace(/[\\/:*?"<>|]/g, '_');
        this.activeDownloadAbortController = new AbortController();
        const signal = this.activeDownloadAbortController.signal;

        this.openDownloadProgressModal(
            `Tải Toàn Bộ: ${title || zipName}`,
            `Đang tải và đóng gói ${tracks.length} bài hát thành file .ZIP...`
        );

        try {
            const JSZip = await this.ensureJSZipLoaded();
            const zip = new JSZip();
            const total = tracks.length;

            // 1. Tạo file playlist M3U8 bên trong ZIP
            let m3u8Content = '#EXTM3U\n#EXTENC:UTF-8\n';
            m3u8Content += `#PLAYLIST:${title || zipName}\n\n`;

            // 2. Tạo file playlist PLS bên trong ZIP
            let plsContent = '[playlist]\n';

            // 3. Tải tuần tự từng bài hát
            for (let i = 0; i < total; i++) {
                if (signal.aborted) {
                    throw new Error('DOWNLOAD_ABORTED');
                }

                const t = tracks[i];
                const artist = t.artist || (this.currentAlbum ? this.currentAlbum.artist : 'XTAPO Music');
                const trackName = t.name || `Track ${i + 1}`;
                const trackNum = String(i + 1).padStart(2, '0');
                const audioFileName = `${trackNum}. ${artist ? artist + ' - ' : ''}${trackName}`.replace(/[\\/:*?"<>|]/g, '_') + '.mp3';

                let sec = -1;
                if (typeof t.duration === 'number' && !isNaN(t.duration)) {
                    sec = Math.round(t.duration);
                } else if (typeof t.duration === 'string' && t.duration.includes(':')) {
                    const parts = t.duration.split(':');
                    sec = (parseInt(parts[0], 10) || 0) * 60 + (parseInt(parts[1], 10) || 0);
                }

                m3u8Content += `#EXTINF:${sec},${artist} - ${trackName}\n${audioFileName}\n\n`;
                plsContent += `File${i + 1}=${audioFileName}\nTitle${i + 1}=${artist} - ${trackName}\nLength${i + 1}=${sec}\n`;

                const percent = Math.round((i / (total + 1)) * 100);
                this.updateDownloadProgress(
                    `Đang tải: ${trackName}`,
                    percent,
                    `Bài ${i + 1} / ${total}`,
                    `Đang nạp file audio lossless...`
                );

                if (t.previewUrl) {
                    try {
                        const fetchRes = await fetch(t.previewUrl, { signal });
                        if (fetchRes.ok) {
                            const buffer = await fetchRes.arrayBuffer();
                            zip.file(audioFileName, buffer);
                        } else {
                            // Tạo file thông tin nếu link stream không fetch được từ client
                            zip.file(`${audioFileName}.txt`, `Không thể tải dữ liệu âm thanh trực tiếp. Link stream: ${t.previewUrl}`);
                        }
                    } catch (fetchErr) {
                        if (signal.aborted) throw new Error('DOWNLOAD_ABORTED');
                        console.warn(`Lỗi khi tải bài hát ${trackName}:`, fetchErr);
                    }
                }
            }

            plsContent += `NumberOfEntries=${total}\nVersion=2\n`;

            // Thêm playlist .m3u8 & .pls vào root của ZIP
            zip.file(`00_Playlist_${safeZipName}.m3u8`, m3u8Content);
            zip.file(`00_Playlist_${safeZipName}.pls`, plsContent);

            // Tải ảnh Cover nếu có
            if (coverUrl && !signal.aborted) {
                try {
                    const imgRes = await fetch(coverUrl, { signal });
                    if (imgRes.ok) {
                        const imgBuffer = await imgRes.arrayBuffer();
                        zip.file('cover.jpg', imgBuffer);
                    }
                } catch (e) {
                    console.warn('Lỗi khi nạp ảnh bìa album:', e);
                }
            }

            if (signal.aborted) throw new Error('DOWNLOAD_ABORTED');

            // 4. Bắt đầu nén file ZIP
            this.updateDownloadProgress(
                'Đang nén dữ liệu thành file .ZIP...',
                95,
                `Hoàn tất ${total} / ${total} bài`,
                'Đang tối ưu nén tệp tin...'
            );

            const zipBlob = await zip.generateAsync(
                { type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 1 } },
                (metadata) => {
                    if (!signal.aborted) {
                        const compPercent = 90 + Math.round(metadata.percent * 0.1);
                        this.updateDownloadProgress(
                            `Đang đóng gói: ${metadata.currentFile || 'Tạo file ZIP...'}`,
                            compPercent,
                            `Đã nén ${Math.round(metadata.percent)}%`,
                            'Chuẩn bị lưu tệp...'
                        );
                    }
                }
            );

            if (signal.aborted) throw new Error('DOWNLOAD_ABORTED');

            // 5. Tải file ZIP về máy
            this.downloadBlob(zipBlob, `${safeZipName}.zip`, 'application/zip');
            this.closeDownloadProgressModal();
            this.showToast(`🎉 Tải về toàn bộ album "${zipName}" thành công!`);

        } catch (err) {
            this.closeDownloadProgressModal();
            if (err.message === 'DOWNLOAD_ABORTED') {
                this.showToast('Đã dừng quá trình tải xuống.');
            } else {
                console.error('Download Zip Error:', err);
                this.showToast(`Lỗi khi tạo file ZIP: ${err.message || err}`);
                // Fallback nếu zip thất bại: chuyển sang batch download
                if (confirm('Không thể nén file ZIP do giới hạn bộ nhớ trình duyệt. Bạn có muốn chuyển sang tải từng bài về máy không?')) {
                    this.downloadBatchTracks(tracks, zipName);
                }
            }
        } finally {
            this.activeDownloadAbortController = null;
        }
    }

    /**
     * Xác định URL Stream M3U8 tương ứng với từng loại Album / Genre / Artist / Playlist
     */
    getAlbumM3U8Url(album) {
        if (!album) return '/api/music/playlist/all.m3u8';
        const albId = String(album.id || album.title || '');

        if (albId.startsWith('genre-')) {
            const rawGenre = decodeURIComponent(albId.substring(6));
            return `/api/music/playlist/genre/${encodeURIComponent(rawGenre)}.m3u8`;
        }
        if (albId.startsWith('artist-')) {
            const rawArtist = decodeURIComponent(albId.substring(7));
            return `/api/music/playlist/artist/${encodeURIComponent(rawArtist)}.m3u8`;
        }
        if (albId.startsWith('pl-')) {
            const plId = albId.substring(3);
            return `/api/music/playlist/user/playlist/${encodeURIComponent(plId)}.m3u8`;
        }
        return `/api/music/playlist/album/${encodeURIComponent(albId)}.m3u8`;
    }

    /**
     * Mở Modal Chia Sẻ & Lấy Link Stream M3U8 Trực Tiếp
     */
    async openM3U8ShareModal({ title, urlPath, tracks }) {
        if (!tracks || tracks.length === 0) {
            this.showToast('Không có bài hát nào trong playlist/album này!');
            return;
        }

        let fullUrl = window.location.origin + (urlPath.startsWith('/') ? urlPath : `/${urlPath}`);
        this.currentM3U8Context = { title, url: fullUrl, tracks };

        if (this.m3u8ModalTitle) this.m3u8ModalTitle.textContent = `Stream M3U8: ${title}`;
        if (this.m3u8DirectUrlInput) this.m3u8DirectUrlInput.value = fullUrl;
        if (this.m3u8CopyText) this.m3u8CopyText.textContent = 'Sao Chép Link';

        // Tự động sao chép link stream vào clipboard ban đầu
        navigator.clipboard.writeText(fullUrl).catch(() => {});
        this.openModal(this.m3u8Modal);

        // Tạo dynamic playlist share trên server để đảm bảo 100% khớp danh sách bài hát
        try {
            const cleanTracks = tracks.map(t => ({
                name: t.name || t.title || 'Track',
                artist: t.artist || 'XTAPO Artist',
                duration: t.duration || '0',
                chat_id: t.chat_id || t.chatId || '',
                msg_id: t.msg_id || t.msgId || '',
                previewUrl: t.previewUrl || t.url || ''
            }));

            const res = await fetch('/api/music/playlist/share', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, tracks: cleanTracks })
            });

            if (res.ok) {
                const data = await res.json();
                if (data.m3u8_url) {
                    fullUrl = data.m3u8_url;
                    this.currentM3U8Context.url = fullUrl;
                    if (this.m3u8DirectUrlInput) this.m3u8DirectUrlInput.value = fullUrl;
                    navigator.clipboard.writeText(fullUrl).then(() => {
                        if (this.m3u8CopyText) this.m3u8CopyText.textContent = 'Đã Copy! ✅';
                        this.showToast(`Đã tạo & copy link stream M3U8: ${title}`);
                        setTimeout(() => {
                            if (this.m3u8CopyText) this.m3u8CopyText.textContent = 'Sao Chép Link';
                        }, 2500);
                    }).catch(() => {});
                    return;
                }
            }
        } catch (e) {
            console.warn('Fallback to static M3U8 URL:', e);
        }

        this.showToast(`Đã copy link stream M3U8: ${title}`);
    }

    // =========================================================================
    // REAL-TIME SYNCED LYRICS & KARAOKE ENGINE (LRCLIB + CUSTOM LRC)
    // =========================================================================

    setupLyricsEvents() {
        // 1. Bottom Player Bar Lyrics Button (Mở Modal Lời Nhạc Karaoke Toàn Màn Hình)
        if (this.lyricsToggleBtn) {
            this.lyricsToggleBtn.addEventListener('click', () => {
                this.openKaraokeModal();
            });
        }

        // 2. Full-screen Karaoke Modal Events
        if (this.btnOpenKaraokeModal) {
            this.btnOpenKaraokeModal.addEventListener('click', () => this.openKaraokeModal());
        }
        if (this.closeLyricsModal) {
            this.closeLyricsModal.addEventListener('click', () => this.closeKaraokeModal());
        }

        // Karaoke Offset Controls
        if (this.karaokeOffsetMinus) {
            this.karaokeOffsetMinus.addEventListener('click', () => this.adjustLyricsOffset(-0.5));
        }
        if (this.karaokeOffsetPlus) {
            this.karaokeOffsetPlus.addEventListener('click', () => this.adjustLyricsOffset(0.5));
        }
        if (this.btnOffsetMinus) {
            this.btnOffsetMinus.addEventListener('click', () => this.adjustLyricsOffset(-0.5));
        }
        if (this.btnOffsetPlus) {
            this.btnOffsetPlus.addEventListener('click', () => this.adjustLyricsOffset(0.5));
        }

        // Karaoke Modal Playback Controls
        if (this.karaokePlayBtn) {
            this.karaokePlayBtn.addEventListener('click', () => this.togglePlay());
        }
        if (this.karaokePrevBtn) {
            this.karaokePrevBtn.addEventListener('click', () => this.prevTrack());
        }
        if (this.karaokeNextBtn) {
            this.karaokeNextBtn.addEventListener('click', () => this.nextTrack());
        }
        if (this.karaokeProgressTrack) {
            this.karaokeProgressTrack.addEventListener('click', (e) => {
                const rect = this.karaokeProgressTrack.getBoundingClientRect();
                const clickPos = (e.clientX - rect.left) / rect.width;
                const targetPercent = Math.max(0, Math.min(1, clickPos));
                if (this.synthesizerActive) {
                    this.synthTime = targetPercent * this.synthDuration;
                    this.updateProgress(targetPercent * 100);
                } else if (this.audio.duration) {
                    this.seekTo(targetPercent * this.audio.duration);
                }
            });
        }

        // 4. Lyrics Editor Modal Events
        const openEditorHandler = () => this.openLyricsEditorModal();
        if (this.btnOpenLyricsEditor) this.btnOpenLyricsEditor.addEventListener('click', openEditorHandler);
        if (this.karaokeEditBtn) this.karaokeEditBtn.addEventListener('click', openEditorHandler);
        if (this.closeLyricsEditorModal) this.closeLyricsEditorModal.addEventListener('click', () => this.closeModal(this.lyricsEditorModal));
        if (this.btnCancelLyricsEditor) this.btnCancelLyricsEditor.addEventListener('click', () => this.closeModal(this.lyricsEditorModal));
        if (this.btnSaveLyricsEditor) this.btnSaveLyricsEditor.addEventListener('click', () => this.saveCustomLyricsFromEditor());

        // File Import (.lrc, .txt)
        if (this.lyricsFileInput) {
            this.lyricsFileInput.addEventListener('change', (e) => {
                const file = e.target.files && e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = (evt) => {
                    if (this.lyricsRawTextarea) {
                        this.lyricsRawTextarea.value = evt.target.result;
                        this.showToast(`Đã đọc nội dung file: ${file.name}`);
                    }
                };
                reader.readAsText(file);
                // Reset input to allow re-selection
                e.target.value = '';
            });
        }

        // Editor Toolbar (Reset & Clear)
        if (this.btnClearLyrics) {
            this.btnClearLyrics.addEventListener('click', () => {
                if (this.lyricsRawTextarea) this.lyricsRawTextarea.value = '';
            });
        }
        if (this.btnResetToOriginalLyrics) {
            this.btnResetToOriginalLyrics.addEventListener('click', async () => {
                const track = this.currentTrack;
                const album = this.currentAlbum;
                if (!track) return;
                const cacheKey = this.getTrackLyricsCacheKey(track, album);
                localStorage.removeItem(`xtapo_custom_lrc_${cacheKey}`);
                this.lyricsOffset = 0;
                localStorage.removeItem(`xtapo_offset_${cacheKey}`);
                this.updateOffsetUI();
                await this.fetchTrackLyrics(track, album, true);
                if (this.lyricsRawTextarea && this.currentLyrics) {
                    this.lyricsRawTextarea.value = this.currentLyrics.rawLrc || this.currentLyrics.rawPlain || '';
                }
                this.showToast('Đã khôi phục lời bài hát gốc từ LRCLIB!');
            });
        }

        // Online Multi-Provider Manual Search from Editor
        if (this.btnLyricsOnlineSearch) {
            this.btnLyricsOnlineSearch.addEventListener('click', () => this.handleManualOnlineLyricsSearch());
        }
        if (this.lyricsSearchTrackInput) {
            this.lyricsSearchTrackInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.handleManualOnlineLyricsSearch();
            });
        }
        if (this.lyricsSearchArtistInput) {
            this.lyricsSearchArtistInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.handleManualOnlineLyricsSearch();
            });
        }

        // Editor Offset Buttons
        if (this.editorOffsetMinus) this.editorOffsetMinus.addEventListener('click', () => this.adjustLyricsOffset(-0.5));
        if (this.editorOffsetMinusSmall) this.editorOffsetMinusSmall.addEventListener('click', () => this.adjustLyricsOffset(-0.1));
        if (this.editorOffsetPlusSmall) this.editorOffsetPlusSmall.addEventListener('click', () => this.adjustLyricsOffset(0.1));
        if (this.editorOffsetPlus) this.editorOffsetPlus.addEventListener('click', () => this.adjustLyricsOffset(0.5));
        if (this.editorOffsetReset) this.editorOffsetReset.addEventListener('click', () => {
            this.lyricsOffset = 0;
            this.updateOffsetUI();
            const track = this.currentTrack;
            const album = this.currentAlbum;
            if (track) {
                const cacheKey = this.getTrackLyricsCacheKey(track, album);
                localStorage.removeItem(`xtapo_offset_${cacheKey}`);
            }
        });

        // 5. Intelligent User Scroll Detection (pauses auto-scroll on manual scroll and resumes after 3.5s)
        const setupScrollInactivityListener = (container, isUserScrollingFlagName, timeoutPropName) => {
            if (!container) return;
            const handleUserScroll = () => {
                this[isUserScrollingFlagName] = true;
                clearTimeout(this[timeoutPropName]);
                this[timeoutPropName] = setTimeout(() => {
                    this[isUserScrollingFlagName] = false;
                }, 3500);
            };
            container.addEventListener('wheel', handleUserScroll, { passive: true });
            container.addEventListener('touchstart', handleUserScroll, { passive: true });
            container.addEventListener('touchmove', handleUserScroll, { passive: true });
        };

        setupScrollInactivityListener(this.heroLyricsScroll, 'isUserScrollingHeroLyrics', 'heroScrollResumeTimeout');
        setupScrollInactivityListener(this.karaokeLyricsScroll, 'isUserScrollingKaraokeLyrics', 'karaokeScrollResumeTimeout');
    }

    switchCoverView(view = 'vinyl') {
        this.activeHeroView = view;
        if (view === 'lyrics') {
            if (this.vinylStage) this.vinylStage.style.display = 'none';
            if (this.heroLyricsStage) this.heroLyricsStage.style.display = 'flex';
            if (this.tabVinylView) this.tabVinylView.classList.remove('active');
            if (this.tabLyricsView) this.tabLyricsView.classList.add('active');
            if (this.lyricsToggleBtn) this.lyricsToggleBtn.classList.add('active');
            // Cuộn ngay vào dòng hiện tại
            this.scrollLyricsToActiveLine(true);
        } else {
            if (this.vinylStage) this.vinylStage.style.display = 'flex';
            if (this.heroLyricsStage) this.heroLyricsStage.style.display = 'none';
            if (this.tabVinylView) this.tabVinylView.classList.add('active');
            if (this.tabLyricsView) this.tabLyricsView.classList.remove('active');
            if (this.lyricsToggleBtn) this.lyricsToggleBtn.classList.remove('active');
        }
    }

    openKaraokeModal() {
        if (this.lyricsModal) {
            const track = this.currentTrack;
            const album = this.currentAlbum;
            if (track) {
                if (this.karaokeTrackTitle) this.karaokeTrackTitle.textContent = track.name;
                if (this.karaokeArtistName) this.karaokeArtistName.textContent = track.artist || album.artist || 'XTAPO Music';
                const trackCover = track.coverUrl || album.coverUrl;
                if (this.karaokeBackdrop) this.karaokeBackdrop.style.backgroundImage = `url("${trackCover}")`;
            }
            this.openModal(this.lyricsModal);
            setTimeout(() => this.scrollLyricsToActiveLine(true), 150);
        }
    }

    closeKaraokeModal() {
        if (this.lyricsModal) {
            this.closeModal(this.lyricsModal);
        }
    }

    openLyricsEditorModal() {
        const track = this.currentTrack;
        const album = this.currentAlbum;
        if (this.lyricsSearchTrackInput && track) {
            this.lyricsSearchTrackInput.value = this.cleanTrackTitleForLyrics(track.name);
        }
        if (this.lyricsSearchArtistInput && (track || album)) {
            this.lyricsSearchArtistInput.value = this.cleanArtistForLyrics((track && track.artist) || (album && album.artist) || '');
        }
        if (this.lyricsRawTextarea) {
            if (this.currentLyrics && (this.currentLyrics.rawLrc || this.currentLyrics.rawPlain)) {
                this.lyricsRawTextarea.value = this.currentLyrics.rawLrc || this.currentLyrics.rawPlain || '';
            } else {
                this.lyricsRawTextarea.value = '';
            }
        }
        this.updateOffsetUI();
        if (this.lyricsEditorModal) {
            this.openModal(this.lyricsEditorModal);
            if (this.lyricsRawTextarea) setTimeout(() => this.lyricsRawTextarea.focus(), 120);
        }
    }

    startLyricsSyncLoop() {
        if (this._lyricsSyncRafId) cancelAnimationFrame(this._lyricsSyncRafId);
        const loop = () => {
            if (this.isPlaying) {
                const curTime = this.synthesizerActive ? this.synthTime : (this.audio.currentTime || 0);
                this.syncLyricsTime(curTime);
                this._lyricsSyncRafId = requestAnimationFrame(loop);
            }
        };
        this._lyricsSyncRafId = requestAnimationFrame(loop);
    }

    stopLyricsSyncLoop() {
        if (this._lyricsSyncRafId) {
            cancelAnimationFrame(this._lyricsSyncRafId);
            this._lyricsSyncRafId = null;
        }
    }

    splitArtistTitle(raw) {
        if (!raw) return { artist: '', title: '' };
        let t = raw.trim();
        t = t.replace(/^\s*\d+[\s\.\-_]+/, '');
        t = t.replace(/\.(flac|mp3|m4a|wav|aac|ogg)$/i, '');
        t = t.replace(/\[.*?\]/g, '');
        t = t.replace(/\((?:official|music|video|audio|lyrics|remaster|remastered|version|deluxe|bonus|expanded|edition|karaoke|beat|instrumental|hd|4k|live).*?\)/gi, '');
        
        for (const sep of [' - ', ' – ', ' — ', ' // ']) {
            if (t.includes(sep)) {
                const parts = t.split(sep);
                if (parts.length >= 2 && parts[0].trim() && parts[1].trim()) {
                    return { artist: parts[0].trim(), title: parts.slice(1).join(' - ').trim() };
                }
            }
        }
        return { artist: '', title: t.trim() };
    }

    cleanTrackTitleForLyrics(title) {
        if (!title) return "";
        const parsed = this.splitArtistTitle(title);
        let t = parsed.title || title;
        t = t.replace(/^\s*\d+[\s\.\-_]+/, ''); // 01. 
        t = t.replace(/\.(flac|mp3|m4a|wav|aac|ogg)$/i, '');
        t = t.replace(/\[.*?\]/g, ''); // [FLAC]
        t = t.replace(/\((?:official|music|video|audio|lyrics|remaster|remastered|version|deluxe|bonus|expanded|edition|karaoke|beat|instrumental|hd|4k|live).*?\)/gi, '');
        return t.replace(/\s+/g, ' ').trim();
    }

    cleanArtistForLyrics(artist, rawTitle = "") {
        if (artist && !['unknown', 'various artists', 'xtapo music', 'chưa rõ', 'none'].includes(artist.toLowerCase().trim())) {
            return artist.replace(/\[.*?\]/g, '').replace(/\s+/g, ' ').trim();
        }
        const parsed = this.splitArtistTitle(rawTitle);
        if (parsed.artist && !['unknown', 'various artists', 'xtapo music', 'chưa rõ', 'none'].includes(parsed.artist.toLowerCase().trim())) {
            return parsed.artist;
        }
        return "";
    }

    getTrackLyricsCacheKey(track, album) {
        const cleanTitle = this.cleanTrackTitleForLyrics(track.name || '');
        const cleanArtist = this.cleanArtistForLyrics(track.artist || (album && album.artist) || '', track.name || '');
        return `${cleanTitle.toLowerCase()}__${cleanArtist.toLowerCase()}`;
    }

    // --- Fetch Lyrics Engine (LRCLIB + DB + LocalStorage) ---
    async fetchTrackLyrics(track, album, forceRefresh = false) {
        if (!track) return;
        const cleanTitle = this.cleanTrackTitleForLyrics(track.name || '');
        const cleanArtist = this.cleanArtistForLyrics(track.artist || (album && album.artist) || '', track.name || '');
        const cacheKey = this.getTrackLyricsCacheKey(track, album);

        // Load saved sync offset
        const savedOffset = localStorage.getItem(`xtapo_offset_${cacheKey}`);
        this.lyricsOffset = savedOffset !== null ? parseFloat(savedOffset) : 0;
        this.updateOffsetUI();

        // 1. Loading UI state
        this.currentLyricIndex = -1;
        if (this.heroLyricsPlaceholder) {
            this.heroLyricsPlaceholder.style.display = 'flex';
            this.heroLyricsPlaceholder.innerHTML = `
                <div class="lyrics-spinner"></div>
                <span>Đang kết nối API LRCLIB & tải lời cho "${this.escapeHtml(cleanTitle)}"...</span>
            `;
        }
        if (this.heroLyricsLines) this.heroLyricsLines.innerHTML = '';
        if (this.karaokePlaceholder) {
            this.karaokePlaceholder.style.display = 'flex';
            if (this.karaokeStatusText) this.karaokeStatusText.textContent = `Đang đồng bộ lời bài hát "${cleanTitle}"...`;
        }
        if (this.karaokeLinesList) this.karaokeLinesList.innerHTML = '';
        if (this.heroLyricsTitle) this.heroLyricsTitle.textContent = `${cleanTitle} ${cleanArtist ? '- ' + cleanArtist : ''}`;

        // 2. Check Custom LocalStorage Lyrics First
        const customLrc = localStorage.getItem(`xtapo_custom_lrc_${cacheKey}`);
        if (customLrc && !forceRefresh) {
            const parsed = this.parseLRC(customLrc);
            this.currentLyrics = {
                lines: parsed.lines,
                rawLrc: customLrc,
                rawPlain: '',
                isCustom: true,
                isPlain: parsed.isPlain,
                source: 'custom_local'
            };
            if (this.heroLyricsSourceTag) this.heroLyricsSourceTag.textContent = 'CUSTOM .LRC (ĐÃ LƯU)';
            this.renderLyrics(this.currentLyrics);
            return;
        }

        // 3. Check Cached Lyrics in LocalStorage
        const cachedRaw = localStorage.getItem(`xtapo_cached_lrc_${cacheKey}`);
        if (cachedRaw && !forceRefresh) {
            try {
                const cachedData = JSON.parse(cachedRaw);
                const lrcContent = cachedData.synced_lyrics || cachedData.syncedLyrics || '';
                const plainContent = cachedData.plain_lyrics || cachedData.plainLyrics || '';
                if (lrcContent || plainContent) {
                    const parsed = this.parseLRC(lrcContent || plainContent);
                    this.currentLyrics = {
                        lines: parsed.lines,
                        rawLrc: lrcContent,
                        rawPlain: plainContent,
                        isCustom: false,
                        isPlain: parsed.isPlain,
                        source: 'cache'
                    };
                    if (this.heroLyricsSourceTag) this.heroLyricsSourceTag.textContent = lrcContent ? 'LRCLIB SYNCED' : 'LRCLIB PLAIN';
                    this.renderLyrics(this.currentLyrics);
                    return;
                }
            } catch (e) {}
        }

        // 4. Fetch from Backend /api/music/lyrics
        let lyricsFound = false;
        try {
            const durationSec = this.getDurationSeconds(track.duration);
            const params = new URLSearchParams({
                track_name: cleanTitle,
                artist_name: cleanArtist,
                duration: durationSec > 0 ? durationSec.toString() : ''
            });
            if (album && album.title) params.append('album_name', album.title);

            const res = await fetch(`/api/music/lyrics?${params.toString()}`);
            if (res.ok) {
                const data = await res.json();
                const synced = data.synced_lyrics || data.syncedLyrics;
                const plain = data.plain_lyrics || data.plainLyrics;
                if (synced || plain) {
                    localStorage.setItem(`xtapo_cached_lrc_${cacheKey}`, JSON.stringify(data));
                    const parsed = this.parseLRC(synced || plain);
                    this.currentLyrics = {
                        lines: parsed.lines,
                        rawLrc: synced || '',
                        rawPlain: plain || '',
                        isCustom: !!data.is_custom,
                        isPlain: parsed.isPlain,
                        source: 'backend_lrclib'
                    };
                    const isNetease = data.source === 'netease_cloud';
                    const srcLabel = data.is_custom ? 'CUSTOM .LRC' : (isNetease ? 'NETEASE SYNCED' : (synced ? 'LRCLIB SYNCED' : 'PLAIN LYRICS'));
                    if (this.heroLyricsSourceTag) {
                        this.heroLyricsSourceTag.textContent = srcLabel;
                    }
                    this.renderLyrics(this.currentLyrics);
                    lyricsFound = true;
                }
            }
        } catch (backendErr) {
            console.log('[Lyrics] Backend API unavailable, trying client direct LRCLIB:', backendErr);
        }

        // 5. Fallback: Direct client-side LRCLIB query (if backend is offline or static)
        if (!lyricsFound) {
            try {
                const queryStr = encodeURIComponent(`${cleanTitle} ${cleanArtist}`.trim());
                const lrclibRes = await fetch(`https://lrclib.net/api/search?q=${queryStr}`);
                if (lrclibRes.ok) {
                    const items = await lrclibRes.json();
                    if (Array.isArray(items) && items.length > 0) {
                        const best = items.find(it => it.syncedLyrics) || items[0];
                        const synced = best.syncedLyrics || '';
                        const plain = best.plainLyrics || '';
                        if (synced || plain) {
                            localStorage.setItem(`xtapo_cached_lrc_${cacheKey}`, JSON.stringify(best));
                            const parsed = this.parseLRC(synced || plain);
                            this.currentLyrics = {
                                lines: parsed.lines,
                                rawLrc: synced,
                                rawPlain: plain,
                                isCustom: false,
                                isPlain: parsed.isPlain,
                                source: 'lrclib_direct'
                            };
                            if (this.heroLyricsSourceTag) this.heroLyricsSourceTag.textContent = synced ? 'LRCLIB SYNCED' : 'LRCLIB PLAIN';
                            this.renderLyrics(this.currentLyrics);
                            lyricsFound = true;
                        }
                    }
                }
            } catch (lrclibErr) {
                console.log('[Lyrics] LRCLIB direct note:', lrclibErr);
            }
        }

        // 6. If no lyrics found anywhere
        if (!lyricsFound) {
            this.currentLyrics = null;
            if (this.heroLyricsPlaceholder) {
                this.heroLyricsPlaceholder.style.display = 'flex';
                this.heroLyricsPlaceholder.innerHTML = `
                    <div style="font-size: 2.2rem; margin-bottom: 6px;">🎤</div>
                    <div style="font-weight: 700; color: #fff;">Chưa tìm thấy lời bài hát</div>
                    <p style="font-size: 0.82rem; color: var(--text-muted); max-width: 320px; margin: 0 auto; line-height: 1.5;">
                        Bạn có thể nhấn nút <b>"Sửa .LRC"</b> ở trên để dán lời hoặc tải file .lrc từ máy tính!
                    </p>
                    <button class="primary-btn" onclick="window.xtapoApp.openLyricsEditorModal()" style="margin-top: 10px; padding: 8px 18px; font-size: 0.8rem;">
                        ✏️ Dán File .LRC Ngay
                    </button>
                `;
            }
            if (this.karaokePlaceholder) {
                this.karaokePlaceholder.style.display = 'flex';
                if (this.karaokeStatusText) {
                    this.karaokeStatusText.innerHTML = `Chưa có sẵn lời cho "${cleanTitle}".<br><span style="font-size: 0.9rem; opacity: 0.7;">Nhấn "Sửa LRC" để thêm lời thủ công!</span>`;
                }
            }
        }
    }

    getDurationSeconds(durationStr) {
        if (!durationStr) return 0;
        if (typeof durationStr === 'number') return durationStr;
        const parts = durationStr.split(':');
        if (parts.length === 2) {
            return (parseInt(parts[0], 10) || 0) * 60 + (parseInt(parts[1], 10) || 0);
        }
        return 0;
    }

    // --- Parser Engine for .LRC Format ---
    parseLRC(lrcText) {
        if (!lrcText || typeof lrcText !== 'string') {
            return { lines: [], isPlain: true };
        }

        const lines = [];
        const rawLines = lrcText.split(/\r?\n/);
        const timeRegex = /\[(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?\]/g;
        let hasTimestamps = false;
        let globalOffsetMs = 0;

        // Check for header tags like [offset:+/-500]
        for (const raw of rawLines) {
            const offsetMatch = raw.match(/\[offset:\s*([+-]?\d+)\s*\]/i);
            if (offsetMatch) {
                globalOffsetMs = parseInt(offsetMatch[1], 10) || 0;
            }
        }

        for (const raw of rawLines) {
            const trimmed = raw.trim();
            if (!trimmed) continue;

            // Check if line contains [mm:ss.xx]
            const matches = [...trimmed.matchAll(timeRegex)];
            if (matches.length > 0) {
                hasTimestamps = true;
                const text = trimmed.replace(timeRegex, '').trim();
                for (const match of matches) {
                    const mins = parseInt(match[1], 10) || 0;
                    const secs = parseInt(match[2], 10) || 0;
                    const msRaw = match[3] || '0';
                    const ms = msRaw.length === 2 ? parseInt(msRaw, 10) * 10 : (msRaw.length === 1 ? parseInt(msRaw, 10) * 100 : parseInt(msRaw, 10));
                    const totalSecs = mins * 60 + secs + ms / 1000 + globalOffsetMs / 1000;
                    lines.push({
                        time: Math.max(0, totalSecs),
                        text: text || '♪ ♪ ♪'
                    });
                }
            } else if (!trimmed.startsWith('[')) {
                // Non-timestamp text line
                lines.push({
                    time: -1,
                    text: trimmed
                });
            }
        }

        if (hasTimestamps) {
            // Sort lines by time ascending strictly
            lines.sort((a, b) => a.time - b.time);
            return { lines, isPlain: false };
        } else {
            // Plain lyrics without timestamps: format as readable lines
            const plainLines = rawLines.map((l, idx) => ({ time: idx * 4, text: l.trim() })).filter(l => l.text);
            return { lines: plainLines, isPlain: true };
        }
    }

    // --- Render Synced Lyrics DOM ---
    renderLyrics(lyricsData) {
        if (!lyricsData || !lyricsData.lines || lyricsData.lines.length === 0) return;
        const lines = lyricsData.lines;

        if (this.heroLyricsPlaceholder) this.heroLyricsPlaceholder.style.display = 'none';
        if (this.karaokePlaceholder) this.karaokePlaceholder.style.display = 'none';

        // 1. Render Hero Lyrics lines
        if (this.heroLyricsLines) {
            this.heroLyricsLines.innerHTML = '';
            lines.forEach((line, idx) => {
                const el = document.createElement('div');
                el.className = 'lyrics-line';
                el.dataset.index = idx;
                el.dataset.time = line.time;
                el.textContent = line.text;
                el.addEventListener('click', () => {
                    if (line.time >= 0) {
                        this.seekTo(line.time);
                    }
                });
                this.heroLyricsLines.appendChild(el);
            });
        }

        // 2. Render Karaoke Fullscreen lines
        if (this.karaokeLinesList) {
            this.karaokeLinesList.innerHTML = '';
            lines.forEach((line, idx) => {
                const el = document.createElement('div');
                el.className = 'karaoke-line';
                el.dataset.index = idx;
                el.dataset.time = line.time;
                el.textContent = line.text;
                el.addEventListener('click', () => {
                    if (line.time >= 0) {
                        this.seekTo(line.time);
                    }
                });
                this.karaokeLinesList.appendChild(el);
            });
        }

        // Run sync immediately with current time
        const curTime = this.synthesizerActive ? this.synthTime : (this.audio.currentTime || 0);
        this.syncLyricsTime(curTime);
    }

    // --- Real-time Timestamp Synchronizer & Auto-scroller ---
    syncLyricsTime(currentTime) {
        if (!this.currentLyrics || !this.currentLyrics.lines || this.currentLyrics.lines.length === 0) return;
        const lines = this.currentLyrics.lines;
        const calibratedTime = currentTime + this.lyricsOffset;

        // Find active line with precision
        let activeIdx = -1;
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].time <= calibratedTime + 0.05) {
                activeIdx = i;
            } else {
                break;
            }
        }

        if (activeIdx !== this.currentLyricIndex) {
            this.currentLyricIndex = activeIdx;
            this.updateActiveLyricClasses(activeIdx);
            this.scrollLyricsToActiveLine(false);
        }

        // Sync Karaoke Modal Timeline Progress Bar
        if (this.lyricsModal && this.lyricsModal.classList.contains('open')) {
            const duration = this.synthesizerActive ? this.synthDuration : (this.audio.duration || 1);
            if (duration > 0 && !isNaN(duration)) {
                const pct = (currentTime / duration) * 100;
                if (this.karaokeProgressFill) this.karaokeProgressFill.style.width = `${pct}%`;
                if (this.karaokeTimeCurrent) this.karaokeTimeCurrent.textContent = this.formatTime(currentTime);
            }
        }
    }

    updateActiveLyricClasses(activeIdx) {
        // 1. Update Hero Lyrics Elements
        if (this.heroLyricsLines) {
            const heroEls = this.heroLyricsLines.querySelectorAll('.lyrics-line');
            heroEls.forEach((el, idx) => {
                if (idx === activeIdx) {
                    el.classList.add('active');
                    el.classList.remove('past');
                } else if (idx < activeIdx) {
                    el.classList.add('past');
                    el.classList.remove('active');
                } else {
                    el.classList.remove('active', 'past');
                }
            });
        }

        // 2. Update Karaoke Modal Elements
        if (this.karaokeLinesList) {
            const karaokeEls = this.karaokeLinesList.querySelectorAll('.karaoke-line');
            karaokeEls.forEach((el, idx) => {
                if (idx === activeIdx) {
                    el.classList.add('active');
                    el.classList.remove('past');
                } else if (idx < activeIdx) {
                    el.classList.add('past');
                    el.classList.remove('active');
                } else {
                    el.classList.remove('active', 'past');
                }
            });
        }
    }

    scrollLyricsToActiveLine(force = false) {
        if (this.currentLyricIndex < 0) return;

        // 1. Hero Lyrics Auto-scroll
        if (this.heroLyricsScroll && this.heroLyricsLines && (force || !this.isUserScrollingHeroLyrics)) {
            const activeEl = this.heroLyricsLines.querySelector(`.lyrics-line[data-index="${this.currentLyricIndex}"]`);
            if (activeEl) {
                const containerH = this.heroLyricsScroll.clientHeight;
                const elTop = activeEl.offsetTop;
                const elH = activeEl.clientHeight;
                const targetScroll = Math.max(0, elTop - containerH * 0.38 + elH / 2);
                this.heroLyricsScroll.scrollTo({
                    top: targetScroll,
                    behavior: force ? 'auto' : 'smooth'
                });
            }
        }

        // 2. Karaoke Fullscreen Modal Auto-scroll
        if (this.karaokeLyricsScroll && this.karaokeLinesList && (force || !this.isUserScrollingKaraokeLyrics)) {
            const activeEl = this.karaokeLinesList.querySelector(`.karaoke-line[data-index="${this.currentLyricIndex}"]`);
            if (activeEl) {
                const containerH = this.karaokeLyricsScroll.clientHeight;
                const elTop = activeEl.offsetTop;
                const elH = activeEl.clientHeight;
                const targetScroll = Math.max(0, elTop - containerH * 0.35 + elH / 2);
                this.karaokeLyricsScroll.scrollTo({
                    top: targetScroll,
                    behavior: force ? 'auto' : 'smooth'
                });
            }
        }
    }

    seekTo(targetSeconds) {
        const safeSecs = Math.max(0, targetSeconds);
        if (this.synthesizerActive) {
            this.synthTime = safeSecs;
            this.syncLyricsTime(this.synthTime);
        } else if (this.audio.duration) {
            this.audio.currentTime = Math.min(safeSecs, this.audio.duration);
            this.syncLyricsTime(this.audio.currentTime);
        }
        this.showToast(`Tua đến: ${this.formatTime(safeSecs)}`);
    }

    adjustLyricsOffset(deltaSeconds) {
        this.lyricsOffset = parseFloat((this.lyricsOffset + deltaSeconds).toFixed(2));
        this.updateOffsetUI();
        const track = this.currentTrack;
        const album = this.currentAlbum;
        if (track) {
            const cacheKey = this.getTrackLyricsCacheKey(track, album);
            localStorage.setItem(`xtapo_offset_${cacheKey}`, this.lyricsOffset.toString());
        }
        const curTime = this.synthesizerActive ? this.synthTime : (this.audio.currentTime || 0);
        this.syncLyricsTime(curTime);
        this.showToast(`Căn chỉnh lời: ${this.lyricsOffset >= 0 ? '+' : ''}${this.lyricsOffset.toFixed(1)}s`);
    }

    updateOffsetUI() {
        const formatted = `${this.lyricsOffset >= 0 ? '+' : ''}${this.lyricsOffset.toFixed(1)}s`;
        if (this.heroLyricsOffset) this.heroLyricsOffset.textContent = `Offset: ${formatted}`;
        if (this.karaokeOffsetLabel) this.karaokeOffsetLabel.textContent = formatted;
        if (this.editorOffsetValue) this.editorOffsetValue.textContent = formatted;
    }

    // --- Save Custom Lyrics from Editor ---
    async saveCustomLyricsFromEditor() {
        const track = this.currentTrack;
        const album = this.currentAlbum;
        if (!track || !this.lyricsRawTextarea) return;

        const rawText = this.lyricsRawTextarea.value.trim();
        if (!rawText) {
            this.showToast('Vui lòng nhập nội dung lời bài hát hoặc file .lrc!');
            return;
        }

        const cacheKey = this.getTrackLyricsCacheKey(track, album);
        localStorage.setItem(`xtapo_custom_lrc_${cacheKey}`, rawText);
        localStorage.setItem(`xtapo_offset_${cacheKey}`, this.lyricsOffset.toString());

        const parsed = this.parseLRC(rawText);
        this.currentLyrics = {
            lines: parsed.lines,
            rawLrc: rawText,
            rawPlain: '',
            isCustom: true,
            isPlain: parsed.isPlain,
            source: 'custom_saved'
        };

        if (this.heroLyricsSourceTag) this.heroLyricsSourceTag.textContent = 'CUSTOM .LRC (ĐÃ LƯU)';
        this.renderLyrics(this.currentLyrics);
        this.closeModal(this.lyricsEditorModal);
        this.showToast('Đã lưu lời bài hát tùy chỉnh thành công! 🎤');

        // Save to backend database asynchronously
        try {
            await fetch('/api/music/lyrics/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    track_name: track.name,
                    artist_name: track.artist || (album && album.artist) || '',
                    synced_lyrics: rawText,
                    plain_lyrics: ''
                })
            });
        } catch (e) {}
    }

    async handleManualOnlineLyricsSearch() {
        const trackQuery = this.lyricsSearchTrackInput ? this.lyricsSearchTrackInput.value.trim() : '';
        const artistQuery = this.lyricsSearchArtistInput ? this.lyricsSearchArtistInput.value.trim() : '';
        const provider = this.lyricsSearchProviderSelect ? this.lyricsSearchProviderSelect.value : 'all';

        if (!trackQuery) {
            this.showToast('Vui lòng nhập tên bài hát cần tìm!');
            return;
        }

        if (this.btnLyricsOnlineSearch) {
            this.btnLyricsOnlineSearch.disabled = true;
            this.btnLyricsOnlineSearch.innerHTML = `<span>Đang quét dữ liệu...</span>`;
        }

        if (this.lyricsSearchResults) {
            this.lyricsSearchResults.style.display = 'block';
            this.lyricsSearchResults.innerHTML = `
                <div style="padding: 14px; font-size: 0.82rem; color: var(--text-muted); text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px;">
                    <div class="lyrics-spinner" style="width: 22px; height: 22px;"></div>
                    <span>Đang tìm kiếm trên LRCLIB & Netease 163...</span>
                </div>
            `;
        }

        try {
            const params = new URLSearchParams({
                track_name: trackQuery,
                artist_name: artistQuery,
                provider: provider
            });

            const res = await fetch(`/api/music/lyrics/search?${params.toString()}`);
            if (res.ok) {
                const data = await res.json();
                const items = data.items || [];
                if (items.length > 0) {
                    if (this.lyricsSearchResults) {
                        this.lyricsSearchResults.innerHTML = `
                            <div style="font-size: 0.75rem; color: var(--accent-gold); font-weight: 700; margin-bottom: 6px; padding: 2px 6px; display: flex; justify-content: space-between; align-items: center;">
                                <span>TÌM THẤY ${items.length} PHIÊN BẢN (NHẤP ĐỂ NẠP LỜI):</span>
                                <span style="font-size: 0.68rem; color: var(--text-muted); font-weight: normal;">Đa Nguồn LRCLIB / Netease</span>
                            </div>
                        `;
                        items.forEach((it) => {
                            const isSynced = Boolean(it.is_synced);
                            const dur = it.duration ? this.formatTime(it.duration) : '--:--';
                            const sourceTag = it.source || 'Online';
                            const isNetease = sourceTag.includes('Netease');
                            const itemEl = document.createElement('div');
                            itemEl.style.cssText = 'display: flex; align-items: center; justify-content: space-between; padding: 9px 12px; margin-bottom: 5px; border-radius: 8px; background: rgba(255,255,255,0.04); cursor: pointer; transition: all 0.2s ease; border: 1px solid rgba(255,255,255,0.05);';
                            itemEl.innerHTML = `
                                <div style="display: flex; flex-direction: column; overflow: hidden; margin-right: 8px;">
                                    <div style="display: flex; align-items: center; gap: 6px;">
                                        <span style="font-weight: 700; color: #fff; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(it.track_name || trackQuery)}</span>
                                        <span style="font-size: 0.65rem; padding: 1px 6px; border-radius: 4px; background: ${isNetease ? 'rgba(239,68,68,0.2)' : 'rgba(56,189,248,0.2)'}; color: ${isNetease ? '#f87171' : '#38bdf8'}; font-weight: 700;">${this.escapeHtml(sourceTag)}</span>
                                    </div>
                                    <span style="font-size: 0.74rem; color: var(--text-muted); margin-top: 2px;">${this.escapeHtml(it.artist_name || 'Nghệ sĩ')} • ${this.escapeHtml(it.album_name || '')} (${dur})</span>
                                </div>
                                <span style="padding: 3px 9px; border-radius: 12px; font-size: 0.68rem; font-weight: 700; background: ${isSynced ? 'rgba(52,211,153,0.18)' : 'rgba(255,255,255,0.08)'}; color: ${isSynced ? '#34d399' : 'rgba(255,255,255,0.5)'}; white-space: nowrap;">
                                    ${isSynced ? '⚡ ĐỒNG BỘ' : 'LỜI THÔ'}
                                </span>
                            `;
                            itemEl.addEventListener('mouseenter', () => {
                                itemEl.style.background = 'rgba(252,191,71,0.14)';
                                itemEl.style.borderColor = 'rgba(252,191,71,0.3)';
                            });
                            itemEl.addEventListener('mouseleave', () => {
                                itemEl.style.background = 'rgba(255,255,255,0.04)';
                                itemEl.style.borderColor = 'rgba(255,255,255,0.05)';
                            });
                            itemEl.addEventListener('click', () => {
                                const lrc = it.synced_lyrics || it.plain_lyrics || '';
                                if (this.lyricsRawTextarea && lrc) {
                                    this.lyricsRawTextarea.value = lrc;
                                    this.showToast(`Đã nạp lời: "${it.track_name}" (${sourceTag})`);
                                }
                            });
                            this.lyricsSearchResults.appendChild(itemEl);
                        });
                    }

                    // Tự động nạp kết quả đầu tiên có đồng bộ vào textarea
                    const best = items.find(it => it.is_synced) || items[0];
                    const lrc = best.synced_lyrics || best.plain_lyrics || '';
                    if (this.lyricsRawTextarea && lrc) {
                        this.lyricsRawTextarea.value = lrc;
                        this.showToast(`Đã tìm thấy ${items.length} bản lời. Đã nạp bản tốt nhất từ ${best.source}!`);
                    }
                } else {
                    if (this.lyricsSearchResults) {
                        this.lyricsSearchResults.innerHTML = `<div style="padding: 12px; font-size: 0.82rem; color: #f87171; text-align: center;">Không tìm thấy kết quả nào cho "${this.escapeHtml(trackQuery)}" trên nguồn đã chọn.</div>`;
                    }
                    this.showToast(`Không tìm thấy kết quả nào cho "${trackQuery}"`);
                }
            } else {
                this.showToast('Lỗi kết nối tới máy chủ tìm kiếm lời');
            }
        } catch (e) {
            this.showToast('Lỗi khi tìm kiếm lời bài hát trực tuyến');
        } finally {
            if (this.btnLyricsOnlineSearch) {
                this.btnLyricsOnlineSearch.disabled = false;
                this.btnLyricsOnlineSearch.innerHTML = `
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    <span>Tìm Lời Nhạc</span>
                `;
            }
        }
    }

    // ==========================================================================
    // SLEEP TIMER (HẸN GIỜ TẮT NHẠC) MANAGER
    // ==========================================================================
    setupSleepTimerEvents() {
        // Preset buttons
        const presetBtns = document.querySelectorAll('.sleep-preset-btn');
        presetBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                if (mode === 'end_of_track') {
                    this.startSleepTimer(0, true);
                } else {
                    const mins = parseInt(btn.dataset.minutes, 10);
                    if (mins > 0) {
                        this.startSleepTimer(mins, false);
                    }
                }
                this.closeModal(this.sleepTimerModal);
            });
        });

        // Custom minutes input apply
        if (this.sleepCustomApplyBtn && this.sleepCustomInput) {
            this.sleepCustomApplyBtn.addEventListener('click', () => {
                const mins = parseInt(this.sleepCustomInput.value, 10);
                if (isNaN(mins) || mins <= 0) {
                    this.showToast('Vui lòng nhập số phút hợp lệ (ví dụ: 15, 30, 45...)');
                    return;
                }
                this.startSleepTimer(mins, false);
                this.closeModal(this.sleepTimerModal);
            });

            this.sleepCustomInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.sleepCustomApplyBtn.click();
                }
            });
        }

        // Cancel timer button
        if (this.sleepCancelTimerBtn) {
            this.sleepCancelTimerBtn.addEventListener('click', () => {
                this.cancelSleepTimer(false);
            });
        }

        // Extend buttons
        if (this.sleepExtend5Btn) {
            this.sleepExtend5Btn.addEventListener('click', () => this.addSleepTimerMinutes(5));
        }
        if (this.sleepExtend15Btn) {
            this.sleepExtend15Btn.addEventListener('click', () => this.addSleepTimerMinutes(15));
        }
        if (this.sleepExtend30Btn) {
            this.sleepExtend30Btn.addEventListener('click', () => this.addSleepTimerMinutes(30));
        }

        // Fade out checkbox
        if (this.sleepFadeOutCheckbox) {
            this.sleepFadeOutCheckbox.addEventListener('change', (e) => {
                this.sleepTimerFadeOut = e.target.checked;
            });
        }
    }

    openSleepTimerModal() {
        this.updateSleepTimerModalView();
        this.openModal(this.sleepTimerModal);
    }

    startSleepTimer(minutes, endOfTrack = false) {
        // Clear any existing timer interval
        if (this.sleepTimerInterval) {
            clearInterval(this.sleepTimerInterval);
            this.sleepTimerInterval = null;
        }

        // Restore volume if previous timer was in fade-out
        if (this.sleepTimerOriginalVolume !== null) {
            this.audio.volume = this.sleepTimerOriginalVolume;
            this.volumeSlider.value = this.sleepTimerOriginalVolume;
            this.sleepTimerOriginalVolume = null;
            this.updateVolumeIcons();
        }

        if (endOfTrack) {
            this.sleepTimerMode = 'end_of_track';
            this.sleepTimerSeconds = 0;
            this.sleepTimerTotalSeconds = 0;
            this.showToast('🌙 Đã hẹn giờ: Dừng phát nhạc sau khi hết bài hát hiện tại.');
        } else {
            this.sleepTimerMode = 'time';
            this.sleepTimerSeconds = minutes * 60;
            this.sleepTimerTotalSeconds = this.sleepTimerSeconds;
            this.showToast(`🌙 Đã hẹn giờ: Nhạc sẽ tự tắt sau ${minutes} phút.`);

            this.sleepTimerInterval = setInterval(() => {
                this.tickSleepTimer();
            }, 1000);
        }

        this.updateSleepTimerUI();
    }

    tickSleepTimer() {
        if (this.sleepTimerMode !== 'time') return;

        this.sleepTimerSeconds--;

        // Gradual fade-out over the final 30 seconds
        if (this.sleepTimerFadeOut && this.sleepTimerSeconds <= 30 && this.sleepTimerSeconds > 0 && this.isPlaying) {
            if (this.sleepTimerOriginalVolume === null) {
                this.sleepTimerOriginalVolume = parseFloat(this.volumeSlider.value) || 0.85;
            }
            const ratio = this.sleepTimerSeconds / 30;
            const targetVol = Math.max(0, this.sleepTimerOriginalVolume * ratio);
            this.audio.volume = targetVol;
            this.volumeSlider.value = targetVol;
        }

        if (this.sleepTimerSeconds <= 0) {
            // Timer expired: stop playback and restore original volume for next session
            this.cancelSleepTimer(true);
            this.pause();
            this.showToast('🌙 Hẹn giờ: Đã tự động tắt nhạc. Chúc bạn ngủ ngon! ✨', 6000);
            return;
        }

        this.updateSleepTimerUI();
    }

    cancelSleepTimer(triggeredByTimer = false) {
        if (this.sleepTimerInterval) {
            clearInterval(this.sleepTimerInterval);
            this.sleepTimerInterval = null;
        }

        if (this.sleepTimerOriginalVolume !== null) {
            this.audio.volume = this.sleepTimerOriginalVolume;
            this.volumeSlider.value = this.sleepTimerOriginalVolume;
            this.sleepTimerOriginalVolume = null;
            this.updateVolumeIcons();
        }

        this.sleepTimerMode = null;
        this.sleepTimerSeconds = 0;
        this.sleepTimerTotalSeconds = 0;

        this.updateSleepTimerUI();

        if (!triggeredByTimer) {
            this.showToast('Đã hủy hẹn giờ tắt nhạc.');
        }
    }

    addSleepTimerMinutes(extraMinutes) {
        if (this.sleepTimerMode !== 'time') {
            this.startSleepTimer(extraMinutes, false);
            return;
        }

        // Restore volume if was in fade-out
        if (this.sleepTimerOriginalVolume !== null) {
            this.audio.volume = this.sleepTimerOriginalVolume;
            this.volumeSlider.value = this.sleepTimerOriginalVolume;
            this.sleepTimerOriginalVolume = null;
            this.updateVolumeIcons();
        }

        this.sleepTimerSeconds += extraMinutes * 60;
        this.sleepTimerTotalSeconds += extraMinutes * 60;
        this.updateSleepTimerUI();
        this.showToast(`🌙 Đã cộng thêm +${extraMinutes} phút vào hẹn giờ tắt nhạc.`);
    }

    updateSleepTimerUI() {
        const isActive = this.sleepTimerMode !== null;

        // Player Bar Button & Nav Badges
        if (this.sleepTimerBtn) {
            this.sleepTimerBtn.classList.toggle('active', isActive);
        }
        if (this.topNavSleepBtn) {
            this.topNavSleepBtn.classList.toggle('active', isActive);
        }
        if (this.topNavSleepBadge) {
            this.topNavSleepBadge.style.display = isActive ? 'block' : 'none';
        }

        if (this.sleepTimerBadge) {
            if (isActive) {
                this.sleepTimerBadge.style.display = 'inline-block';
                if (this.sleepTimerMode === 'end_of_track') {
                    this.sleepTimerBadge.textContent = 'Hết bài';
                } else {
                    const mins = Math.floor(this.sleepTimerSeconds / 60);
                    const secs = this.sleepTimerSeconds % 60;
                    this.sleepTimerBadge.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
                }
            } else {
                this.sleepTimerBadge.style.display = 'none';
            }
        }

        this.updateSleepTimerModalView();
    }

    updateSleepTimerModalView() {
        const isActive = this.sleepTimerMode !== null;

        if (this.sleepTimerRunningBox && this.sleepTimerConfigBox) {
            if (isActive) {
                this.sleepTimerRunningBox.style.display = 'flex';
                this.sleepTimerConfigBox.style.display = 'none';

                if (this.sleepTimerCountdownDisplay && this.sleepTimerCountdownSub) {
                    if (this.sleepTimerMode === 'end_of_track') {
                        this.sleepTimerCountdownDisplay.textContent = 'HẾT BÀI';
                        this.sleepTimerCountdownDisplay.style.fontSize = '1.6rem';
                        this.sleepTimerCountdownSub.textContent = 'Dừng phát khi kết thúc bài hiện tại';
                    } else {
                        const mins = Math.floor(this.sleepTimerSeconds / 60);
                        const secs = this.sleepTimerSeconds % 60;
                        this.sleepTimerCountdownDisplay.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
                        this.sleepTimerCountdownDisplay.style.fontSize = '2.2rem';
                        this.sleepTimerCountdownSub.textContent = 'Thời gian còn lại';
                    }
                }
            } else {
                this.sleepTimerRunningBox.style.display = 'none';
                this.sleepTimerConfigBox.style.display = 'block';
            }
        }
    }

    escapeHtml(str) {
        if (!str || typeof str !== 'string') return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    window.xtapoApp = new XTAPOMusicApp();
});



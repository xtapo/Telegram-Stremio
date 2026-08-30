package com.telegramstremio.music;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.support.v4.media.MediaBrowserCompat;
import android.support.v4.media.MediaDescriptionCompat;
import android.support.v4.media.MediaMetadataCompat;
import android.support.v4.media.session.MediaSessionCompat;
import android.support.v4.media.session.PlaybackStateCompat;
import android.text.TextUtils;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;
import androidx.media.MediaBrowserServiceCompat;
import androidx.media.session.MediaButtonReceiver;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class XTMediaBrowserService extends MediaBrowserServiceCompat {

    private static final String TAG = "XTMediaBrowserService";
    private static final String CHANNEL_ID = "xt_music_playback_channel";
    private static final int NOTIFICATION_ID = 501;

    public static final String ROOT_ID = "xt_root_id";
    public static final String FOLDER_ALL_TRACKS = "xt_folder_all_tracks";
    public static final String FOLDER_ALBUMS = "xt_folder_albums";

    public static XTMediaBrowserService instance;

    private MediaSessionCompat mediaSession;
    private PlaybackStateCompat.Builder stateBuilder;
    private MediaPlayer mediaPlayer;
    private ExecutorService executorService;
    private Handler mainHandler;

    // Track model for Android Auto
    public static class AutoTrack {
        public String id;
        public String title;
        public String artist;
        public String album;
        public String streamUrl;
        public String coverUrl;
        public String durationStr;
        public long durationMs;
    }

    public static class AutoAlbum {
        public String id;
        public String title;
        public String artist;
        public String coverUrl;
        public List<AutoTrack> tracks = new ArrayList<>();
    }

    private final List<AutoTrack> allTracks = new ArrayList<>();
    private final List<AutoAlbum> allAlbums = new ArrayList<>();
    private final Map<String, AutoTrack> trackMap = new HashMap<>();
    private int currentTrackIndex = -1;
    private Bitmap currentCoverBitmap = null;

    public interface MediaControlListener {
        void onPlayRequested();
        void onPauseRequested();
        void onSkipNextRequested();
        void onSkipPrevRequested();
        void onPlayTrackByIndex(int index, String trackId);
    }

    private static MediaControlListener controlListener;

    public static void setControlListener(MediaControlListener listener) {
        controlListener = listener;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        executorService = Executors.newSingleThreadExecutor();
        mainHandler = new Handler(Looper.getMainLooper());

        createNotificationChannel();
        initMediaSession();
        initMediaPlayer();

        // Fetch music catalog from server in background
        fetchServerCatalog();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "XT-Music Playback",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Điều khiển và phát nhạc XT-Music trên Android Auto");
            channel.setShowBadge(false);
            channel.setSound(null, null);
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private void initMediaSession() {
        mediaSession = new MediaSessionCompat(this, TAG);
        mediaSession.setFlags(
                MediaSessionCompat.FLAG_HANDLES_MEDIA_BUTTONS |
                MediaSessionCompat.FLAG_HANDLES_TRANSPORT_CONTROLS
        );

        Intent activityIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, activityIntent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );
        mediaSession.setSessionActivity(pendingIntent);

        stateBuilder = new PlaybackStateCompat.Builder()
                .setActions(
                        PlaybackStateCompat.ACTION_PLAY |
                        PlaybackStateCompat.ACTION_PAUSE |
                        PlaybackStateCompat.ACTION_PLAY_PAUSE |
                        PlaybackStateCompat.ACTION_SKIP_TO_NEXT |
                        PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS |
                        PlaybackStateCompat.ACTION_SEEK_TO |
                        PlaybackStateCompat.ACTION_STOP
                )
                .setState(PlaybackStateCompat.STATE_NONE, 0, 1.0f);
        mediaSession.setPlaybackState(stateBuilder.build());

        mediaSession.setCallback(new MediaSessionCompat.Callback() {
            @Override
            public void onPlay() {
                handlePlay();
            }

            @Override
            public void onPause() {
                handlePause();
            }

            @Override
            public void onSkipToNext() {
                handleSkipNext();
            }

            @Override
            public void onSkipToPrevious() {
                handleSkipPrevious();
            }

            @Override
            public void onSeekTo(long pos) {
                if (mediaPlayer != null && mediaPlayer.isPlaying()) {
                    mediaPlayer.seekTo((int) pos);
                    updatePlaybackState(PlaybackStateCompat.STATE_PLAYING, pos);
                }
            }

            @Override
            public void onPlayFromMediaId(String mediaId, Bundle extras) {
                handlePlayFromMediaId(mediaId);
            }

            @Override
            public void onStop() {
                handlePause();
                stopForeground(true);
            }
        });

        setSessionToken(mediaSession.getSessionToken());
    }

    private void initMediaPlayer() {
        mediaPlayer = new MediaPlayer();
        mediaPlayer.setAudioAttributes(
                new AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .build()
        );

        mediaPlayer.setOnPreparedListener(mp -> {
            mp.start();
            updatePlaybackState(PlaybackStateCompat.STATE_PLAYING, 0);
            updateNotification();
        });

        mediaPlayer.setOnCompletionListener(mp -> handleSkipNext());

        mediaPlayer.setOnErrorListener((mp, what, extra) -> {
            Log.e(TAG, "MediaPlayer error: " + what + ", " + extra);
            updatePlaybackState(PlaybackStateCompat.STATE_ERROR, 0);
            return true;
        });
    }

    private String getBaseServerUrl() {
        SharedPreferences prefs = getSharedPreferences("TelegramMusicPrefs", Context.MODE_PRIVATE);
        String url = prefs.getString("server_url", "https://tg.xtapo.org");
        if (TextUtils.isEmpty(url)) url = "https://tg.xtapo.org";
        while (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        return url;
    }

    private void fetchServerCatalog() {
        executorService.execute(() -> {
            try {
                String serverUrl = getBaseServerUrl();
                URL url = new URL(serverUrl + "/api/music/albums");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(6000);
                conn.setReadTimeout(10000);

                if (conn.getResponseCode() == 200) {
                    BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        sb.append(line);
                    }
                    reader.close();

                    parseCatalogJson(sb.toString(), serverUrl);
                    mainHandler.post(() -> notifyChildrenChanged(ROOT_ID));
                }
            } catch (Exception e) {
                Log.w(TAG, "Failed to load music catalog from server: " + e.getMessage());
            }
        });
    }

    private void parseCatalogJson(String jsonStr, String baseUrl) {
        try {
            JSONObject obj = new JSONObject(jsonStr);
            JSONArray albumsArr = obj.optJSONArray("albums");
            if (albumsArr == null) return;

            synchronized (allTracks) {
                allTracks.clear();
                allAlbums.clear();
                trackMap.clear();

                for (int i = 0; i < albumsArr.length(); i++) {
                    JSONObject albObj = albumsArr.getJSONObject(i);
                    AutoAlbum album = new AutoAlbum();
                    album.id = albObj.optString("id", "album_" + i);
                    album.title = albObj.optString("title", "Album " + (i + 1));
                    album.artist = albObj.optString("artist", "XT-Music");
                    String rawCover = albObj.optString("cover", "");
                    album.coverUrl = resolveUrl(rawCover, baseUrl);

                    JSONArray tracksArr = albObj.optJSONArray("tracks");
                    if (tracksArr != null) {
                        for (int j = 0; j < tracksArr.length(); j++) {
                            JSONObject trObj = tracksArr.getJSONObject(j);
                            AutoTrack track = new AutoTrack();
                            track.id = trObj.optString("id", album.id + "_tr_" + j);
                            track.title = trObj.optString("name", "Bài hát " + (j + 1));
                            track.artist = trObj.optString("artist", album.artist);
                            track.album = albObj.optString("title", album.title);
                            track.durationStr = trObj.optString("duration", "3:30");
                            
                            String previewUrl = trObj.optString("previewUrl", "");
                            track.streamUrl = resolveUrl(previewUrl, baseUrl);
                            track.coverUrl = resolveUrl(trObj.optString("coverUrl", album.coverUrl), baseUrl);

                            album.tracks.add(track);
                            allTracks.add(track);
                            trackMap.put(track.id, track);
                        }
                    }
                    allAlbums.add(album);
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error parsing catalog json: " + e.getMessage());
        }
    }

    private String resolveUrl(String path, String baseUrl) {
        if (TextUtils.isEmpty(path)) return "";
        if (path.startsWith("http://") || path.startsWith("https://")) {
            return path;
        }
        if (!path.startsWith("/")) {
            path = "/" + path;
        }
        return baseUrl + path;
    }

    private void handlePlay() {
        if (mediaPlayer != null && !mediaPlayer.isPlaying() && mediaPlayer.getCurrentPosition() > 0) {
            mediaPlayer.start();
            updatePlaybackState(PlaybackStateCompat.STATE_PLAYING, mediaPlayer.getCurrentPosition());
            updateNotification();
            return;
        }

        if (currentTrackIndex >= 0 && currentTrackIndex < allTracks.size()) {
            playTrackByIndex(currentTrackIndex);
        } else if (!allTracks.isEmpty()) {
            playTrackByIndex(0);
        } else {
            if (controlListener != null) {
                controlListener.onPlayRequested();
            }
        }
    }

    private void handlePause() {
        if (mediaPlayer != null && mediaPlayer.isPlaying()) {
            mediaPlayer.pause();
            updatePlaybackState(PlaybackStateCompat.STATE_PAUSED, mediaPlayer.getCurrentPosition());
            updateNotification();
        }
        if (controlListener != null) {
            controlListener.onPauseRequested();
        }
    }

    private void handleSkipNext() {
        if (allTracks.isEmpty()) {
            if (controlListener != null) controlListener.onSkipNextRequested();
            return;
        }
        int nextIndex = (currentTrackIndex + 1) % allTracks.size();
        playTrackByIndex(nextIndex);
        if (controlListener != null) {
            controlListener.onSkipNextRequested();
        }
    }

    private void handleSkipPrevious() {
        if (allTracks.isEmpty()) {
            if (controlListener != null) controlListener.onSkipPrevRequested();
            return;
        }
        int prevIndex = (currentTrackIndex - 1 + allTracks.size()) % allTracks.size();
        playTrackByIndex(prevIndex);
        if (controlListener != null) {
            controlListener.onSkipPrevRequested();
        }
    }

    private void handlePlayFromMediaId(String mediaId) {
        if (TextUtils.isEmpty(mediaId)) return;

        AutoTrack track = trackMap.get(mediaId);
        if (track != null) {
            int idx = allTracks.indexOf(track);
            if (idx >= 0) {
                playTrackByIndex(idx);
                if (controlListener != null) {
                    controlListener.onPlayTrackByIndex(idx, track.id);
                }
            }
        } else {
            handlePlay();
        }
    }

    private void playTrackByIndex(int index) {
        if (index < 0 || index >= allTracks.size()) return;
        currentTrackIndex = index;
        AutoTrack track = allTracks.get(index);

        updatePlaybackState(PlaybackStateCompat.STATE_BUFFERING, 0);

        executorService.execute(() -> {
            try {
                // Fetch artwork bitmap
                if (!TextUtils.isEmpty(track.coverUrl)) {
                    try {
                        URL u = new URL(track.coverUrl);
                        HttpURLConnection c = (HttpURLConnection) u.openConnection();
                        c.setConnectTimeout(4000);
                        c.setReadTimeout(4000);
                        InputStream is = c.getInputStream();
                        currentCoverBitmap = BitmapFactory.decodeStream(is);
                        is.close();
                    } catch (Exception ignored) {
                        currentCoverBitmap = null;
                    }
                }

                mainHandler.post(() -> {
                    updateMediaMetadata(track);
                    try {
                        mediaPlayer.reset();
                        mediaPlayer.setDataSource(track.streamUrl);
                        mediaPlayer.prepareAsync();
                    } catch (Exception e) {
                        Log.e(TAG, "Error playing track stream: " + e.getMessage());
                        updatePlaybackState(PlaybackStateCompat.STATE_ERROR, 0);
                    }
                });
            } catch (Exception e) {
                Log.e(TAG, "playTrackByIndex exception: " + e.getMessage());
            }
        });
    }

    private void updateMediaMetadata(AutoTrack track) {
        MediaMetadataCompat.Builder meta = new MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_MEDIA_ID, track.id)
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, track.title)
                .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, track.artist)
                .putString(MediaMetadataCompat.METADATA_KEY_ALBUM, track.album);

        if (currentCoverBitmap != null) {
            meta.putBitmap(MediaMetadataCompat.METADATA_KEY_ALBUM_ART, currentCoverBitmap);
            meta.putBitmap(MediaMetadataCompat.METADATA_KEY_DISPLAY_ICON, currentCoverBitmap);
        }

        mediaSession.setMetadata(meta.build());
    }

    public void updatePlaybackState(int state, long position) {
        if (mediaSession != null && stateBuilder != null) {
            stateBuilder.setState(state, position, 1.0f);
            mediaSession.setPlaybackState(stateBuilder.build());
            mediaSession.setActive(state == PlaybackStateCompat.STATE_PLAYING || state == PlaybackStateCompat.STATE_BUFFERING);
        }
    }

    public void updateTrack(String title, String artist, String album, String coverUrl, boolean isPlaying) {
        AutoTrack track = new AutoTrack();
        track.id = "web_track_now";
        track.title = title;
        track.artist = artist;
        track.album = album;
        track.coverUrl = coverUrl;

        executorService.execute(() -> {
            if (!TextUtils.isEmpty(coverUrl)) {
                try {
                    URL u = new URL(coverUrl);
                    HttpURLConnection c = (HttpURLConnection) u.openConnection();
                    c.setConnectTimeout(4000);
                    InputStream is = c.getInputStream();
                    currentCoverBitmap = BitmapFactory.decodeStream(is);
                    is.close();
                } catch (Exception ignored) {
                }
            }
            mainHandler.post(() -> {
                updateMediaMetadata(track);
                updatePlaybackState(isPlaying ? PlaybackStateCompat.STATE_PLAYING : PlaybackStateCompat.STATE_PAUSED, 0);
                updateNotification();
            });
        });
    }

    private void updateNotification() {
        try {
            MediaMetadataCompat meta = mediaSession.getController().getMetadata();
            if (meta == null) return;

            String title = meta.getString(MediaMetadataCompat.METADATA_KEY_TITLE);
            String artist = meta.getString(MediaMetadataCompat.METADATA_KEY_ARTIST);
            boolean isPlaying = mediaSession.getController().getPlaybackState() != null &&
                    mediaSession.getController().getPlaybackState().getState() == PlaybackStateCompat.STATE_PLAYING;

            Intent intent = new Intent(this, MainActivity.class);
            PendingIntent pi = PendingIntent.getActivity(
                    this, 0, intent,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
            );

            NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                    .setContentTitle(title)
                    .setContentText(artist)
                    .setSmallIcon(R.drawable.ic_launcher)
                    .setLargeIcon(currentCoverBitmap)
                    .setContentIntent(pi)
                    .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                    .setOngoing(isPlaying)
                    .addAction(
                            R.drawable.ic_launcher, "Previous",
                            MediaButtonReceiver.buildMediaButtonPendingIntent(this, PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS)
                    )
                    .addAction(
                            R.drawable.ic_launcher, isPlaying ? "Pause" : "Play",
                            MediaButtonReceiver.buildMediaButtonPendingIntent(this, isPlaying ? PlaybackStateCompat.ACTION_PAUSE : PlaybackStateCompat.ACTION_PLAY)
                    )
                    .addAction(
                            R.drawable.ic_launcher, "Next",
                            MediaButtonReceiver.buildMediaButtonPendingIntent(this, PlaybackStateCompat.ACTION_SKIP_TO_NEXT)
                    )
                    .setStyle(
                            new androidx.media.app.NotificationCompat.MediaStyle()
                                    .setMediaSession(mediaSession.getSessionToken())
                                    .setShowActionsInCompactView(0, 1, 2)
                    );

            Notification notif = builder.build();
            startForeground(NOTIFICATION_ID, notif);
        } catch (Exception e) {
            Log.w(TAG, "Failed to show notification: " + e.getMessage());
        }
    }

    @Nullable
    @Override
    public BrowserRoot onGetRoot(@NonNull String clientPackageName, int clientUid, @Nullable Bundle rootHints) {
        return new BrowserRoot(ROOT_ID, null);
    }

    @Override
    public void onLoadChildren(@NonNull String parentMediaId, @NonNull Result<List<MediaBrowserCompat.MediaItem>> result) {
        List<MediaBrowserCompat.MediaItem> items = new ArrayList<>();

        if (ROOT_ID.equals(parentMediaId)) {
            // Root menu for Android Auto
            MediaDescriptionCompat allTracksDesc = new MediaDescriptionCompat.Builder()
                    .setMediaId(FOLDER_ALL_TRACKS)
                    .setTitle("🎵 Tất cả bài hát")
                    .setSubtitle(allTracks.size() + " bài hát có sẵn")
                    .build();
            items.add(new MediaBrowserCompat.MediaItem(allTracksDesc, MediaBrowserCompat.MediaItem.FLAG_BROWSABLE));

            MediaDescriptionCompat albumsDesc = new MediaDescriptionCompat.Builder()
                    .setMediaId(FOLDER_ALBUMS)
                    .setTitle("💿 Danh sách Album")
                    .setSubtitle(allAlbums.size() + " Album phát hành")
                    .build();
            items.add(new MediaBrowserCompat.MediaItem(albumsDesc, MediaBrowserCompat.MediaItem.FLAG_BROWSABLE));

            if (!allTracks.isEmpty()) {
                AutoTrack first = allTracks.get(0);
                MediaDescriptionCompat streamDesc = new MediaDescriptionCompat.Builder()
                        .setMediaId(first.id)
                        .setTitle("▶️ " + first.title)
                        .setSubtitle(first.artist + " • Phát ngẫu nhiên")
                        .setIconUri(Uri.parse(first.coverUrl))
                        .build();
                items.add(new MediaBrowserCompat.MediaItem(streamDesc, MediaBrowserCompat.MediaItem.FLAG_PLAYABLE));
            }
        } else if (FOLDER_ALL_TRACKS.equals(parentMediaId)) {
            // Return all individual tracks
            for (AutoTrack t : allTracks) {
                MediaDescriptionCompat.Builder desc = new MediaDescriptionCompat.Builder()
                        .setMediaId(t.id)
                        .setTitle(t.title)
                        .setSubtitle(t.artist + " • " + t.album);

                if (!TextUtils.isEmpty(t.coverUrl)) {
                    desc.setIconUri(Uri.parse(t.coverUrl));
                }

                items.add(new MediaBrowserCompat.MediaItem(desc.build(), MediaBrowserCompat.MediaItem.FLAG_PLAYABLE));
            }
        } else if (FOLDER_ALBUMS.equals(parentMediaId)) {
            // Return albums list
            for (AutoAlbum a : allAlbums) {
                MediaDescriptionCompat.Builder desc = new MediaDescriptionCompat.Builder()
                        .setMediaId("album_group_" + a.id)
                        .setTitle(a.title)
                        .setSubtitle(a.artist + " (" + a.tracks.size() + " bài hát)");

                if (!TextUtils.isEmpty(a.coverUrl)) {
                    desc.setIconUri(Uri.parse(a.coverUrl));
                }

                items.add(new MediaBrowserCompat.MediaItem(desc.build(), MediaBrowserCompat.MediaItem.FLAG_BROWSABLE));
            }
        } else if (parentMediaId.startsWith("album_group_")) {
            // Return tracks inside clicked album
            String albumId = parentMediaId.replace("album_group_", "");
            for (AutoAlbum a : allAlbums) {
                if (a.id.equals(albumId)) {
                    for (AutoTrack t : a.tracks) {
                        MediaDescriptionCompat.Builder desc = new MediaDescriptionCompat.Builder()
                                .setMediaId(t.id)
                                .setTitle(t.title)
                                .setSubtitle(t.artist);

                        if (!TextUtils.isEmpty(t.coverUrl)) {
                            desc.setIconUri(Uri.parse(t.coverUrl));
                        }

                        items.add(new MediaBrowserCompat.MediaItem(desc.build(), MediaBrowserCompat.MediaItem.FLAG_PLAYABLE));
                    }
                    break;
                }
            }
        }

        result.sendResult(items);
    }

    @Override
    public void onDestroy() {
        if (mediaPlayer != null) {
            try {
                mediaPlayer.release();
            } catch (Exception ignored) {
            }
            mediaPlayer = null;
        }
        if (mediaSession != null) {
            mediaSession.release();
        }
        if (executorService != null) {
            executorService.shutdown();
        }
        instance = null;
        super.onDestroy();
    }
}

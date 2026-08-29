package com.telegramstremio.music;

import android.app.PendingIntent;
import android.content.Intent;
import android.os.Bundle;
import android.support.v4.media.MediaBrowserCompat;
import android.support.v4.media.MediaDescriptionCompat;
import android.support.v4.media.MediaMetadataCompat;
import android.support.v4.media.session.MediaSessionCompat;
import android.support.v4.media.session.PlaybackStateCompat;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.media.MediaBrowserServiceCompat;

import java.util.ArrayList;
import java.util.List;

public class XTMediaBrowserService extends MediaBrowserServiceCompat {

    private static final String MY_MEDIA_ROOT_ID = "xt_media_root_id";
    private static final String MY_EMPTY_MEDIA_ROOT_ID = "xt_empty_root_id";
    private static final String LOG_TAG = "XTMediaBrowserService";

    public static XTMediaBrowserService instance;
    private MediaSessionCompat mediaSession;
    private PlaybackStateCompat.Builder stateBuilder;

    public interface MediaControlListener {
        void onPlayRequested();
        void onPauseRequested();
        void onSkipNextRequested();
        void onSkipPrevRequested();
    }

    private static MediaControlListener controlListener;

    public static void setControlListener(MediaControlListener listener) {
        controlListener = listener;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;

        // Create a MediaSessionCompat
        mediaSession = new MediaSessionCompat(this, LOG_TAG);

        // Enable callbacks from MediaButtons and TransportControls
        mediaSession.setFlags(
                MediaSessionCompat.FLAG_HANDLES_MEDIA_BUTTONS |
                MediaSessionCompat.FLAG_HANDLES_TRANSPORT_CONTROLS
        );

        // PendingIntent to launch MainActivity when clicking on the player notification / car screen
        Intent activityIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, activityIntent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );
        mediaSession.setSessionActivity(pendingIntent);

        // Set an initial PlaybackState
        stateBuilder = new PlaybackStateCompat.Builder()
                .setActions(
                        PlaybackStateCompat.ACTION_PLAY |
                        PlaybackStateCompat.ACTION_PAUSE |
                        PlaybackStateCompat.ACTION_PLAY_PAUSE |
                        PlaybackStateCompat.ACTION_SKIP_TO_NEXT |
                        PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS |
                        PlaybackStateCompat.ACTION_STOP
                )
                .setState(PlaybackStateCompat.STATE_NONE, 0, 1.0f);
        mediaSession.setPlaybackState(stateBuilder.build());

        // Callbacks from car buttons or steering wheel controls
        mediaSession.setCallback(new MediaSessionCompat.Callback() {
            @Override
            public void onPlay() {
                updatePlaybackState(PlaybackStateCompat.STATE_PLAYING);
                if (controlListener != null) {
                    controlListener.onPlayRequested();
                }
            }

            @Override
            public void onPause() {
                updatePlaybackState(PlaybackStateCompat.STATE_PAUSED);
                if (controlListener != null) {
                    controlListener.onPauseRequested();
                }
            }

            @Override
            public void onSkipToNext() {
                if (controlListener != null) {
                    controlListener.onSkipNextRequested();
                }
            }

            @Override
            public void onSkipToPrevious() {
                if (controlListener != null) {
                    controlListener.onSkipPrevRequested();
                }
            }

            @Override
            public void onStop() {
                updatePlaybackState(PlaybackStateCompat.STATE_STOPPED);
                if (controlListener != null) {
                    controlListener.onPauseRequested();
                }
            }
        });

        // Set the session's token so that client activities can communicate with it.
        setSessionToken(mediaSession.getSessionToken());
    }

    public void updatePlaybackState(int state) {
        if (mediaSession != null && stateBuilder != null) {
            stateBuilder.setState(state, PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN, 1.0f);
            mediaSession.setPlaybackState(stateBuilder.build());
            mediaSession.setActive(state == PlaybackStateCompat.STATE_PLAYING);
        }
    }

    public void updateMetadata(String title, String artist, String album) {
        if (mediaSession != null) {
            MediaMetadataCompat.Builder metadataBuilder = new MediaMetadataCompat.Builder()
                    .putString(MediaMetadataCompat.METADATA_KEY_TITLE, title)
                    .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, artist)
                    .putString(MediaMetadataCompat.METADATA_KEY_ALBUM, album);
            mediaSession.setMetadata(metadataBuilder.build());
        }
    }

    @Nullable
    @Override
    public BrowserRoot onGetRoot(@NonNull String clientPackageName, int clientUid, @Nullable Bundle rootHints) {
        // Return root id for Android Auto
        return new BrowserRoot(MY_MEDIA_ROOT_ID, null);
    }

    @Override
    public void onLoadChildren(@NonNull String parentMediaId, @NonNull Result<List<MediaBrowserCompat.MediaItem>> result) {
        List<MediaBrowserCompat.MediaItem> mediaItems = new ArrayList<>();

        if (MY_MEDIA_ROOT_ID.equals(parentMediaId)) {
            // Build root items for Android Auto dashboard
            MediaDescriptionCompat desc = new MediaDescriptionCompat.Builder()
                    .setMediaId("xt_stream_now")
                    .setTitle("XT-Music Live Stream")
                    .setSubtitle("Mở và phát nhạc từ máy chủ")
                    .build();

            mediaItems.add(new MediaBrowserCompat.MediaItem(desc, MediaBrowserCompat.MediaItem.FLAG_PLAYABLE));
        }

        result.sendResult(mediaItems);
    }

    @Override
    public void onDestroy() {
        if (mediaSession != null) {
            mediaSession.release();
        }
        instance = null;
        super.onDestroy();
    }
}

package com.telegramstremio.music;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.text.TextUtils;
import android.app.UiModeManager;
import android.content.res.Configuration;
import android.view.KeyEvent;
import android.view.LayoutInflater;
import android.view.View;
import android.webkit.ConsoleMessage;
import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.OnBackPressedCallback;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

import com.google.android.material.dialog.MaterialAlertDialogBuilder;

public class MainActivity extends AppCompatActivity {

    private static final String PREFS_NAME = "TelegramMusicPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String DEFAULT_SERVER_URL = "https://tg.xtapo.org";
    private static final int REQUEST_NOTIFICATION_PERMISSION = 1001;

    private WebView webView;
    private SwipeRefreshLayout swipeRefresh;
    private ProgressBar progressBar;
    private LinearLayout errorLayout;
    private TextView tvErrorDetail;
    private Button btnRetry;
    private Button btnChangeServer;

    private SharedPreferences prefs;
    private PowerManager.WakeLock wakeLock;
    private long backPressedTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);

        initViews();
        setupWebView();
        setupWakeLock();
        checkPermissions();
        setupBackNavigation();
        setupMediaControls();

        String serverUrl = getServerUrl();
        if (TextUtils.isEmpty(serverUrl)) {
            showServerUrlDialog(true);
        } else {
            loadMusicUrl(serverUrl);
        }
    }

    private void setupMediaControls() {
        try {
            Intent serviceIntent = new Intent(this, XTMediaBrowserService.class);
            startService(serviceIntent);
        } catch (Exception ignored) {
        }

        XTMediaBrowserService.setControlListener(new XTMediaBrowserService.MediaControlListener() {
            @Override
            public void onPlayRequested() {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("document.querySelector('#playBtn')?.click() || (document.querySelector('audio') && document.querySelector('audio').play());", null);
                    }
                });
            }

            @Override
            public void onPauseRequested() {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("(document.querySelector('audio') && document.querySelector('audio').pause()) || document.querySelector('#playBtn')?.click();", null);
                    }
                });
            }

            @Override
            public void onSkipNextRequested() {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("document.querySelector('#nextBtn')?.click();", null);
                    }
                });
            }

            @Override
            public void onSkipPrevRequested() {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("document.querySelector('#prevBtn')?.click();", null);
                    }
                });
            }

            @Override
            public void onPlayTrackByIndex(int index, String trackId) {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.player && typeof window.player.playTrackById === 'function') { window.player.playTrackById('" + trackId + "'); }", null);
                    }
                });
            }
        });
    }

    public class WebAppInterface {
        @android.webkit.JavascriptInterface
        public void updateTrackInfo(String title, String artist, String album, String coverUrl, int isPlaying) {
            if (XTMediaBrowserService.instance != null) {
                XTMediaBrowserService.instance.updateTrack(title, artist, album, coverUrl, isPlaying == 1);
            }
        }
    }

    private void initViews() {
        webView = findViewById(R.id.web_view);
        swipeRefresh = findViewById(R.id.swipe_refresh);
        progressBar = findViewById(R.id.progress_bar);
        errorLayout = findViewById(R.id.error_layout);
        tvErrorDetail = findViewById(R.id.tv_error_detail);
        btnRetry = findViewById(R.id.btn_retry);
        btnChangeServer = findViewById(R.id.btn_change_server);

        // Swipe-to-refresh
        swipeRefresh.setColorSchemeColors(ContextCompat.getColor(this, R.color.primary));
        swipeRefresh.setProgressBackgroundColorSchemeColor(ContextCompat.getColor(this, R.color.surface_dark));
        swipeRefresh.setOnRefreshListener(() -> {
            if (webView != null) {
                webView.reload();
            } else {
                swipeRefresh.setRefreshing(false);
            }
        });

        btnRetry.setOnClickListener(v -> {
            errorLayout.setVisibility(View.GONE);
            webView.setVisibility(View.VISIBLE);
            String url = getServerUrl();
            if (!TextUtils.isEmpty(url)) {
                loadMusicUrl(url);
            } else {
                showServerUrlDialog(true);
            }
        });

        btnChangeServer.setOnClickListener(v -> showServerUrlDialog(false));
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);
        }
        CookieManager.getInstance().setAcceptCookie(true);

        // Custom User-Agent tag to identify app & Android TV
        String defaultUA = settings.getUserAgentString();
        boolean isTV = isAndroidTvDevice();
        String tvTag = isTV ? " TelegramMusicTV/1.0 AndroidTV Leanback" : " TelegramMusicApp/1.0";
        settings.setUserAgentString(defaultUA + tvTag);

        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);
        if (isTV) {
            webView.requestFocus();
        }

        // Android Bridge for 2-way syncing with Android Auto
        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                progressBar.setVisibility(View.VISIBLE);
                errorLayout.setVisibility(View.GONE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request.isForMainFrame()) {
                    progressBar.setVisibility(View.GONE);
                    swipeRefresh.setRefreshing(false);
                    webView.setVisibility(View.GONE);
                    errorLayout.setVisibility(View.VISIBLE);
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                        tvErrorDetail.setText("Lỗi kết nối: " + error.getDescription());
                    }
                }
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    return false; // Load inside webview
                }
                try {
                    // Open telegram links or external intent protocols
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                } catch (Exception e) {
                    return true;
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress < 100) {
                    progressBar.setVisibility(View.VISIBLE);
                    progressBar.setProgress(newProgress);
                } else {
                    progressBar.setVisibility(View.GONE);
                }
            }

            @Override
            public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
                return super.onConsoleMessage(consoleMessage);
            }
        });
    }

    private void setupWakeLock() {
        try {
            PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (powerManager != null) {
                wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "TelegramMusic:WakeLock");
            }
        } catch (Exception ignored) {
        }
    }

    private void checkPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(
                        this,
                        new String[]{Manifest.permission.POST_NOTIFICATIONS},
                        REQUEST_NOTIFICATION_PERMISSION
                );
            }
        }
        checkBatteryOptimizations();
    }

    private void checkBatteryOptimizations() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
                if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                    Intent intent = new Intent(android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                    intent.setData(Uri.parse("package:" + getPackageName()));
                    startActivity(intent);
                }
            }
        } catch (Exception ignored) {
        }
    }

    private void setupBackNavigation() {
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (errorLayout.getVisibility() == View.VISIBLE) {
                    finish();
                    return;
                }
                if (webView != null && webView.canGoBack()) {
                    webView.goBack();
                } else {
                    if (System.currentTimeMillis() - backPressedTime < 2000) {
                        finish();
                    } else {
                        backPressedTime = System.currentTimeMillis();
                        Toast.makeText(MainActivity.this, getString(R.string.exit_prompt), Toast.LENGTH_SHORT).show();
                    }
                }
            }
        });
    }

    private String getServerUrl() {
        return prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL);
    }

    private void saveServerUrl(String url) {
        prefs.edit().putString(KEY_SERVER_URL, url).apply();
    }

    private void loadMusicUrl(String baseServerUrl) {
        String finalUrl = baseServerUrl.trim();
        while (finalUrl.endsWith("/")) {
            finalUrl = finalUrl.substring(0, finalUrl.length() - 1);
        }

        // If user entered only domain (e.g. https://my-server.com), append /music
        if (!finalUrl.toLowerCase().endsWith("/music") && !finalUrl.toLowerCase().contains("/music/")) {
            finalUrl = finalUrl + "/music";
        }

        // On Android TV devices, directly load ultra-lightweight tv.html
        if (isAndroidTvDevice()) {
            if (!finalUrl.toLowerCase().endsWith("tv.html") && !finalUrl.toLowerCase().endsWith("/tv")) {
                if (finalUrl.endsWith("/music")) {
                    finalUrl = finalUrl + "/tv.html";
                } else if (!finalUrl.contains("tv.html")) {
                    finalUrl = finalUrl + (finalUrl.endsWith("/") ? "tv.html" : "/tv.html");
                }
            }
        }

        errorLayout.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
        webView.loadUrl(finalUrl);
    }

    public void showServerUrlDialog(boolean isInitial) {
        LayoutInflater inflater = LayoutInflater.from(this);
        View dialogView = inflater.inflate(R.layout.dialog_server_url, null);
        EditText etServerUrl = dialogView.findViewById(R.id.et_server_url);

        String currentUrl = getServerUrl();
        if (!TextUtils.isEmpty(currentUrl)) {
            etServerUrl.setText(currentUrl);
            etServerUrl.setSelection(currentUrl.length());
        }

        MaterialAlertDialogBuilder builder = new MaterialAlertDialogBuilder(this, com.google.android.material.R.style.ThemeOverlay_MaterialComponents_MaterialAlertDialog)
                .setView(dialogView)
                .setCancelable(!isInitial)
                .setPositiveButton(R.string.save_and_connect, (dialog, which) -> {
                    String input = etServerUrl.getText() != null ? etServerUrl.getText().toString().trim() : "";
                    if (TextUtils.isEmpty(input)) {
                        Toast.makeText(this, "Vui lòng nhập URL máy chủ hợp lệ", Toast.LENGTH_SHORT).show();
                        if (isInitial) {
                            showServerUrlDialog(true);
                        }
                        return;
                    }
                    if (!input.startsWith("http://") && !input.startsWith("https://")) {
                        input = "https://" + input;
                    }
                    saveServerUrl(input);
                    loadMusicUrl(input);
                });

        if (!isInitial) {
            builder.setNegativeButton(R.string.cancel, null);
        }

        builder.show();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (wakeLock != null && !wakeLock.isHeld()) {
            try {
                wakeLock.acquire();
            } catch (Exception ignored) {
            }
        }
        if (webView != null) {
            webView.onResume();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        // KHÔNG ngắt WakeLock và KHÔNG pause WebView ở đây để nhạc tiếp tục phát liên tục khi tắt màn hình!
    }

    private boolean isAndroidTvDevice() {
        try {
            UiModeManager uiModeManager = (UiModeManager) getSystemService(Context.UI_MODE_SERVICE);
            if (uiModeManager != null && uiModeManager.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION) {
                return true;
            }
            PackageManager pm = getPackageManager();
            if (pm != null && (pm.hasSystemFeature(PackageManager.FEATURE_LEANBACK) || pm.hasSystemFeature("android.hardware.type.television"))) {
                return true;
            }
        } catch (Exception ignored) {
        }
        return false;
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            int keyCode = event.getKeyCode();
            switch (keyCode) {
                case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                case KeyEvent.KEYCODE_HEADSETHOOK:
                    if (webView != null) {
                        webView.evaluateJavascript("window.player?.togglePlay();", null);
                        return true;
                    }
                    break;
                case KeyEvent.KEYCODE_MEDIA_PLAY:
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.player && !window.player.isPlaying) window.player.togglePlay();", null);
                        return true;
                    }
                    break;
                case KeyEvent.KEYCODE_MEDIA_PAUSE:
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.player && window.player.isPlaying) window.player.togglePlay();", null);
                        return true;
                    }
                    break;
                case KeyEvent.KEYCODE_MEDIA_NEXT:
                case KeyEvent.KEYCODE_MEDIA_FAST_FORWARD:
                    if (webView != null) {
                        webView.evaluateJavascript("window.player?.nextTrack();", null);
                        return true;
                    }
                    break;
                case KeyEvent.KEYCODE_MEDIA_PREVIOUS:
                case KeyEvent.KEYCODE_MEDIA_REWIND:
                    if (webView != null) {
                        webView.evaluateJavascript("window.player?.prevTrack();", null);
                        return true;
                    }
                    break;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    @Override
    protected void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {
            }
        }
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}

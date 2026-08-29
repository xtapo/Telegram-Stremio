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
        });
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

        // Custom User-Agent tag to identify app
        String defaultUA = settings.getUserAgentString();
        settings.setUserAgentString(defaultUA + " TelegramMusicApp/1.0");

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
        if (!finalUrl.toLowerCase().endsWith("/music")) {
            finalUrl = finalUrl + "/music";
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
                wakeLock.acquire(10 * 60 * 1000L /* 10 minutes */);
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
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {
            }
        }
        // Notice: We don't call webView.onPause() so HTML5 audio can continue playing seamlessly in background!
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}

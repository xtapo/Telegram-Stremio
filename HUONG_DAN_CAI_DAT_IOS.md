# 🍏 Hướng Dẫn Cài Đặt Ứng Dụng "XT-Music" Trên iPhone (iOS)

Bạn có 2 cách để sử dụng XT-Music trên iPhone:

---

## ⚡ Cách 1: Thêm vào Màn hình chính (PWA - Nhanh nhất, Không cần máy tính)

Đây là cách tối ưu nhất trên iOS, hoạt động độc lập toàn màn hình và hỗ trợ phát nhạc ngầm khi tắt màn hình:

1. Mở trình duyệt **Safari** trên iPhone.
2. Truy cập vào địa chỉ: **`https://tg.xtapo.org/music`**
3. Bấm vào nút **Chia sẻ** (biểu tượng ô vuông có mũi tên hướng lên 📤 ở thanh công cụ dưới).
4. Cuộn xuống và chọn **"Thêm vào MH chính"** (Add to Home Screen).
5. Nhập tên `XT-Music` rồi bấm **Thêm**.
6. Biểu tượng **XT-Music** sẽ xuất hiện trên màn hình chính như một App độc lập, hỗ trợ điều khiển trên Dynamic Island & Lock Screen.

---

## 📦 Cách 2: Tải & Cài file `.ipa` từ GitHub Actions (Sideload)

### Bước 1: Kích hoạt build file `.ipa` trên GitHub
1. Vào kho lưu trữ **Telegram-Stremio** trên GitHub.
2. Vào tab **Actions** > Chọn workflow **Build iOS IPA**.
3. Bấm **Run workflow** (hoặc tự động chạy khi bạn push code lên branch `master`/`main`).
4. Chờ khoảng 2-3 phút cho máy ảo macOS build xong, vào mục **Artifacts** tải file **`XT-Music-IPA`** (giải nén ra file `XT-Music.ipa`).

### Bước 2: Cài file `.ipa` vào iPhone
Do chính sách của Apple, file `.ipa` cần được ký qua công cụ Sideload:

* **Sử dụng Sideloadly (Khuyên dùng trên Windows/Mac):**
  1. Tải phần mềm [Sideloadly](https://sideloadly.io/) về máy tính.
  2. Kết nối iPhone với máy tính qua cáp USB.
  3. Kéo thả file `XT-Music.ipa` vào Sideloadly.
  4. Nhập tài khoản Apple ID của bạn và bấm **Start**.
  5. Khi hoàn tất, trên iPhone vào **Cài đặt > Cài đặt chung > Quản lý VPN & Thiết bị** > Bấm **Tin cậy (Trust)** tài khoản của bạn để mở app.

* **Sử dụng TrollStore (Nếu iOS hỗ trợ từ 14.0 - 16.6.1):**
  - Mở file `XT-Music.ipa` trực tiếp bằng TrollStore trên iPhone để cài đặt vĩnh viễn không cần ký lại sau 7 ngày.

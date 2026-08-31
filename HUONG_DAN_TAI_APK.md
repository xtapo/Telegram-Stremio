# 📱 Hướng Dẫn Tải & Cài Đặt Ứng Dụng APK "XT-Music"

Ứng dụng Android **XT-Music** cho phép bạn nghe nhạc từ máy chủ Telegram-Stremio trực tiếp trên điện thoại, hỗ trợ **phát nhạc ngầm khi tắt màn hình**, hiển thị thông tin bài hát trên màn hình khóa và điều khiển qua thanh thông báo (Notification Media Controls).

---

## 🚀 Cách 1: Tải file APK tự động qua GitHub Actions (Khuyên dùng)

Bạn không cần cài đặt phần mềm lập trình nào trên máy tính, GitHub sẽ tự động build file `.apk` cho bạn:

### Bước 1: Đẩy (Push) code lên GitHub
Mở terminal hoặc Git client của bạn và chạy lệnh:
```bash
git add .
git commit -m "Update app to XT-Music"
git push
```

### Bước 2: Tải file APK từ GitHub
1. Truy cập vào kho lưu trữ (Repository) **Telegram-Stremio** của bạn trên GitHub.
2. Nhấp vào tab **Actions** ở menu trên cùng.
3. Ở danh sách bên trái, chọn **Build Android APK**.
4. Nhấp vào nút **Run workflow** (hoặc chọn đợt chạy mới nhất do lệnh `git push` kích hoạt).
5. Chờ khoảng **1 đến 2 phút** để tiến trình build hoàn tất (hiện dấu tích xanh ✅).
6. Nhấp vào lần chạy vừa hoàn thành, cuộn xuống mục **Artifacts** ở dưới cùng.
7. Nhấp vào **XT-Music-APK** để tải file `.zip` chứa file cài đặt `XT-Music.apk`.

---

## 📲 Cách 2: Cài đặt và Kết nối trên Điện thoại

1. Chuyển file `XT-Music.apk` vào điện thoại của bạn (qua Zalo, Telegram, Google Drive hoặc tải trực tiếp bằng trình duyệt trên điện thoại).
2. Nhấp vào file `.apk` để tiến hành cài đặt:
   - *Nếu điện thoại hỏi "Cho phép cài đặt ứng dụng từ nguồn này", hãy bật "Cho phép" (Allow).*
3. Mở ứng dụng **XT-Music**:
   - Lần đầu tiên mở app, một bảng thông báo sẽ xuất hiện yêu cầu **Cấu hình Server**.
   - Nhập URL máy chủ của bạn (Ví dụ: `https://my-server.hf.space` hoặc `http://192.168.1.10:8000`).
   - Bấm **Lưu & Kết nối**.
4. Trình phát nhạc sẽ tải ngay lập tức!

> 💡 **Mẹo:** Nếu bạn muốn đổi sang địa chỉ máy chủ khác sau này, bạn chỉ cần nhấn nút **Đổi Server** khi mất kết nối hoặc xóa dữ liệu ứng dụng trong Cài đặt của điện thoại.

---

## 🚗 Cách Sử Dụng Trên Màn Hình Xe Hơi (Android Auto)

Ứng dụng **XT-Music** đã được tích hợp chuẩn `MediaBrowserService` để hiển thị và điều khiển trực tiếp trên màn hình xe ô tô.

### Bước kích hoạt 1 lần duy nhất trên điện thoại:
1. Mở ứng dụng **Android Auto** trên điện thoại (hoặc vào *Cài đặt > tìm "Android Auto"*).
2. Cuộn xuống dưới cùng > **Chạm 10 lần liên tiếp vào dòng "Phiên bản" (Version)** cho đến khi hiện thông báo bật chế độ nhà phát triển.
3. Bấm vào biểu tượng **3 dấu chấm (⋮)** ở góc trên bên phải > Chọn **Cài đặt cho nhà phát triển (Developer settings)**.
4. Tích chọn **"Nguồn không xác định" (Unknown sources)**.
5. Cắm điện thoại vào màn hình xe qua cổng USB hoặc kết nối Android Auto không dây: **XT-Music** sẽ xuất hiện trên danh sách ứng dụng giải trí của xe, hỗ trợ bấm chuyển bài ngay trên vô lăng!

## 📺 Cách Sử Dụng Trên Android TV / Google TV / TV Box (Bản Cấu Hình Yếu)

Ứng dụng **XT-Music** đã được tích hợp chuẩn **Leanback Launcher** và chế độ **TV Lite Siêu Nhẹ**:

1. Cài đặt file `XT-Music.apk` lên Android TV (qua USB, ứng dụng *Send Files to TV*, hoặc trình duyệt trên TV).
2. Icon **XT-Music** sẽ xuất hiện trực tiếp trên màn hình chính (Home Launcher) của Android TV / Google TV.
3. **Điều khiển hoàn toàn bằng Remote TV (D-Pad)**:
   - **4 phím mũi tên (▲ ▼ ◀ ▶)**: Di chuyển giữa các bài hát, album, danh mục, thanh điều khiển.
   - **Phím OK / Enter**: Chọn phát nhạc hoặc mở menu.
   - **Phím Back / Quay lại**: Đóng cửa sổ popup, thoát mục hoặc quay về danh sách.
   - **Phím Media trên Remote (Play / Pause / Next / Prev)**: Điều khiển phát nhạc trực tiếp tức thì.
4. **Tự động kích hoạt TV Lite Mode**:
   - Khi chạy trên Android TV hoặc màn hình lớn, app tự động tắt toàn bộ hiệu ứng nặng (`backdrop-filter: blur`, visualizer canvas, đồ họa xoay 3D) giúp thiết bị RAM 1GB - 2GB chạy mượt mà, phản hồi ngay lập tức và không giật lag.

---

## 🎧 Tính Năng Nổi Bật của Ứng Dụng APK
- ✅ **Hỗ trợ Android TV / Google TV**: Hiển thị trên màn hình chính Leanback, điều khiển 100% bằng Remote TV D-Pad.
- ✅ **Chế độ TV Lite (Zero Lag)**: Tối ưu triệt để cho TV và TV Box cấu hình yếu.
- ✅ **Hỗ trợ Android Auto**: Hiển thị trên màn hình xe ô tô, điều khiển qua phím vô lăng.
- ✅ **Phát nhạc nền (Background Playback)**: Nhạc vẫn phát mượt mà khi bạn khóa màn hình hoặc dùng ứng dụng khác.
- ✅ **MediaSession Controls**: Hiển thị tên bài hát, ảnh bìa album và các nút Next/Previous/Pause trên màn hình khóa / remote.
- ✅ **Giao diện tối (Dark Mode)**: Tương thích hoàn hảo với giao diện người dùng hiện đại của Web Player.

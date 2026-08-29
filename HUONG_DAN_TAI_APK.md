# 📱 Hướng Dẫn Tải & Cài Đặt Ứng Dụng APK "Telegram Music"

Ứng dụng Android **Telegram Music** cho phép bạn nghe nhạc từ máy chủ Telegram-Stremio trực tiếp trên điện thoại, hỗ trợ **phát nhạc ngầm khi tắt màn hình**, hiển thị thông tin bài hát trên màn hình khóa và điều khiển qua thanh thông báo (Notification Media Controls).

---

## 🚀 Cách 1: Tải file APK tự động qua GitHub Actions (Khuyên dùng)

Bạn không cần cài đặt phần mềm lập trình nào trên máy tính, GitHub sẽ tự động build file `.apk` cho bạn:

### Bước 1: Đẩy (Push) code lên GitHub
Mở terminal hoặc Git client của bạn và chạy lệnh:
```bash
git add .
git commit -m "Add Android app and APK build workflow"
git push
```

### Bước 2: Tải file APK từ GitHub
1. Truy cập vào kho lưu trữ (Repository) **Telegram-Stremio** của bạn trên GitHub.
2. Nhấp vào tab **Actions** ở menu trên cùng.
3. Ở danh sách bên trái, chọn **Build Android APK**.
4. Nhấp vào nút **Run workflow** (hoặc chọn đợt chạy mới nhất do lệnh `git push` kích hoạt).
5. Chờ khoảng **1 đến 2 phút** để tiến trình build hoàn tất (hiện dấu tích xanh ✅).
6. Nhấp vào lần chạy vừa hoàn thành, cuộn xuống mục **Artifacts** ở dưới cùng.
7. Nhấp vào **Telegram-Music-APK** để tải file `.zip` chứa file cài đặt `Telegram-Music.apk`.

---

## 📲 Cách 2: Cài đặt và Kết nối trên Điện thoại

1. Chuyển file `Telegram-Music.apk` vào điện thoại của bạn (qua Zalo, Telegram, Google Drive hoặc tải trực tiếp bằng trình duyệt trên điện thoại).
2. Nhấp vào file `.apk` để tiến hành cài đặt:
   - *Nếu điện thoại hỏi "Cho phép cài đặt ứng dụng từ nguồn này", hãy bật "Cho phép" (Allow).*
3. Mở ứng dụng **Telegram Music**:
   - Lần đầu tiên mở app, một bảng thông báo sẽ xuất hiện yêu cầu **Cấu hình Server**.
   - Nhập URL máy chủ của bạn (Ví dụ: `https://my-server.hf.space` hoặc `http://192.168.1.10:8000`).
   - Bấm **Lưu & Kết nối**.
4. Trình phát nhạc sẽ tải ngay lập tức!

> 💡 **Mẹo:** Nếu bạn muốn đổi sang địa chỉ máy chủ khác sau này, bạn chỉ cần nhấn nút **Đổi Server** khi mất kết nối hoặc xóa dữ liệu ứng dụng trong Cài đặt của điện thoại.

---

## 🎧 Tính Năng Nổi Bật của Ứng Dụng APK
- ✅ **Phát nhạc nền (Background Playback)**: Nhạc vẫn phát mượt mà khi bạn khóa màn hình hoặc dùng ứng dụng khác (Facebook, lướt web, v.v.).
- ✅ **MediaSession Controls**: Hiển thị tên bài hát, ảnh bìa album và các nút Next/Previous/Pause trên màn hình khóa.
- ✅ **Giao diện tối (Dark Mode)**: Tương thích hoàn hảo với giao diện người dùng hiện đại của Web Player.
- ✅ **Điều hướng mượt mà**: Phím Back hỗ trợ quay lại trang trước, nhấn 2 lần liên tiếp để thoát ứng dụng.

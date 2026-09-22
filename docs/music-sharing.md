# Chia sẻ playlist và nhạc yêu thích

Trên giao diện `/music/` (máy tính hoặc điện thoại):

1. Mở **PLAYLISTS**, chọn **Chia sẻ** ở playlist muốn gửi. Trong **YÊU THÍCH**, dùng **Chia sẻ tất cả** hoặc **Chia sẻ** ở từng bài hát.
2. Nhập tên đăng nhập tài khoản XTAPO MUSIC của người nhận trên cùng máy chủ (có thể thêm `@` ở đầu), rồi bấm **Gửi chia sẻ**.
3. Người nhận mở **Được chia sẻ** trong PLAYLISTS hoặc YÊU THÍCH. Bấm **Làm mới** để nhận danh sách mới nhất.
4. Chọn **Phát**, **Xem bài hát**, **Lưu playlist** hoặc **Thêm vào yêu thích**.

Chia sẻ lưu bản sao tại thời điểm gửi; thay đổi sau đó ở danh sách gốc không cập nhật bản đã gửi. Lưu playlist tạo bản riêng có thể chỉnh sửa. Lưu cùng một chia sẻ nhiều lần không tạo thêm playlist hoặc thêm trùng bài yêu thích. **Bỏ khỏi danh sách** xóa mục nhận chia sẻ, giữ lại playlist và yêu thích đã lưu.

Chỉ tài khoản nhận đang đăng nhập và hoạt động mới đọc, lưu hoặc bỏ mục chia sẻ. Người gửi chỉ chọn được playlist/yêu thích của mình. Tên đăng nhập không phân biệt chữ hoa/thường; không gửi cho chính mình hoặc tài khoản bị khóa. Mỗi lần gửi tối đa 2.000 bài có đường dẫn phát hợp lệ. Chia sẻ không cấp thêm quyền truy cập kênh Telegram; bài trong kênh riêng vẫn cần quyền phát hợp lệ của người nhận.

## Lưu trữ và kiểm thử

Các bản chia sẻ được lưu trong collection `tracking.music_user_shares`; chỉ mục theo người nhận và ngày gửi được tạo khi backend kết nối cơ sở dữ liệu. Không cần biến môi trường mới. Giao diện TV Lite hiện dùng playlist/yêu thích đã lưu qua giao diện `/music/`.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_music_sharing.py -v
node tests/test_music_sharing.cjs
node tests/test_music_album_picker.cjs
```

Kiểm tra giao diện bằng dữ liệu giả lập, không kết nối MongoDB/Telegram thật:

```powershell
.venv\Scripts\python.exe tests/test_music_sharing.py --serve
```

Mở `http://127.0.0.1:8765/fixture/alice` để gửi cho `bob`, rồi mở `/fixture/bob` trên cùng máy chủ để kiểm tra nhận và lưu. Máy chủ thử nghiệm chỉ nghe trên loopback, dùng dữ liệu trong RAM và âm thanh im lặng; không dùng máy chủ này để triển khai.

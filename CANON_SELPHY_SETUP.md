# Hướng dẫn cấu hình in Canon Selphy CP

## Vấn đề
Khi in qua browser, máy in Canon Selphy CP in ra giấy A4 thay vì kích thước 4x6 inches như mong muốn.

## Giải pháp

### Cách 1: Sử dụng Print Agent (Khuyến nghị)

Print Agent cho phép in trực tiếp với cấu hình kích thước giấy chính xác.

#### Bước 1: Cài đặt Print Agent

```bash
cd print-agent
npm install
npm start
```

Print agent sẽ chạy trên `http://localhost:3000`

#### Bước 2: Cấu hình máy in Canon Selphy CP trong Windows

1. Mở **Settings** > **Devices** > **Printers & scanners**
2. Tìm máy in **Canon Selphy CP**
3. Click **Manage** > **Printing preferences**
4. Thiết lập:
   - **Paper Size**: 4x6 inches (hoặc 100x150mm)
   - **Paper Type**: Photo Paper
   - **Quality**: Best/High
5. Click **OK** để lưu

#### Bước 3: In từ ứng dụng

1. Sau khi chụp ảnh, click **"In ảnh"**
2. Chọn **"Direct Print (Agent)"** (nếu print agent đang chạy)
3. Chọn **Canon Selphy CP** từ dropdown "Select Printer"
4. Chọn **Paper Size: 4x6 inches**
5. Click **"Print with Agent"**

### Cách 2: Sử dụng Browser Print (Cần cấu hình thủ công)

1. Click **"Print with Browser"**
2. Trong hộp thoại Print:
   - Chọn máy in **Canon Selphy CP**
   - Click **"More settings"** hoặc **"Printer properties"**
   - Đặt **Paper Size** = **4x6 inches** (hoặc 100x150mm)
   - Đặt **Paper Type** = **Photo Paper**
   - Bỏ chọn **"Fit to page"** nếu muốn kích thước chính xác
3. Click **Print**

**Lưu ý**: Mỗi lần in qua browser, bạn cần cấu hình lại paper size trong print dialog.

## Cấu hình mặc định cho Canon Selphy CP

Để tránh phải cấu hình mỗi lần in:

### Windows 10/11:

1. Mở **Control Panel** > **Devices and Printers**
2. Right-click **Canon Selphy CP** > **Printing preferences**
3. Tab **Page Setup**:
   - Paper Size: **4x6 inches**
   - Orientation: **Portrait** (hoặc Landscape tùy layout)
4. Tab **Main**:
   - Paper Type: **Photo Paper**
   - Print Quality: **Best**
5. Click **OK**

### Thiết lập làm máy in mặc định (Tùy chọn)

1. Right-click **Canon Selphy CP**
2. Chọn **"Set as default printer"**

## Kiểm tra kết nối

### Kiểm tra Print Agent

1. Mở browser, truy cập: `http://localhost:3000/status`
2. Bạn sẽ thấy danh sách máy in có sẵn
3. Tìm **Canon Selphy CP** trong danh sách

### Kiểm tra máy in trong Windows

```powershell
# Mở PowerShell và chạy:
Get-Printer | Select-Object Name, Default
```

Bạn sẽ thấy Canon Selphy CP trong danh sách.

## Xử lý lỗi

### Lỗi: "Print agent is not available"
- Đảm bảo print agent đang chạy: `npm start` trong thư mục `print-agent`
- Kiểm tra port 3000 không bị chiếm bởi ứng dụng khác

### Lỗi: "Printer not found"
- Kiểm tra máy in đã được cài đặt driver và kết nối
- Restart print agent sau khi kết nối máy in
- Kiểm tra máy in có bật và có giấy/ink

### Vẫn in ra A4
- Đảm bảo đã cấu hình Paper Size = 4x6 inches trong printer properties
- Sử dụng Print Agent thay vì Browser Print
- Kiểm tra driver Canon Selphy CP đã được cài đặt đúng

### Chất lượng in kém
- Đảm bảo Paper Type = Photo Paper
- Chọn Print Quality = Best/High
- Kiểm tra độ phân giải ảnh (khuyến nghị 300 DPI)

## Tối ưu hóa

1. **Luôn sử dụng Print Agent**: Cho kết quả nhất quán và chính xác
2. **Cấu hình mặc định**: Thiết lập printer properties một lần để dùng mãi
3. **Kiểm tra trước khi in**: Xem preview trong ứng dụng để đảm bảo layout đúng

## Hỗ trợ

Nếu vẫn gặp vấn đề:
1. Kiểm tra log của print agent trong terminal
2. Kiểm tra Windows Event Viewer > Applications and Services Logs
3. Thử in test page từ Windows Settings để đảm bảo máy in hoạt động

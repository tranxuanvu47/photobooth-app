import urllib.request
import base64
import ssl

# URL phải khớp với Username: Nếu dùng 'photobooth' thì URL kết thúc bằng /photobooth/
url = "https://drive.congchunghoangvanviet.com/remote.php/dav/files/photobooth/"
user = "photobooth"
password = "7daTr-r7zyy-zY6cB-Zeopx-g73kQ"

auth = base64.b64encode(f"{user}:{password}".encode()).decode()
headers = {
    'Authorization': f'Basic {auth}',
    'Depth': '0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

print(f"Testing URL: {url}")
req = urllib.request.Request(url, method='PROPFIND', headers=headers)
context = ssl._create_unverified_context()

try:
    with urllib.request.urlopen(req, context=context) as response:
        print(f"Status Code: {response.getcode()}")
        print("Response Body (first 300 chars):")
        print(response.read().decode('utf-8')[:300])
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    print("Response Body:")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
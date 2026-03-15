import urllib.request
import base64
import ssl
import os
from urllib.parse import quote

BASE = "https://drive.congchunghoangvanviet.com/remote.php/dav/files/photobooth/"
USER = "photobooth"
PASSWORD = "7daTr-r7zyy-zY6cB-Zeopx-g73kQ"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def dav_url_join(base, rel, is_dir=False):
    base = base.rstrip('/')
    rel = rel.strip('/')
    if not rel:
        return base + ('/' if is_dir else '')
    parts = [quote(p) for p in rel.split('/') if p]
    url = f"{base}/{'/'.join(parts)}"
    if is_dir: url += "/"
    return url

def mkcol_recursive(base_dav, rel_path, context):
    auth = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
    accum = ""
    for seg in [x for x in rel_path.strip("/").split("/") if x]:
        accum += "/" + seg
        url = dav_url_join(base_dav, accum, is_dir=True)
        
        headers = {
            'Authorization': f'Basic {auth}',
            'User-Agent': USER_AGENT,
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        print(f"MKCOL {url}", end=" ")
        req = urllib.request.Request(url, method='MKCOL', headers=headers)
        try:
            with urllib.request.urlopen(req, context=context) as response:
                print("->", response.getcode())
        except urllib.error.HTTPError as e:
            print("->", e.code, "(Existing or OK)" if e.code in [405, 403] else f"- ERROR: {e.reason}")
            if e.code not in [405, 403]: return False
        except Exception as e:
            print(f"-> Error: {e}")
            return False
    return True

def upload_file(base_dav, rel_dir, local_file, remote_name, context):
    auth = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
    url = dav_url_join(base_dav, f"{rel_dir}/{remote_name}", is_dir=False)
    
    with open(local_file, 'rb') as f:
        data = f.read()
        
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/octet-stream',
        'Content-Length': str(len(data)),
        'User-Agent': USER_AGENT,
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    print(f"PUT {url}", end=" ")
    req = urllib.request.Request(url, data=data, method='PUT', headers=headers)
    try:
        with urllib.request.urlopen(req, context=context) as response:
            print("->", response.getcode())
            return True
    except urllib.error.HTTPError as e:
        print("->", e.code, f"- ERROR: {e.reason}")
        return False
    except Exception as e:
        print(f"-> Error: {e}")
        return False

if __name__ == "__main__":
    test_dir = "Photobooth/Raw/Khach_Mac_Dinh"
    test_file = "test.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("hello nextcloud from urllib")
    
    context = ssl._create_unverified_context()
    
    if mkcol_recursive(BASE, test_dir, context):
        if upload_file(BASE, test_dir, test_file, "test.txt", context):
            print("\n✅ Full Upload Flow OK!")
        else:
            print("\n❌ Upload Failed.")
    else:
        print("\n❌ MKCOL Failed.")
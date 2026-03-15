import os
import urllib.request
import urllib.parse
import base64
import ssl
import json

def nc_get_base_domain(dav_url):
    """Extrapolate base domain from DAV URL."""
    # E.g. https://drive.example.com/remote.php/dav/files/user/ -> https://drive.example.com
    parsed = urllib.parse.urlparse(dav_url)
    return f"{parsed.scheme}://{parsed.netloc}"

def nc_ocs_request(base_domain, endpoint, method, user, password, data=None):
    """Make a request to the Nextcloud OCS API."""
    url = f"{base_domain.rstrip('/')}{endpoint}"
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {
        'Authorization': f'Basic {auth}',
        'OCS-APIRequest': 'true',
        'Accept': 'application/json',
        'User-Agent': 'Photobooth-App (Python)'
    }
    
    encoded_data = None
    if data:
        encoded_data = urllib.parse.urlencode(data).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    req = urllib.request.Request(url, data=encoded_data, method=method, headers=headers)
    try:
        try:
            context = ssl.create_default_context()
        except:
            context = ssl._create_unverified_context()
            
        with urllib.request.urlopen(req, context=context) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"DEBUG: OCS Request failed for {url}: {e}")
        return None

def nc_get_public_link(nc_config):
    """
    Tries to find an existing public share link for NC_REMOTE_PATH.
    If not found, tries to create one.
    Returns (True, url) or (False, error_msg)
    """
    base_dav = nc_config['NC_URL']
    user = nc_config['NC_USER']
    password = nc_config['NC_PASS']
    path = nc_config['NC_REMOTE_PATH'].strip('/')
    
    domain = nc_get_base_domain(base_dav)
    shares_endpoint = "/ocs/v2.php/apps/files_sharing/api/v1/shares"
    
    # 1. Check existing shares
    res = nc_ocs_request(domain, f"{shares_endpoint}?path={urllib.parse.quote(path)}", 'GET', user, password)
    if res and res.get('ocs', {}).get('meta', {}).get('status') == 'ok':
        shares = res.get('ocs', {}).get('data', [])
        for s in shares:
            if s.get('share_type') == 3: # Public link
                return True, s.get('url')
                
    # 2. Not found, create one
    print(f"DEBUG: Creating new public share for {path}...")
    data = {
        'path': f"/{path}",
        'shareType': 3, # Public link
        'permissions': 1 # Read only
    }
    res = nc_ocs_request(domain, shares_endpoint, 'POST', user, password, data=data)
    if res and res.get('ocs', {}).get('meta', {}).get('status') == 'ok':
        share_data = res.get('ocs', {}).get('data', {})
        return True, share_data.get('url')
    
    # Check if maybe it already exists but GET didn't return it (rare) or 403
    status = res.get('ocs', {}).get('meta', {}).get('status') if res else "Unknown"
    msg = res.get('ocs', {}).get('meta', {}).get('message') if res else "Request failed"
    return False, f"OCS Error ({status}): {msg}"

def dav_url_join(base, rel, is_dir=False):
    """
    Join a base URL and a relative path, ensuring each segment of the path is URL-encoded.
    """
    base = base.rstrip('/')
    rel = rel.strip('/')
    if not rel:
        return base + ('/' if is_dir else '')
    
    segments = [urllib.parse.quote(seg) for seg in rel.split('/') if seg]
    url = f"{base}/{'/'.join(segments)}"
    if is_dir:
        url += '/'
    return url

def nc_exists(base_dav, rel_path, user, password, context):
    """Check if a path exists on the WebDAV server using PROPFIND."""
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {
        'Authorization': f'Basic {auth}',
        'Depth': '0',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    # Check both with and without trailing slash for maximum compatibility
    for is_dir in [True, False]:
        url = dav_url_join(base_dav, rel_path, is_dir=is_dir)
        req = urllib.request.Request(url, method='PROPFIND', headers=headers)
        try:
            with urllib.request.urlopen(req, context=context) as response:
                if response.getcode() in [200, 207]:
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            if e.code in [401, 403]:
                # Log that we got forbidden on a simple exists check
                print(f"DEBUG: PROPFIND Forbidden ({e.code}) at {url}")
        except Exception:
            pass
    return False

def nc_mkcol_recursive(base_dav, rel_path, user, password):
    """
    Recursively create directories on a WebDAV server using the MKCOL method.
    """
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    # Debug: Masked credentials
    masked_auth = auth[:4] + "..." + auth[-4:] if len(auth) > 8 else "****"
    
    accum = ""
    try:
        context = ssl.create_default_context()
    except:
        context = ssl._create_unverified_context()
        
    for seg in rel_path.strip('/').split('/'):
        if not seg:
            continue
        accum += f"/{seg}"
        
        # 1. Check if it exists first
        if nc_exists(base_dav, accum, user, password, context):
            continue
            
        # 2. Doesn't exist, try MKCOL
        headers = {
            'Authorization': f'Basic {auth}',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': user_agent
        }
        url = dav_url_join(base_dav, accum, is_dir=True)
        print(f"DEBUG: MKCOL -> {url}")
        
        req = urllib.request.Request(url, method='MKCOL', headers=headers)
        code = 0
        try:
            with urllib.request.urlopen(req, context=context) as response:
                code = response.getcode()
        except urllib.error.HTTPError as e:
            code = e.code
            # Try once to see if it's a 403 with useful info in body
            try:
                body = e.read().decode('utf-8', errors='ignore')
                print(f"DEBUG: Server error body: {body[:200]}")
            except: pass
        except Exception as e:
            return False, f"Exception: {str(e)}"
            
        # 201 Created is success. 405 means it exists.
        if code not in [201, 405, 207, 403]:
            # If 403, we really want to know why.
            return False, f"HTTP {code} for {accum}. URL: {url}"
            
        if code == 403:
            print(f"DEBUG: MKCOL returned 403 for {url}. Assuming it might exist or restricted.")
            
    return True, "Done"

def nc_put_file(base_dav, rel_dir, local_path, remote_name, user, password):
    """
    Upload a local file to a WebDAV server using the PUT method.
    """
    if not os.path.exists(local_path):
        return False, "Local file not found"
        
    url = dav_url_join(base_dav, f"{rel_dir}/{remote_name}", is_dir=False)
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    
    try:
        # Use simple read for file content
        with open(local_path, 'rb') as f:
            data = f.read()
            
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/octet-stream',
            'Content-Length': str(len(data)),
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        try:
            context = ssl.create_default_context()
        except:
            context = ssl._create_unverified_context()

        print(f"DEBUG: PUT -> {url}")
        req = urllib.request.Request(url, data=data, method='PUT', headers=headers)
        
        with urllib.request.urlopen(req, context=context) as response:
            code = response.getcode()
            
        if 200 <= code < 300:
            return True, f"Success (HTTP {code})"
        else:
            return False, f"HTTP Error {code}"
            
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error {e.code}: {e.reason} at {url}"
    except Exception as e:
        return False, str(e)

def upload_to_nextcloud(nc_config, local_path, remote_subfolder, remote_name=None):
    """
    High-level function to handle directory creation and file upload.
    nc_config: dict with NC_URL, NC_USER, NC_PASS, NC_REMOTE_PATH
    """
    if not nc_config.get('NC_ENABLED', True):
        return False, "Nextcloud disabled"
        
    base_dav = nc_config['NC_URL']
    user = nc_config['NC_USER']
    password = nc_config['NC_PASS']
    base_remote_path = nc_config['NC_REMOTE_PATH']
    
    if not remote_name:
        remote_name = os.path.basename(local_path)
        
    # Normalize: strip slashes and join with a single slash
    base_remote_path = base_remote_path.strip('/')
    remote_subfolder = remote_subfolder.strip('/')
    
    if remote_subfolder:
        full_rel_dir = f"{base_remote_path}/{remote_subfolder}"
    else:
        full_rel_dir = base_remote_path
        
    full_rel_dir = full_rel_dir.replace('\\', '/')
    
    # Ensure directory exists
    success, msg = nc_mkcol_recursive(base_dav, full_rel_dir, user, password)
    if not success:
        return False, f"Folders fail ({msg})"
        
    # Upload file
    return nc_put_file(base_dav, full_rel_dir, local_path, remote_name, user, password)

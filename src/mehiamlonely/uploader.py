import asyncio
import httpx
import json
from pathlib import Path

async def upload_data(server_url, data, pdf_paths):
    async with httpx.AsyncClient() as client:
        json_data = json.dumps(data).encode()
        files = [("data", ("data.json", json_data, "application/json"))]
        
        # Add PDF files if they exist
        pdf_file_handles = []
        for pdf_path in pdf_paths:
            if Path(pdf_path).exists():
                pdf_file = open(pdf_path, "rb")
                pdf_file_handles.append(pdf_file)
                files.append(("pdfs", (Path(pdf_path).name, pdf_file, "application/pdf")))
        
        try:
            response = await client.post(f"{server_url}/api/extract", files=files)
            
            # Log detailed response information for debugging
            if response.status_code != 200:
                print(f"Upload failed with status {response.status_code}: {response.text}")
            else:
                try:
                    response_data = response.json()
                    print(f"Upload successful: {response_data}")
                except:
                    print(f"Upload successful: {response.text if response.content else 'No response body'}")
                    
            return response.status_code == 200
        finally:
            # Close file handles
            for pdf_file in pdf_file_handles:
                pdf_file.close()

async def upload_all(server_url, profiles_data):
    tasks = [upload_data(server_url, data, paths) for data, paths in profiles_data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    failed = [r for r in results if isinstance(r, Exception) or not r]
    if failed:
        print(f"Upload failed for {len(failed)} items.")
    else:
        print("All uploads successful.")
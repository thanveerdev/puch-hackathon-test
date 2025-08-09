#!/usr/bin/env python3
"""
Simple MCP Server Testing Script
Tests basic connectivity and data types using direct HTTP requests
"""

import asyncio
import httpx
import json
import base64
from io import BytesIO
from PIL import Image

# Configuration
SERVER_URL = "http://localhost:8086"
AUTH_TOKEN = "hackdevtoken_12345"

class SimpleMCPTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)
        
    async def test_basic_connectivity(self):
        """Test basic server connectivity"""
        print("🔗 Testing basic connectivity...")
        
        try:
            # Test root endpoint
            response = await self.client.get(f"{SERVER_URL}/")
            print(f"  GET /: Status {response.status_code}")
            
            # Test MCP endpoint
            response = await self.client.get(f"{SERVER_URL}/mcp/")
            print(f"  GET /mcp/: Status {response.status_code}")
            
            # Test with authentication
            headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
            response = await self.client.get(f"{SERVER_URL}/mcp/", headers=headers)
            print(f"  GET /mcp/ (with auth): Status {response.status_code}")
            
            return True
        except Exception as e:
            print(f"  ❌ Connection failed: {e}")
            return False
    
    async def test_mcp_list_tools(self):
        """Test listing available tools"""
        print("\n🛠️ Testing tool discovery...")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        
        headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        try:
            response = await self.client.post(f"{SERVER_URL}/mcp/", 
                                            json=payload, 
                                            headers=headers)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if "result" in data and "tools" in data["result"]:
                    tools = data["result"]["tools"]
                    print(f"  ✅ Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"    - {tool['name']}: {tool.get('description', 'No description')[:60]}...")
                    return tools
                else:
                    print(f"  ❌ Unexpected response format: {data}")
            else:
                print(f"  ❌ Failed with response: {response.text}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        return []
    
    async def test_validate_tool(self):
        """Test the validate tool specifically"""
        print("\n✅ Testing validate tool...")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "validate",
                "arguments": {}
            }
        }
        
        headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        try:
            response = await self.client.post(f"{SERVER_URL}/mcp/", 
                                            json=payload, 
                                            headers=headers)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    result = data["result"]
                    print(f"  ✅ Validate returned: {result}")
                    return True
                else:
                    print(f"  ❌ No result in response: {data}")
            else:
                print(f"  ❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        return False
    
    async def test_job_finder_variations(self):
        """Test job_finder with different parameters"""
        print("\n🔍 Testing job_finder variations...")
        
        test_cases = [
            {
                "name": "Basic job search",
                "params": {"user_goal": "python developer jobs in bangalore"}
            },
            {
                "name": "Job description analysis", 
                "params": {
                    "user_goal": "analyze this job",
                    "job_description": "We are hiring a Python developer with Django experience."
                }
            },
            {
                "name": "URL fetching",
                "params": {
                    "user_goal": "fetch job details",
                    "job_url": "https://httpbin.org/html"
                }
            },
            {
                "name": "Keywords test",
                "params": {"user_goal": "find software engineering positions"}
            }
        ]
        
        success_count = 0
        
        for i, test_case in enumerate(test_cases):
            print(f"  Test {i+1}: {test_case['name']}")
            
            payload = {
                "jsonrpc": "2.0",
                "id": i + 10,
                "method": "tools/call", 
                "params": {
                    "name": "job_finder",
                    "arguments": test_case["params"]
                }
            }
            
            headers = {
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            }
            
            try:
                response = await self.client.post(f"{SERVER_URL}/mcp/", 
                                                json=payload, 
                                                headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        result = data["result"]
                        print(f"    ✅ Success: {str(result)[:100]}...")
                        success_count += 1
                    else:
                        print(f"    ❌ No result: {data}")
                else:
                    print(f"    ❌ Status {response.status_code}: {response.text[:100]}...")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        print(f"  📊 Success rate: {success_count}/{len(test_cases)}")
        return success_count > 0
    
    def create_test_image(self):
        """Create a simple test image"""
        img = Image.new('RGB', (50, 50), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    async def test_image_processing(self):
        """Test image processing tool"""
        print("\n🖼️ Testing image processing...")
        
        test_image = self.create_test_image()
        
        payload = {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "make_img_black_and_white", 
                "arguments": {
                    "puch_image_data": test_image
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        try:
            response = await self.client.post(f"{SERVER_URL}/mcp/", 
                                            json=payload, 
                                            headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    result = data["result"]
                    print(f"  ✅ Image processed successfully")
                    if isinstance(result, list) and len(result) > 0:
                        print(f"    Returned {len(result)} content items")
                        for item in result:
                            if isinstance(item, dict) and item.get("type") == "image":
                                print(f"    - Image: {item.get('mimeType', 'unknown')} format")
                    return True
                else:
                    print(f"  ❌ No result: {data}")
            else:
                print(f"  ❌ Status {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        return False
    
    async def run_all_tests(self):
        """Run all tests and provide summary"""
        print("🧪 Simple MCP Server Testing")
        print("=" * 40)
        
        results = {}
        
        # Test 1: Basic connectivity
        results["connectivity"] = await self.test_basic_connectivity()
        
        if not results["connectivity"]:
            print("\n❌ Basic connectivity failed. Make sure server is running.")
            return results
        
        # Test 2: Tool discovery
        tools = await self.test_mcp_list_tools()
        results["tool_discovery"] = len(tools) > 0
        
        # Test 3: Validate tool
        results["validate"] = await self.test_validate_tool()
        
        # Test 4: Job finder
        results["job_finder"] = await self.test_job_finder_variations()
        
        # Test 5: Image processing
        results["image_processing"] = await self.test_image_processing()
        
        # Summary
        print("\n" + "=" * 40)
        print("📊 TEST SUMMARY")
        print("=" * 40)
        
        success_count = sum(1 for result in results.values() if result)
        total_count = len(results)
        
        for test_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {test_name.replace('_', ' ').title()}")
        
        print(f"\n📈 Overall success rate: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        
        if all(results.values()):
            print("🎉 All tests passed! Your MCP server is working correctly.")
        else:
            print("⚠️ Some tests failed. Check the output above for details.")
        
        return results
    
    async def close(self):
        await self.client.aclose()

async def main():
    print("🚀 Starting Simple MCP Server Tests")
    print(f"🎯 Target: {SERVER_URL}")
    print(f"🔐 Auth: {AUTH_TOKEN}")
    
    tester = SimpleMCPTester()
    
    try:
        results = await tester.run_all_tests()
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
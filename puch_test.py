#!/usr/bin/env python3
"""
Puch.ai Style MCP Connection Test
Tests what data types work by mimicking how Puch.ai actually connects
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

class PuchStyleTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)
        self.session_id = None
        
    async def connect_session(self):
        """Establish a session like Puch.ai does"""
        print("🔗 Establishing MCP session...")
        
        # Initialize request
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": False},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "puch-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json", 
            "Accept": "application/json, text/event-stream",
            "User-Agent": "Puch-Test-Client/1.0"
        }
        
        try:
            response = await self.client.post(f"{SERVER_URL}/mcp/", 
                                            json=payload, 
                                            headers=headers)
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Session initialized successfully")
                self.session_id = "test-session-123"
                return True
            else:
                print(f"  Response: {response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    async def test_validate_directly(self):
        """Test validate tool directly as Puch.ai would"""
        print("\n✅ Testing validate tool (Puch.ai authentication)...")
        
        # This mimics what Puch.ai sends
        url = f"{SERVER_URL}/validate"
        headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            # Try POST request (most common)
            response = await self.client.post(url, json={}, headers=headers)
            print(f"  POST /validate: Status {response.status_code}")
            
            if response.status_code == 200:
                result = response.text
                print(f"  ✅ Validate returned: {result}")
                return result
            
            # Try GET request
            response = await self.client.get(url, headers=headers)
            print(f"  GET /validate: Status {response.status_code}")
            
            if response.status_code == 200:
                result = response.text
                print(f"  ✅ Validate returned: {result}")
                return result
                
            print(f"  Response: {response.text[:100]}...")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        return None
    
    async def test_raw_endpoints(self):
        """Test direct tool endpoints"""
        print("\n🛠️ Testing direct tool endpoints...")
        
        tools_to_test = ["validate", "job_finder", "make_img_black_and_white"]
        results = {}
        
        for tool in tools_to_test:
            print(f"  Testing /{tool}...")
            
            url = f"{SERVER_URL}/{tool}"
            headers = {
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Test different request types
            for method in ["GET", "POST"]:
                try:
                    if method == "GET":
                        response = await self.client.get(url, headers=headers)
                    else:
                        test_data = {}
                        if tool == "job_finder":
                            test_data = {"user_goal": "test jobs"}
                        elif tool == "make_img_black_and_white":
                            test_data = {"puch_image_data": self.create_test_image()}
                        
                        response = await self.client.post(url, json=test_data, headers=headers)
                    
                    print(f"    {method}: Status {response.status_code}")
                    
                    if response.status_code == 200:
                        results[f"{tool}_{method.lower()}"] = {
                            "success": True,
                            "response": response.text[:100] + "..." if len(response.text) > 100 else response.text
                        }
                    else:
                        print(f"      Response: {response.text[:50]}...")
                        
                except Exception as e:
                    print(f"    {method}: Error - {e}")
        
        return results
    
    async def test_tool_parameters(self):
        """Test what parameters each tool accepts"""
        print("\n📝 Testing tool parameter variations...")
        
        # Test job_finder with different parameter combinations
        job_finder_tests = [
            {"user_goal": "python jobs"},
            {"user_goal": "find software engineer positions"},
            {"user_goal": "analyze job", "job_description": "Python developer needed"},
            {"user_goal": "fetch", "job_url": "https://httpbin.org/json"},
            {"user_goal": "search", "raw": True},
            {"user_goal": "jobs in kerala", "job_description": "Full stack developer", "raw": False}
        ]
        
        results = {}
        
        for i, params in enumerate(job_finder_tests):
            print(f"  Test {i+1}: job_finder with {list(params.keys())}")
            
            url = f"{SERVER_URL}/job_finder"
            headers = {
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            }
            
            try:
                response = await self.client.post(url, json=params, headers=headers)
                success = response.status_code == 200
                
                if success:
                    print(f"    ✅ Success: {response.text[:60]}...")
                    results[f"job_finder_test_{i+1}"] = True
                else:
                    print(f"    ❌ Failed ({response.status_code}): {response.text[:60]}...")
                    results[f"job_finder_test_{i+1}"] = False
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
                results[f"job_finder_test_{i+1}"] = False
        
        return results
    
    def create_test_image(self):
        """Create a simple test image"""
        img = Image.new('RGB', (10, 10), color='red')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    async def test_image_data_types(self):
        """Test different image data formats"""
        print("\n🖼️ Testing image data formats...")
        
        # Create different image formats
        test_images = {
            "small_png": self.create_test_image(),
            "invalid_base64": "not-valid-base64-data", 
            "empty_string": "",
            "text_as_image": base64.b64encode(b"this is not an image").decode('utf-8')
        }
        
        results = {}
        
        for test_name, image_data in test_images.items():
            print(f"  Testing {test_name}...")
            
            url = f"{SERVER_URL}/make_img_black_and_white"
            headers = {
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            }
            
            params = {"puch_image_data": image_data}
            
            try:
                response = await self.client.post(url, json=params, headers=headers)
                success = response.status_code == 200
                
                if success:
                    print(f"    ✅ Success")
                    results[test_name] = True
                else:
                    print(f"    ❌ Failed ({response.status_code})")
                    results[test_name] = False
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
                results[test_name] = False
        
        return results
    
    async def run_comprehensive_test(self):
        """Run all tests and summarize findings"""
        print("🧪 Puch.ai Style MCP Testing")
        print("=" * 40)
        
        all_results = {}
        
        # Test 1: Basic validation 
        validate_result = await self.test_validate_directly()
        all_results["validate"] = validate_result is not None
        
        # Test 2: Direct endpoints
        print("\nTesting direct tool endpoints...")
        endpoint_results = await self.test_raw_endpoints()
        all_results.update(endpoint_results)
        
        # Test 3: Parameter variations
        param_results = await self.test_tool_parameters()
        all_results.update(param_results)
        
        # Test 4: Image data types
        image_results = await self.test_image_data_types()
        all_results.update(image_results)
        
        # Summary
        print("\n" + "=" * 40)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 40)
        
        success_count = sum(1 for result in all_results.values() if result)
        total_count = len(all_results)
        
        print(f"✅ Successful tests: {success_count}")
        print(f"❌ Failed tests: {total_count - success_count}")
        print(f"📈 Success rate: {success_count/total_count*100:.1f}%")
        
        # Group results by category
        categories = {
            "Authentication": [k for k in all_results.keys() if "validate" in k],
            "Job Finder": [k for k in all_results.keys() if "job_finder" in k], 
            "Image Processing": [k for k in all_results.keys() if any(img in k for img in ["image", "png", "base64"])]
        }
        
        for category, tests in categories.items():
            if tests:
                category_success = sum(1 for test in tests if all_results.get(test, False))
                print(f"\n📂 {category}: {category_success}/{len(tests)} passed")
                for test in tests:
                    status = "✅" if all_results.get(test, False) else "❌"
                    print(f"  {status} {test}")
        
        # What works summary
        working_features = []
        if all_results.get("validate", False):
            working_features.append("Phone number validation (918086165065)")
        
        job_finder_working = any(all_results.get(k, False) for k in all_results.keys() if "job_finder" in k)
        if job_finder_working:
            working_features.append("Job search and analysis")
        
        image_working = any(all_results.get(k, False) for k in all_results.keys() if "image" in k or "png" in k)
        if image_working:
            working_features.append("Image processing (black & white conversion)")
        
        if working_features:
            print(f"\n🎉 CONFIRMED WORKING FEATURES:")
            for feature in working_features:
                print(f"  ✅ {feature}")
        
        return all_results
    
    async def close(self):
        await self.client.aclose()

async def main():
    print("🚀 Starting Puch.ai Style MCP Testing")
    print(f"🎯 Target: {SERVER_URL}")
    
    tester = PuchStyleTester()
    
    try:
        results = await tester.run_comprehensive_test()
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
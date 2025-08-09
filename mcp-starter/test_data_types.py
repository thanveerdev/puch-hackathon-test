#!/usr/bin/env python3
"""
MCP Server Data Type Testing Script
Tests various data types and parameters that can be sent to the MCP server
"""

import asyncio
import json
import base64
import httpx
from typing import Any, Dict, List
from io import BytesIO
from PIL import Image
import os

# Test configuration
MCP_SERVER_URL = "http://localhost:8086/mcp/"
AUTH_TOKEN = "hackdevtoken_12345"

class MCPTester:
    def __init__(self, server_url: str, auth_token: str):
        self.server_url = server_url
        self.auth_token = auth_token
        self.client = httpx.AsyncClient(timeout=30)
        
    async def test_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict:
        """Test a tool call with given parameters"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": parameters
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(self.server_url, 
                                            json=payload, 
                                            headers=headers)
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "error": None
            }
        except Exception as e:
            return {
                "status_code": None,
                "success": False,
                "response": None,
                "error": str(e)
            }

    def create_test_image(self) -> str:
        """Create a test image and return as base64"""
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()
        return base64.b64encode(img_data).decode('utf-8')

    async def run_all_tests(self):
        """Run comprehensive tests on all tools and data types"""
        print("🧪 MCP Server Data Type Testing")
        print("=" * 50)
        
        test_results = []
        
        # Test 1: Basic validate tool
        print("\n1️⃣ Testing validate tool (required by Puch.ai)")
        result = await self.test_tool_call("validate", {})
        test_results.append(("validate_basic", result))
        self.print_test_result("validate", {}, result)
        
        # Test 2: job_finder with different parameter combinations
        print("\n2️⃣ Testing job_finder tool variations")
        
        # 2a: Basic text query
        params = {"user_goal": "python developer jobs in bangalore"}
        result = await self.test_tool_call("job_finder", params)
        test_results.append(("job_finder_text_query", result))
        self.print_test_result("job_finder", params, result)
        
        # 2b: Job description analysis
        params = {
            "user_goal": "analyze this job",
            "job_description": "We are looking for a Python developer with 3+ years experience in Django and REST APIs. Location: Remote. Salary: $80k-100k."
        }
        result = await self.test_tool_call("job_finder", params)
        test_results.append(("job_finder_description", result))
        self.print_test_result("job_finder", params, result)
        
        # 2c: URL fetching
        params = {
            "user_goal": "fetch job details",
            "job_url": "https://httpbin.org/html"  # Safe test URL
        }
        result = await self.test_tool_call("job_finder", params)
        test_results.append(("job_finder_url", result))
        self.print_test_result("job_finder", params, result)
        
        # 2d: URL with raw flag
        params = {
            "user_goal": "fetch raw content",
            "job_url": "https://httpbin.org/json",
            "raw": True
        }
        result = await self.test_tool_call("job_finder", params)
        test_results.append(("job_finder_url_raw", result))
        self.print_test_result("job_finder", params, result)
        
        # Test 3: Image processing
        print("\n3️⃣ Testing image processing tool")
        
        # 3a: Basic image conversion
        test_image = self.create_test_image()
        params = {"puch_image_data": test_image}
        result = await self.test_tool_call("make_img_black_and_white", params)
        test_results.append(("image_processing_basic", result))
        self.print_test_result("make_img_black_and_white", {"puch_image_data": "base64_image..."}, result)
        
        # Test 4: Edge cases and invalid data
        print("\n4️⃣ Testing edge cases and invalid data")
        
        # 4a: Empty parameters
        result = await self.test_tool_call("job_finder", {})
        test_results.append(("job_finder_empty", result))
        self.print_test_result("job_finder", {}, result)
        
        # 4b: Invalid URL
        params = {
            "user_goal": "test invalid url",
            "job_url": "not-a-valid-url"
        }
        result = await self.test_tool_call("job_finder", params)
        test_results.append(("job_finder_invalid_url", result))
        self.print_test_result("job_finder", params, result)
        
        # 4c: Invalid base64 image
        params = {"puch_image_data": "invalid-base64-data"}
        result = await self.test_tool_call("make_img_black_and_white", params)
        test_results.append(("image_processing_invalid", result))
        self.print_test_result("make_img_black_and_white", params, result)
        
        # 4d: Non-existent tool
        result = await self.test_tool_call("non_existent_tool", {"param": "value"})
        test_results.append(("non_existent_tool", result))
        self.print_test_result("non_existent_tool", {"param": "value"}, result)
        
        # Test 5: Data type variations
        print("\n5️⃣ Testing various data types")
        
        # 5a: Very long text
        long_text = "a" * 10000
        params = {"user_goal": long_text}
        result = await self.test_tool_call("job_finder", params)
        test_results.append(("job_finder_long_text", result))
        self.print_test_result("job_finder", {"user_goal": f"very_long_text({len(long_text)}_chars)"}, result)
        
        # 5b: Special characters
        params = {"user_goal": "jobs with special chars: !@#$%^&*()çñü🚀"}
        result = await self.test_tool_call("job_finder", params)
        test_results.append(("job_finder_special_chars", result))
        self.print_test_result("job_finder", params, result)
        
        # 5c: Multiple keywords for search trigger
        for keyword in ["job", "career", "work", "employment", "position", "opening", "vacancy"]:
            params = {"user_goal": f"looking for {keyword} opportunities"}
            result = await self.test_tool_call("job_finder", params)
            test_results.append((f"job_finder_keyword_{keyword}", result))
            self.print_test_result("job_finder", params, result, brief=True)
        
        # Generate summary report
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY REPORT")
        print("=" * 50)
        
        success_count = sum(1 for _, result in test_results if result["success"])
        total_count = len(test_results)
        
        print(f"✅ Successful tests: {success_count}/{total_count}")
        print(f"❌ Failed tests: {total_count - success_count}/{total_count}")
        print(f"📈 Success rate: {success_count/total_count*100:.1f}%")
        
        print("\n🔍 FAILED TESTS:")
        for test_name, result in test_results:
            if not result["success"]:
                print(f"  ❌ {test_name}: {result.get('error', 'Unknown error')}")
        
        print("\n✅ SUCCESSFUL DATA TYPES:")
        successful_types = set()
        for test_name, result in test_results:
            if result["success"]:
                if "text_query" in test_name or "special_chars" in test_name:
                    successful_types.add("String/Text data")
                elif "url" in test_name:
                    successful_types.add("URL data")
                elif "description" in test_name:
                    successful_types.add("Long text descriptions")
                elif "image" in test_name:
                    successful_types.add("Base64 image data")
                elif "validate" in test_name:
                    successful_types.add("Empty parameters (validate tool)")
        
        for data_type in sorted(successful_types):
            print(f"  ✅ {data_type}")
        
        return test_results

    def print_test_result(self, tool_name: str, params: Dict, result: Dict, brief: bool = False):
        """Print formatted test result"""
        status = "✅" if result["success"] else "❌"
        if brief:
            print(f"    {status} {tool_name} - {list(params.values())[0][:30]}...")
            return
            
        print(f"  {status} Tool: {tool_name}")
        print(f"     Params: {json.dumps(params, indent=6)[:100]}{'...' if len(str(params)) > 100 else ''}")
        
        if result["success"]:
            print(f"     Status: {result['status_code']} - SUCCESS")
            response_preview = str(result["response"])[:200] + "..." if len(str(result["response"])) > 200 else str(result["response"])
            print(f"     Response: {response_preview}")
        else:
            print(f"     Status: {result['status_code']} - FAILED")
            print(f"     Error: {result['error']}")
        print()

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

async def main():
    """Main test runner"""
    print("🚀 Starting MCP Server Data Type Tests")
    print(f"🔗 Testing server: {MCP_SERVER_URL}")
    print(f"🔑 Using token: {AUTH_TOKEN}")
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8086/")
            print(f"🟢 Server is running (status: {response.status_code})")
    except Exception as e:
        print(f"🔴 Server not accessible: {e}")
        print("❗ Make sure your MCP server is running on localhost:8086")
        return
    
    # Run tests
    tester = MCPTester(MCP_SERVER_URL, AUTH_TOKEN)
    
    try:
        results = await tester.run_all_tests()
        
        # Save detailed results to file
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: test_results.json")
        
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
#!/bin/bash

# MCP Server Data Type Testing Script
echo "🧪 MCP Server Data Type Testing"
echo "================================"

# Check if MCP server is running
echo "🔍 Checking if MCP server is running..."
if ! curl -s http://localhost:8086/ > /dev/null; then
    echo "❌ MCP server not running on localhost:8086"
    echo "📝 Start your server first:"
    echo "   cd mcp-starter"
    echo "   uv run python mcp-bearer-token/mcp_starter.py"
    exit 1
fi

echo "✅ MCP server is running"

# Install test dependencies if needed
echo "📦 Installing test dependencies..."
if command -v uv &> /dev/null; then
    uv add httpx pillow pytest pytest-asyncio
else
    pip install -r requirements-test.txt
fi

# Run the comprehensive test
echo "🚀 Running comprehensive data type tests..."
if command -v uv &> /dev/null; then
    uv run python test_data_types.py
else
    python test_data_types.py
fi

echo ""
echo "✨ Testing complete! Check test_results.json for detailed results."
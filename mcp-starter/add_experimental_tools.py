#!/usr/bin/env python3
"""
Script to add experimental data discovery tools to your MCP server
Run this to automatically add the experimental tools to your server
"""

def add_experimental_tools():
    """Add experimental tools to mcp_starter.py"""
    
    # Read the experimental tools
    with open('experimental_tools.py', 'r') as f:
        experimental_code = f.read()
    
    # Read the current server code
    with open('mcp-bearer-token/mcp_starter.py', 'r') as f:
        current_code = f.read()
    
    # Extract just the tool definitions (skip the imports and middleware)
    tools_start = experimental_code.find('@mcp.tool')
    tools_code = experimental_code[tools_start:]
    
    # Remove the middleware part and imports
    tools_code = tools_code.split('# --- Request Logger Function ---')[0]
    
    # Find where to insert the new tools (before the main function)
    insert_point = current_code.find('# --- Run MCP Server ---')
    
    if insert_point == -1:
        insert_point = current_code.find('async def main():')
    
    if insert_point == -1:
        insert_point = current_code.find('if __name__ == "__main__":')
    
    # Insert the experimental tools
    new_code = (
        current_code[:insert_point] + 
        "\n# --- Experimental Data Discovery Tools ---\n\n" +
        tools_code + "\n\n" +
        current_code[insert_point:]
    )
    
    # Save the updated code
    with open('mcp-bearer-token/mcp_starter_with_experiments.py', 'w') as f:
        f.write(new_code)
    
    print("✅ Created mcp_starter_with_experiments.py")
    print("🔧 Experimental tools added:")
    print("   - data_type_explorer: Tests all Python data types")
    print("   - flexible_input_tester: Accepts any parameters")
    print("   - json_schema_tester: Tests complex JSON structures")
    print("   - file_data_tester: Tests file upload capabilities")
    print("   - context_data_tester: Tests contextual data")
    print()
    print("📋 To use:")
    print("   1. Stop your current server (Ctrl+C)")
    print("   2. Run: uv run python mcp-bearer-token/mcp_starter_with_experiments.py")
    print("   3. Test these new tools in Puch.ai")
    print("   4. Check puch_data_log.json for detailed analysis")

if __name__ == "__main__":
    add_experimental_tools()
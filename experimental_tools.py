#!/usr/bin/env python3
"""
Experimental tools to discover what data types Puch.ai can send
Add these to your mcp_starter.py to explore Puch.ai's capabilities
"""

import json
import inspect
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from mcp.types import TextContent, ImageContent, AudioContent
from mcp import McpError, ErrorData
from mcp.types import INTERNAL_ERROR

# --- Data Type Exploration Tools ---

@mcp.tool
def handler(req):
    if req.message.payload == "roast_voice":
        return {
            "messages": [
                AudioContent(mediaUrl="https://example.com/roast.mp3")
            ]
        }


@mcp.tool
async def data_type_explorer(
    # Accept every possible data type to see what Puch sends
    any_param: Any = None,
    text_param: str = "",
    number_param: float = 0.0,
    int_param: int = 0,
    bool_param: bool = False,
    list_param: List[Any] = None,
    dict_param: Dict[str, Any] = None,
    optional_param: Optional[str] = None,
    union_param: Union[str, int, float] = None,
) -> str:
    """
    Universal data type explorer - accepts any data type to see what Puch.ai sends
    """
    
    # Log all received parameters
    params_received = {
        "any_param": {"value": any_param, "type": type(any_param).__name__},
        "text_param": {"value": text_param, "type": type(text_param).__name__},
        "number_param": {"value": number_param, "type": type(number_param).__name__},
        "int_param": {"value": int_param, "type": type(int_param).__name__},
        "bool_param": {"value": bool_param, "type": type(bool_param).__name__},
        "list_param": {"value": list_param, "type": type(list_param).__name__ if list_param else "None"},
        "dict_param": {"value": dict_param, "type": type(dict_param).__name__ if dict_param else "None"},
        "optional_param": {"value": optional_param, "type": type(optional_param).__name__ if optional_param else "None"},
        "union_param": {"value": union_param, "type": type(union_param).__name__},
    }
    
    # Save to log file for analysis
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": "data_type_explorer",
        "parameters_received": params_received,
        "caller": "puch.ai"
    }
    
    with open("puch_data_log.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    # Return detailed analysis
    analysis = "🔍 **Data Type Analysis**\n\n"
    for param_name, info in params_received.items():
        if info["value"] is not None and info["value"] != "" and info["value"] != 0 and info["value"] != False:
            analysis += f"✅ **{param_name}**: {info['type']} = {repr(info['value'])}\n"
    
    analysis += f"\n📊 Total non-empty parameters: {sum(1 for p in params_received.values() if p['value'] not in [None, '', 0, False, []])}"
    analysis += f"\n📝 Full log saved to puch_data_log.json"
    
    return analysis

@mcp.tool 
async def flexible_input_tester(
    **kwargs: Any  # Accept any keyword arguments
) -> str:
    """
    Accepts any number of parameters with any names to see what Puch.ai sends
    """
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": "flexible_input_tester", 
        "kwargs_received": {k: {"value": v, "type": type(v).__name__} for k, v in kwargs.items()},
        "total_params": len(kwargs)
    }
    
    with open("puch_data_log.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    if not kwargs:
        return "🤔 No parameters received. Try sending some data!"
    
    result = "🎯 **Flexible Input Analysis**\n\n"
    
    for key, value in kwargs.items():
        result += f"**{key}**: {type(value).__name__} = {repr(value)}\n"
    
    # Analyze data patterns
    data_types = [type(v).__name__ for v in kwargs.values()]
    result += f"\n📊 **Data Type Summary:**\n"
    for dtype in set(data_types):
        count = data_types.count(dtype)
        result += f"- {dtype}: {count} parameter(s)\n"
    
    return result

@mcp.tool
async def json_schema_tester(
    structured_data: Dict[str, Any] = Field(default_factory=dict, description="Send any structured JSON data"),
    array_data: List[Any] = Field(default_factory=list, description="Send any array/list data"),
    nested_object: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Send nested object data"),
) -> str:
    """
    Tests complex JSON structures and nested data
    """
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": "json_schema_tester",
        "structured_data": structured_data,
        "array_data": array_data, 
        "nested_object": nested_object
    }
    
    with open("puch_data_log.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    analysis = "🏗️ **JSON Structure Analysis**\n\n"
    
    if structured_data:
        analysis += f"📦 **Structured Data**: {len(structured_data)} keys\n"
        for k, v in structured_data.items():
            analysis += f"  - {k}: {type(v).__name__} = {repr(v)[:50]}...\n"
    
    if array_data:
        analysis += f"\n📋 **Array Data**: {len(array_data)} items\n"
        for i, item in enumerate(array_data[:5]):  # Show first 5
            analysis += f"  [{i}]: {type(item).__name__} = {repr(item)[:50]}...\n"
    
    if nested_object:
        analysis += f"\n🔗 **Nested Objects**: {len(nested_object)} top-level keys\n"
        for k, v in nested_object.items():
            if isinstance(v, dict):
                analysis += f"  - {k}: Dict with {len(v)} sub-keys\n"
            else:
                analysis += f"  - {k}: {type(v).__name__}\n"
    
    return analysis

@mcp.tool
async def file_data_tester(
    file_content: str = Field(description="Base64 encoded file content"),
    file_type: str = Field(default="unknown", description="File type/extension"),
    file_name: str = Field(default="", description="Original filename"),
    file_size: int = Field(default=0, description="File size in bytes"),
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
) -> str:
    """
    Tests file upload capabilities and metadata
    """
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": "file_data_tester",
        "file_type": file_type,
        "file_name": file_name,
        "file_size": file_size,
        "content_length": len(file_content) if file_content else 0,
        "has_metadata": bool(metadata),
        "metadata_keys": list(metadata.keys()) if metadata else []
    }
    
    with open("puch_data_log.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    result = "📁 **File Data Analysis**\n\n"
    
    if file_content:
        result += f"📄 **Content**: {len(file_content)} characters (Base64)\n"
        
        # Try to detect file type from content
        if file_content.startswith("data:"):
            data_uri_part = file_content.split(",")[0]
            result += f"🔍 **Data URI detected**: {data_uri_part}\n"
        elif file_content.startswith("/9j/"):
            result += f"🖼️ **JPEG image detected**\n"
        elif file_content.startswith("iVBOR"):
            result += f"🖼️ **PNG image detected**\n"
        elif file_content.startswith("JVBERi"):
            result += f"📄 **PDF document detected**\n"
    
    if file_name:
        result += f"📝 **Filename**: {file_name}\n"
    
    if file_type and file_type != "unknown":
        result += f"🏷️ **File Type**: {file_type}\n"
    
    if file_size > 0:
        result += f"📏 **Size**: {file_size} bytes\n"
    
    if metadata:
        result += f"📊 **Metadata**: {len(metadata)} fields\n"
        for k, v in metadata.items():
            result += f"  - {k}: {type(v).__name__} = {repr(v)[:50]}...\n"
    
    return result

@mcp.tool
async def context_data_tester(
    user_message: str = Field(description="The user's original message"),
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Previous messages"),
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences/settings"),
    session_data: Dict[str, Any] = Field(default_factory=dict, description="Session information"),
    location_data: Dict[str, Any] = Field(default_factory=dict, description="User location information"),
    timestamp: str = Field(default="", description="Request timestamp"),
) -> str:
    """
    Tests contextual data that Puch.ai might send
    """
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": "context_data_tester",
        "user_message": user_message,
        "has_history": len(conversation_history) > 0,
        "history_length": len(conversation_history),
        "has_preferences": len(user_preferences) > 0,
        "has_session_data": len(session_data) > 0,
        "has_location": len(location_data) > 0,
        "request_timestamp": timestamp
    }
    
    with open("puch_data_log.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    result = "🌐 **Context Data Analysis**\n\n"
    
    if user_message:
        result += f"💬 **User Message**: {repr(user_message)}\n"
    
    if conversation_history:
        result += f"📚 **Conversation History**: {len(conversation_history)} messages\n"
        for i, msg in enumerate(conversation_history[-3:]):  # Show last 3
            result += f"  [{i}]: {msg.get('role', 'unknown')} - {str(msg.get('content', ''))[:50]}...\n"
    
    if user_preferences:
        result += f"⚙️ **User Preferences**: {len(user_preferences)} settings\n"
        for k, v in user_preferences.items():
            result += f"  - {k}: {repr(v)}\n"
    
    if session_data:
        result += f"🔗 **Session Data**: {len(session_data)} fields\n"
        for k, v in session_data.items():
            result += f"  - {k}: {type(v).__name__} = {repr(v)[:50]}...\n"
    
    if location_data:
        result += f"📍 **Location Data**: {len(location_data)} fields\n"
        for k, v in location_data.items():
            result += f"  - {k}: {repr(v)}\n"
    
    if timestamp:
        result += f"⏰ **Timestamp**: {timestamp}\n"
    
    return result

# --- Request Logger Function ---
def log_all_requests():
    """Add this to your main server to log all incoming requests"""
    
    # This would go in your FastMCP app setup
    @mcp.middleware
    async def request_logger(request, call_next):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": await request.body() if hasattr(request, 'body') else None
        }
        
        with open("all_requests_log.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return await call_next(request)
    
# @mcp.tool
# def handler(req):
#     return {
#         "messages": [
#             {
#                 "type": "text",
#                 "text": "Here’s your audio message 🔊"
#             },
#             {
#                 "type": "audio",
#                 "mediaUrl": "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav"
#             }
#         ]
#     }



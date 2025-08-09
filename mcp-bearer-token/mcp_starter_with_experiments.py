import asyncio
from typing import Annotated
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field, AnyUrl

import markdownify
import httpx
import readabilipy

# --- Load environment variables ---
load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# --- Auth Provider ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="puch-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

# --- Rich Tool Description model ---
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# --- Fetch Utility Class ---
class Fetch:
    USER_AGENT = "Puch/1.0 (Autonomous)"

    @classmethod
    async def fetch_url(
        cls,
        url: str,
        user_agent: str,
        force_raw: bool = False,
    ) -> tuple[str, str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": user_agent},
                    timeout=30,
                )
            except httpx.HTTPError as e:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"))

            if response.status_code >= 400:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url} - status code {response.status_code}"))

            page_raw = response.text

        content_type = response.headers.get("content-type", "")
        is_page_html = "text/html" in content_type

        if is_page_html and not force_raw:
            return cls.extract_content_from_html(page_raw), ""

        return (
            page_raw,
            f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
        )

    @staticmethod
    def extract_content_from_html(html: str) -> str:
        """Extract and convert HTML content to Markdown format."""
        ret = readabilipy.simple_json.simple_json_from_html_string(html, use_readability=True)
        if not ret or not ret.get("content"):
            return "<error>Page failed to be simplified from HTML</error>"
        content = markdownify.markdownify(ret["content"], heading_style=markdownify.ATX)
        return content

    @staticmethod
    async def google_search_links(query: str, num_results: int = 5) -> list[str]:
        """
        Perform a scoped DuckDuckGo search and return a list of job posting URLs.
        (Using DuckDuckGo because Google blocks most programmatic scraping.)
        """
        ddg_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        links = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(ddg_url, headers={"User-Agent": Fetch.USER_AGENT})
            if resp.status_code != 200:
                return ["<error>Failed to perform search.</error>"]

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", class_="result__a", href=True):
            href = a["href"]
            if "http" in href:
                links.append(href)
            if len(links) >= num_results:
                break

        return links or ["<error>No results found.</error>"]

# --- MCP Server Setup ---
mcp = FastMCP(
    "Job Finder MCP Server",
    auth=SimpleBearerAuthProvider(TOKEN),
)

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    return MY_NUMBER

# --- Tool: job_finder (now smart!) ---
JobFinderDescription = RichToolDescription(
    description="Smart job tool: analyze descriptions, fetch URLs, or search jobs based on free text.",
    use_when="Use this to evaluate job descriptions or search for jobs using freeform goals.",
    side_effects="Returns insights, fetched job descriptions, or relevant job links.",
)

@mcp.tool(description=JobFinderDescription.model_dump_json())
async def job_finder(
    user_goal: Annotated[str, Field(description="The user's goal (can be a description, intent, or freeform query)")],
    job_description: Annotated[str | None, Field(description="Full job description text, if available.")] = None,
    job_url: Annotated[AnyUrl | None, Field(description="A URL to fetch a job description from.")] = None,
    raw: Annotated[bool, Field(description="Return raw HTML content if True")] = False,
) -> str:
    """
    Handles multiple job discovery methods: direct description, URL fetch, or freeform search query.
    """
    if job_description:
        return (
            f"📝 **Job Description Analysis**\n\n"
            f"---\n{job_description.strip()}\n---\n\n"
            f"User Goal: **{user_goal}**\n\n"
            f"💡 Suggestions:\n- Tailor your resume.\n- Evaluate skill match.\n- Consider applying if relevant."
        )

    if job_url:
        content, _ = await Fetch.fetch_url(str(job_url), Fetch.USER_AGENT, force_raw=raw)
        return (
            f"🔗 **Fetched Job Posting from URL**: {job_url}\n\n"
            f"---\n{content.strip()}\n---\n\n"
            f"User Goal: **{user_goal}**"
        )

    # Default to search if no job_description or job_url provided
    search_keywords = ["job", "jobs", "career", "work", "employment", "position", "opening", "vacancy", "look for", "find"]
    if any(keyword in user_goal.lower() for keyword in search_keywords):
        links = await Fetch.google_search_links(user_goal)
        return (
            f"🔍 **Search Results for**: _{user_goal}_\n\n" +
            "\n".join(f"- {link}" for link in links)
        )

    raise McpError(ErrorData(code=INVALID_PARAMS, message="Please provide either a job description, a job URL, or a search query in user_goal."))


# Image inputs and sending images

MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION = RichToolDescription(
    description="Convert an image to black and white and save it.",
    use_when="Use this tool when the user provides an image URL and requests it to be converted to black and white.",
    side_effects="The image will be processed and saved in a black and white format.",
)

@mcp.tool(description=MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION.model_dump_json())
async def make_img_black_and_white(
    puch_image_data: Annotated[str, Field(description="Base64-encoded image data to convert to black and white")] = None,
) -> list[TextContent | ImageContent]:
    import base64
    import io

    from PIL import Image

    try:
        image_bytes = base64.b64decode(puch_image_data)
        image = Image.open(io.BytesIO(image_bytes))

        bw_image = image.convert("L")

        buf = io.BytesIO()
        bw_image.save(buf, format="PNG")
        bw_bytes = buf.getvalue()
        bw_base64 = base64.b64encode(bw_bytes).decode("utf-8")

        return [ImageContent(type="image", mimeType="image/png", data=bw_base64)]
    except Exception as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))


# --- Experimental Data Discovery Tools ---

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



# --- Run MCP Server ---
async def main():
    print("🚀 Starting MCP server on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())

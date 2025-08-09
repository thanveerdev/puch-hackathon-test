import asyncio
from typing import Annotated, Optional, Any
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, ImageContent, AudioContent, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field, AnyUrl

import markdownify
import httpx
import readabilipy
import json
import base64
import io
from datetime import datetime

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

# --- Simple data persistence for vendors and offers ---
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
VENDORS_DB_PATH = os.path.abspath(os.path.join(DATA_DIR, "vendors.json"))


def ensure_data_dir_exists() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_vendors_db() -> dict[str, Any]:
    ensure_data_dir_exists()
    if not os.path.exists(VENDORS_DB_PATH):
        return {"vendors": []}
    try:
        with open(VENDORS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"vendors": []}


def save_vendors_db(db: dict[str, Any]) -> None:
    ensure_data_dir_exists()
    tmp_path = VENDORS_DB_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, VENDORS_DB_PATH)


def slugify(text: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    s = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    while "--" in s:
        s = s.replace("--", "-")
    s = s.strip("-")
    return "".join(ch for ch in s if ch in allowed) or "shop"


class Vendor(BaseModel):
    vendor_id: str
    name: str
    slug: str
    pincode: str
    address: Optional[str] = None
    phone: Optional[str] = None
    tags: list[str] = []
    discount_text: Optional[str] = None
    menu_images_base64: list[str] = []
    created_at: str

# --- MCP Server Setup ---
mcp = FastMCP(
    "Job Finder MCP Server",
    auth=SimpleBearerAuthProvider(TOKEN),
)

# Request logging utility function
def log_tool_request(tool_name: str, **kwargs):
    """Log tool invocations for analysis"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "parameters": {k: {"value": v, "type": type(v).__name__} for k, v in kwargs.items()},
        "parameter_count": len(kwargs)
    }
    
    with open("prototype2_tool_log.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    log_tool_request("validate")
    return MY_NUMBER

# --- Tool: vendor_onboard ---
VendorOnboardDesc = RichToolDescription(
    description=(
        "Onboard a local vendor: capture name, pincode, optional address/phone/tags/discount, and one or more menu images (base64)."
    ),
    use_when=(
        "Use when a shop owner wants to add their shop via WhatsApp. Accepts menu images as base64 strings."
    ),
    side_effects="Creates or updates vendor in local data store and returns a public URL slug.",
)


@mcp.tool(description=VendorOnboardDesc.model_dump_json())
async def vendor_onboard(
    name: Annotated[str, Field(description="Shop name")],
    pincode: Annotated[str, Field(description="6-digit pincode")],
    address: Annotated[str | None, Field(description="Address (optional)")] = None,
    phone: Annotated[str | None, Field(description="Phone/WhatsApp (optional)")] = None,
    tags: Annotated[str | None, Field(description="Comma-separated tags like bakery, snacks, veg")] = None,
    discount_text: Annotated[str | None, Field(description="Optional discount description e.g. 10% off on combos")] = None,
    menu_images_base64: Annotated[list[str] | None, Field(description="List of base64-encoded menu images")] = None,
) -> str:
    """
    Creates or updates a vendor entry identified by (name+pincode) slug. Stores menu images inline for simplicity.
    Returns a public URL to view the vendor.
    """
    if not pincode.isdigit() or len(pincode) not in (5, 6):
        raise McpError(ErrorData(code=INVALID_PARAMS, message="pincode must be 5 or 6 digits"))

    db = load_vendors_db()
    vendor_slug = slugify(f"{name}-{pincode}")

    existing: Optional[dict[str, Any]] = next((v for v in db.get("vendors", []) if v.get("slug") == vendor_slug), None)

    tags_list = [t.strip() for t in (tags or "").split(",") if t.strip()] if tags else []
    images = menu_images_base64 or []

    if existing:
        # Update fields
        existing.update({
            "name": name,
            "pincode": pincode,
            "address": address,
            "phone": phone,
            "tags": tags_list,
            "discount_text": discount_text,
        })
        if images:
            existing.setdefault("menu_images_base64", [])
            existing["menu_images_base64"].extend(images)
        vendor_id = existing["vendor_id"]
    else:
        vendor_id = f"v_{int(datetime.utcnow().timestamp())}"
        vendor = Vendor(
            vendor_id=vendor_id,
            name=name,
            slug=vendor_slug,
            pincode=pincode,
            address=address,
            phone=phone,
            tags=tags_list,
            discount_text=discount_text,
            menu_images_base64=images,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        db.setdefault("vendors", []).append(vendor.model_dump())

    save_vendors_db(db)
    public_url = f"https://example.com/s/{vendor_slug}"
    return (
        f"Onboarded: {name} (PIN {pincode}). Public menu: {public_url}\n"
        f"Add more images anytime by calling vendor_onboard with the same name+pincode."
    )


# --- Tool: discounts_lookup ---
DiscountsLookupDesc = RichToolDescription(
    description=(
        "Find vendors by pincode and optional query (shop name/tag) and show any discount text."
    ),
    use_when="Customer asks which shops offer discounts in a pincode or for a specific shop",
    side_effects=None,
)


@mcp.tool(description=DiscountsLookupDesc.model_dump_json())
async def discounts_lookup(
    pincode: Annotated[str, Field(description="5/6-digit pincode to search in")],
    query: Annotated[str | None, Field(description="Optional search: shop name keyword or tag")] = None,
    max_results: Annotated[int, Field(description="Max vendors to return")] = 10,
) -> str:
    if not pincode.isdigit() or len(pincode) not in (5, 6):
        raise McpError(ErrorData(code=INVALID_PARAMS, message="pincode must be 5 or 6 digits"))

    db = load_vendors_db()
    vendors: list[dict[str, Any]] = [v for v in db.get("vendors", []) if v.get("pincode") == pincode]

    if query:
        q = query.lower()
        vendors = [
            v for v in vendors
            if q in (v.get("name", "").lower())
            or q in ",".join(v.get("tags", [])).lower()
            or (v.get("discount_text") or "").lower().__contains__(q)
        ]

    vendors = vendors[: max(1, min(max_results, 25))]

    if not vendors:
        return (
            "No shops with discounts found in this pincode yet."
            " Add your shop: https://example.com/add and try nearby pincodes."
        )

    lines = [f"Discounts near PIN {pincode}:"]
    for v in vendors:
        discount = v.get("discount_text") or "—"
        url = f"https://example.com/s/{v.get('slug')}"
        tags = ", ".join(v.get("tags", []))
        lines.append(f"- {v.get('name')} ({tags}) — {discount} — {url}")

    more_url = f"https://example.com/p/{pincode}"
    lines.append(f"More shops: {more_url}")
    return "\n".join(lines)

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

# --- Location Testing Tools (Prototype 2) ---

LOCATION_EXPERIMENT_DESC = RichToolDescription(
    description="Experimental tool to test what location data Puch.ai can provide from WhatsApp",
    use_when="Use when testing location sharing capabilities or when user says 'test my location'",
    side_effects="Logs location data for analysis and returns formatted location info"
)

@mcp.tool(description=LOCATION_EXPERIMENT_DESC.model_dump_json())
async def location_experiment(
    user_latitude: Annotated[float, Field(description="Your current latitude coordinate")] = 0.0,
    user_longitude: Annotated[float, Field(description="Your current longitude coordinate")] = 0.0,
    user_address: Annotated[str, Field(description="Your current address")] = "",
    location_accuracy: Annotated[float, Field(description="GPS accuracy in meters")] = 0.0,
    pincode: Annotated[str, Field(description="Your area pincode")] = "",
    city: Annotated[str, Field(description="Your city name")] = "",
    state: Annotated[str, Field(description="Your state name")] = ""
) -> str:
    """
    🗺️ Test what location data Puch.ai can access from WhatsApp users
    """
    
    result = f"📍 **Location Data Test Results:**\n\n"
    
    # Check what data was received
    data_received = []
    if user_latitude != 0.0:
        data_received.append(f"🌐 Latitude: {user_latitude}")
    if user_longitude != 0.0:
        data_received.append(f"🌐 Longitude: {user_longitude}")
    if user_address:
        data_received.append(f"📫 Address: {user_address}")
    if location_accuracy > 0:
        data_received.append(f"🎯 GPS Accuracy: {location_accuracy}m")
    if pincode:
        data_received.append(f"📮 Pincode: {pincode}")
    if city:
        data_received.append(f"🏙️ City: {city}")
    if state:
        data_received.append(f"🗺️ State: {state}")
    
    if data_received:
        result += "\n".join(data_received)
        result += f"\n\n✅ **Success!** Received {len(data_received)} location parameters"
        
        # Try to find offers if we got location data
        search_pincode = pincode if pincode else "000000"
        if user_latitude != 0.0 and user_longitude != 0.0:
            result += f"\n\n🎯 **Location Capabilities Confirmed:**"
            result += f"\n- GPS coordinates: ✅ Working"
            result += f"\n- Address data: {'✅ Working' if user_address else '❌ Not provided'}"
            result += f"\n- Pincode: {'✅ Working' if pincode else '❌ Not provided'}"
            
            # If we have pincode, search for offers
            if pincode:
                try:
                    offers = await discounts_lookup(pincode, max_results=3)
                    result += f"\n\n🛍️ **Sample Offers in Your Area:**\n{offers}"
                except:
                    result += f"\n\n🛍️ **Offers Search:** Ready to search once vendors are added"
        
    else:
        result += "❌ **No location data received**"
        result += f"\n\n💡 **To test location access:**"
        result += f"\n1. Type: 'location_experiment test my location'"
        result += f"\n2. When prompted, share your current location"
        result += f"\n3. Allow WhatsApp location permissions"
    
    # Log the data for analysis
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": "location_experiment",
        "latitude": user_latitude,
        "longitude": user_longitude,
        "address": user_address,
        "accuracy": location_accuracy,
        "pincode": pincode,
        "city": city,
        "state": state,
        "data_points_received": len(data_received)
    }
    
    try:
        log_file = os.path.join(DATA_DIR, "location_test_log.json")
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        result += f"\n\n💾 **Data logged** for analysis in location_test_log.json"
    except:
        pass
    
    return result

OFFERS_NEAR_ME_DESC = RichToolDescription(
    description="Find offers and discounts near user's current location using GPS or pincode",
    use_when="When user asks for 'offers near me', 'discounts nearby', or location-based searches",
    side_effects="Returns local vendor offers based on location data"
)

@mcp.tool(description=OFFERS_NEAR_ME_DESC.model_dump_json())
async def offers_near_me(
    detected_pincode: Annotated[str, Field(description="Auto-detected pincode from user location")] = "",
    user_latitude: Annotated[float, Field(description="User's current latitude")] = 0.0,
    user_longitude: Annotated[float, Field(description="User's current longitude")] = 0.0,
    search_query: Annotated[str, Field(description="What type of offers? (food, shopping, etc)")] = "",
    radius_km: Annotated[int, Field(description="Search radius in kilometers")] = 5
) -> str:
    """
    🎯 Find offers near your current location
    """
    
    result = "🗺️ **Location-Based Offers Search**\n\n"
    
    # Determine search area
    search_pincode = detected_pincode
    
    # If no pincode but have coordinates, try to estimate area
    if not search_pincode and user_latitude != 0.0 and user_longitude != 0.0:
        result += f"📍 Using GPS coordinates: {user_latitude}, {user_longitude}\n"
        result += f"🔍 Searching within {radius_km}km radius\n\n"
        # For now, use a default pincode - in production you'd use reverse geocoding
        search_pincode = "682001"  # Default for testing
        result += f"🎯 Estimated search area: {search_pincode}\n\n"
    
    if not search_pincode:
        return result + "❌ **Location Required**\n\n" + \
               "💡 Please share your location or provide a pincode to find nearby offers.\n\n" + \
               "Try: 'offers_near_me share my location' or 'offers_near_me in 682001'"
    
    # Search for offers
    try:
        offers = await discounts_lookup(
            pincode=search_pincode,
            query=search_query if search_query else None,
            max_results=10
        )
        result += offers
    except Exception as e:
        result += f"❌ Error searching offers: {str(e)}"
    
    return result

# --- Tool: audio_test_handler ---
@mcp.tool
async def audio_test_handler(
    message: str = "play audio"
) -> list[TextContent | AudioContent]:
    """Test audio content return - always returns audio for testing"""
    log_tool_request("audio_test_handler", message=message)
    return [
        TextContent(type="text", text="🎵 Here's your test audio! Playing Star Wars theme..."),
        AudioContent(type="audio", mediaUrl="https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav")
    ]

# --- Run MCP Server ---
async def main():
    print("🚀 Starting MCP server (Prototype 2) on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())
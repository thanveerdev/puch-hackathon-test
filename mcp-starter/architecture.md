# MCP Server Architecture for Puch.ai Integration

## Overview
Your MCP (Model Context Protocol) server is built with **FastMCP** framework and serves as a bridge between Puch.ai and various external services (web scraping, job search, image processing).

## Core Architecture Components

### 1. **Server Framework**
```python
mcp = FastMCP("Job Finder MCP Server", auth=SimpleBearerAuthProvider(TOKEN))
```
- **Framework**: FastMCP 2.11.2 (streamable-http transport)
- **Port**: 8086
- **Protocol**: HTTP with MCP over streamable transport
- **Authentication**: Custom Bearer token authentication

### 2. **Authentication Layer**
```python
class SimpleBearerAuthProvider(BearerAuthProvider):
    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"])
```
- **Token**: `hackdevtoken_12345`
- **Validation**: Returns phone number `918086165065` for Puch.ai verification
- **Security**: RSA key pair generation for JWT-style authentication

### 3. **Tool Architecture**

#### **Required Tool: `validate`**
```python
@mcp.tool
async def validate() -> str:
    return MY_NUMBER  # Returns 918086165065
```
- **Purpose**: Puch.ai authentication requirement
- **Returns**: Phone number in `{country_code}{number}` format

#### **Main Tool: `job_finder`**
```python
@mcp.tool
async def job_finder(user_goal, job_description=None, job_url=None, raw=False)
```
**Multi-mode functionality:**
- **Direct Analysis**: Analyzes provided job descriptions
- **URL Fetching**: Scrapes job postings from URLs  
- **Smart Search**: DuckDuckGo search for job queries

#### **Image Tool: `make_img_black_and_white`**
```python
@mcp.tool
async def make_img_black_and_white(puch_image_data: str)
```
- **Input**: Base64 encoded image data
- **Processing**: PIL/Pillow for image conversion
- **Output**: Black & white PNG image

### 4. **External Service Integration**

#### **Web Scraping Engine**
```python
class Fetch:
    @classmethod
    async def fetch_url(cls, url, user_agent, force_raw=False)
```
- **HTTP Client**: httpx with async support
- **Content Processing**: readabilipy + markdownify for clean extraction
- **Error Handling**: MCP-compliant error responses

#### **Search Engine**
```python
@staticmethod
async def google_search_links(query: str, num_results: int = 5)
```
- **Provider**: DuckDuckGo (avoids Google blocking)
- **Parsing**: BeautifulSoup for HTML extraction
- **Results**: Returns job posting URLs

## Deployment Architecture

### 1. **Local Development**
```
MCP Server (localhost:8086) ← → Cloudflare Tunnel ← → Puch.ai
```

### 2. **Network Flow**
1. **Puch.ai** sends HTTPS requests to tunnel URL
2. **Cloudflare Tunnel** forwards to `localhost:8086/mcp/`
3. **FastMCP Server** processes MCP protocol requests
4. **Tools** execute business logic and return responses

### 3. **Configuration Management**
```bash
.env file:
├── AUTH_TOKEN=hackdevtoken_12345
└── MY_NUMBER=918086165065

config.yml:
├── tunnel: 66806db9-9870-424c-b8ce-66b71a39385a
└── service: http://localhost:8086
```

## Data Flow Architecture

### 1. **Authentication Flow**
```
Puch.ai → POST /mcp/validate → Bearer Token Check → Phone Number Response
```

### 2. **Job Search Flow**
```
User Query → job_finder Tool → DuckDuckGo Search → HTML Parsing → Job Links
```

### 3. **URL Processing Flow**
```
Job URL → httpx Fetch → readabilipy Clean → Markdown Convert → Structured Response
```

### 4. **Image Processing Flow**
```
Base64 Image → PIL Decode → Grayscale Convert → PNG Encode → Base64 Response
```

## Technology Stack

### **Backend**
- **Python 3.11+** - Runtime
- **FastMCP 2.11.2** - MCP server framework
- **Uvicorn** - ASGI server
- **asyncio** - Async/await support

### **Dependencies**
- **httpx** - HTTP client for web requests
- **beautifulsoup4** - HTML parsing
- **readabilipy** - Content extraction
- **markdownify** - HTML to Markdown conversion
- **Pillow** - Image processing
- **python-dotenv** - Environment management

### **Infrastructure**
- **Cloudflare Tunnel** - HTTPS exposure
- **GitHub** - Code repository
- **uv** - Python package manager

## Security Architecture

### 1. **Authentication**
- Bearer token validation
- Phone number verification
- RSA key pair for JWT-style tokens

### 2. **Network Security**
- HTTPS-only communication (Puch.ai requirement)
- Cloudflare tunnel encryption
- No direct port exposure

### 3. **Input Validation**
- MCP protocol validation
- URL sanitization
- Base64 image validation

## Scalability Considerations

### **Current Limitations**
- Single-process deployment
- Temporary Cloudflare tunnels
- No load balancing

### **Production Improvements**
- Deploy to Vercel/Railway for stability
- Add database for persistent storage
- Implement rate limiting
- Add monitoring and logging

This architecture provides a robust foundation for MCP tool integration with Puch.ai while maintaining security and extensibility.
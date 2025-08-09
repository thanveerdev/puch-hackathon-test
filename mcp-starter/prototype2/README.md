# Prototype 2 - Location-Aware MCP Server

This is the Prototype 2 version with complex location testing tools.

## Features

### Core Business Tools
- ✅ `validate` - Phone authentication
- ✅ `vendor_onboard` - Business registration with images
- ✅ `discounts_lookup` - Pincode-based vendor search
- ✅ `job_finder` - Job search functionality
- ✅ `make_img_black_and_white` - Image processing

### Location Testing Tools (Prototype 2)
- 🗺️ `location_experiment` - Complex 7-parameter location testing
- 🎯 `offers_near_me` - GPS-based offer discovery with 5 parameters

## Key Differences from Main Version

**Additional Complexity:**
- **138 lines more code** for location testing
- **Complex parameter handling** for GPS coordinates
- **Location data logging** to `location_test_log.json`
- **Reverse geocoding preparation**
- **Manual coordinate input** (which causes UX issues)

## Running Prototype 2

```bash
cd "/Users/thanveer.dev/Desktop/Puch hackathon/prototype2"
uv sync
uv run python mcp_starter_prototype2.py
```

## Location Testing

**Tools to test:**
```
location_experiment test my location
offers_near_me find food deals nearby
```

**Expected issues:**
- Manual coordinate input instead of WhatsApp location snippets
- Complex parameter prompts that confuse users
- Over-engineered location handling

## Why This Was Reverted

The complex location tools required users to manually input GPS coordinates instead of triggering WhatsApp's native location sharing UI. This created poor UX compared to the natural "offers near me" flow that should trigger location snippets automatically.

## File Structure

```
prototype2/
├── mcp_starter_prototype2.py    # 530+ lines with location tools
├── .env                         # Environment variables
├── pyproject.toml              # Dependencies
├── data/                       # Data storage
│   └── location_test_log.json  # Location testing logs
└── README.md                   # This file
```

---

*This prototype demonstrates the complexity trap of over-engineering location features instead of focusing on natural WhatsApp interaction patterns.*
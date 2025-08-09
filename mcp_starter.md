## MCP Starter: Vendor Onboarding + Discounts Lookup

This document summarizes the two custom tools added to the MCP server, how users invoke them in Puch, and what you must configure before going live.

### What’s included
- vendor_onboard: Sellers can add their shop (name, pincode, address, phone, tags, discount) and optional menu images (base64)
- discounts_lookup: Customers can find shops and discounts in a given pincode, optionally filtered by a keyword/tag
- Simple JSON persistence under `data/vendors.json`

### Tool definitions
- vendor_onboard(
  - name: string (shop name)
  - pincode: string (5/6 digits)
  - address?: string
  - phone?: string
  - tags?: string (comma-separated: e.g., "bakery, snacks, veg")
  - discount_text?: string (e.g., "10% off on combos")
  - menu_images_base64?: string[] (base64-encoded images)
) -> string

- discounts_lookup(
  - pincode: string (5/6 digits)
  - query?: string (shop name/tag/keyword)
  - max_results?: number (default 10)
) -> string (list with HTTPS links)

### WhatsApp usage (Puch)
- Vendor onboarding examples:
  - "/onboard Shree Snacks 560001 address=MG Road phone=90000xxxxx tags=snacks,veg discount=10% off" (attach menu images if any)
  - Puch calls `vendor_onboard(...)`; tool returns public URL for the shop
- Customer discovery examples:
  - "/discounts 560001"
  - "/discounts 560001 vada pav"
  - Puch calls `discounts_lookup(...)`; tool replies with a short list and links

### Deploy and connect
1) Deploy MCP server over HTTPS (Vercel/Cloudflare/Render/etc.)
2) Connect from Puch chat (one-time):
   - Bearer token: `/mcp connect https://your-domain/mcp <token>`
   - Or hosted server ID: `/mcp use <server_id>`
3) After connect, users send commands as normal (no extra setup)

### Data persistence
- Path: `mcp-starter/data/vendors.json`
- Structure: `{ "vendors": [ { vendor fields... } ] }`
- A couple of seed vendors are included for PIN `560001`

### Public URLs
- Tool responses currently use placeholders like:
  - Shop: `https://example.com/s/<slug>`
  - Pincode directory: `https://example.com/p/<pincode>`
- Replace `example.com` with your real domain (for your public pages)

### Constraints and notes
- Puch MCP tools receive text parameters and images (base64). No audio/video/file payloads right now
- If you must return a file (e.g., PDF), host it yourself and return the URL in text
- Keep image payload sizes reasonable (compress/resize before returning)

### Next steps
- Build minimal public pages:
  - `/s/<slug>`: shop page (name, items, prices, contact)
  - `/p/<pincode>`: list of shops in that pincode
- Optionally add a simple web form for sellers to onboard outside WhatsApp
- Swap placeholder domain to your deployed domain and redeploy

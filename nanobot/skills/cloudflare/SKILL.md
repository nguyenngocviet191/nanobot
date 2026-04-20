---
name: cloudflare
description: Cloudflare services và API. Workers, R2 storage, Browser Rendering, Tunnels, Pages, DNS Management.
---

# Cloudflare Skill

Các dịch vụ và API của Cloudflare.

## Khi nào dùng

- Deploy Workers
- Sử dụng R2 storage
- Browser Rendering
- Tunnels
- Pages deployment
- DNS Management (add/update/delete records)

## Services

### Cloudflare Workers
- Serverless execution
- Edge computing
- JavaScript/TypeScript

### Cloudflare R2
- S3-compatible storage
- No egress fees
- Object storage

### Cloudflare Browser Rendering
- Chrome automation
- Screenshot capture
- Web scraping

### Cloudflare Tunnels
- Secure access
- Zero config
- Private connections

### DNS Management
- Add A/AAAA/CNAME records
- List DNS records
- Update records
- Delete records

## Environment Variables

```bash
# Required
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_ZONE_ID=your_zone_id
CLOUDFLARE_EMAIL=your@email.com
```

## API Usage

### List DNS Records
```bash
curl -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json"
```

### Add DNS Record
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "A",
    "name": "vps",
    "content": "103.245.237.43",
    "ttl": 3600,
    "proxied": false
  }'
```

### Delete DNS Record
```bash
curl -X DELETE "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
  -H "Authorization: Bearer $API_TOKEN"
```

## Quick Commands

```bash
# List all DNS records
cf-list-dns

# Add A record
cf-add-record vps 103.245.237.43 A

# Add CNAME record
cf-add-record www example.com CNAME

# Get Zone ID
cf-get-zone shinnio.com
```

## Lấy API Token

1. Login [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Profile → API Tokens
3. Create Custom Token
4. Permissions: Zone → DNS → Edit
5. Zone Resources: Include → Specific zone → shinnio.com

## Sử dụng

"Sử dụng cloudflare để [task]"
"Add DNS record cho vps.shinnio.com"

# Landmark Ops - Installation & Setup Guide

## Overview
This Frappe app handles Landmark Auto Spare Parts delivery operations with WhatsApp integration and Azure Document Intelligence OCR.

## Target Site
- **Site**: `landmark.leet.ae`
- **Module**: Landmark Ops

## Installation Commands

### 1. Create the App (if not already created)
```bash
cd /home/frappe/frappe-bench
bench new-app landmarkops
# When prompted:
# - App Title: Landmark Ops
# - App Description: Landmark delivery operations with WhatsApp integration
# - App Publisher: Landmark
# - App Email: ops@landmark.ae
# - App Icon: octicon octicon-package
# - App Color: #3498db
```

### 2. Install the App on the Site
```bash
bench --site landmark.leet.ae install-app landmarkops
```

### 3. Build Assets
```bash
bench build --app landmarkops
```

### 4. Restart Services
```bash
bench restart
# Or if using supervisor:
sudo supervisorctl restart all
```

## Configuration

### 1. Navigate to Landmark Ops Settings
After installation, go to:
**Desk → Landmark Ops → Landmark Ops Settings**

Configure the following:

#### Azure Document Intelligence
- **Azure Endpoint**: `https://YOUR-RESOURCE.cognitiveservices.azure.com/`
- **Azure API Key**: Your Azure Document Intelligence API key
- **Azure Model ID**: `prebuilt-document` (or your custom model ID)

#### WhatsApp Business API
- **WhatsApp API Base URL**: Your WhatsApp Business API gateway URL (e.g., `https://graph.facebook.com/v18.0`)
- **WhatsApp API Token**: Your WhatsApp Business API access token
- **WhatsApp Business Number**: The WhatsApp number ID for sending messages

#### Driver Integration
- **Driver Link DocType**: `Whatsapp Contact Link` (default)
- **Driver Link Fieldname**: The field name in Whatsapp Contact Link that links to Driver (e.g., `driver` or `employee`)

## API Endpoints

The app exposes the following whitelisted endpoints:

### 1. Inbound WhatsApp Webhook
**Endpoint**: `/api/method/landmarkops.api.whatsapp_inbound`
**Method**: POST
**Payload**:
```json
{
  "from_number": "+9715xxxxxxxx",
  "media_url": "https://example.com/path/to/image.jpg",
  "message_id": "wamid.xxx",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**cURL Example**:
```bash
curl -X POST "https://landmark.leet.ae/api/method/landmarkops.api.whatsapp_inbound" \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d '{
    "from_number": "+971501234567",
    "media_url": "https://example.com/delivery-note.jpg",
    "message_id": "wamid.123456789"
  }'
```

### 2. Driver Confirm Items
**Endpoint**: `/api/method/landmarkops.api.driver_confirm_items`
**Method**: POST
**Payload**:
```json
{
  "delivery_note_name": "LDEL-0001",
  "items": [
    {"name": "LDEL-0001-1", "qty": 5},
    {"name": "LDEL-0001-2", "qty": 3}
  ]
}
```

**cURL Example**:
```bash
curl -X POST "https://landmark.leet.ae/api/method/landmarkops.api.driver_confirm_items" \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d '{
    "delivery_note_name": "LDEL-0001",
    "items": [
      {"name": "LDEL-0001-1", "qty": 5}
    ]
  }'
```

### 3. Driver Delivery Status
**Endpoint**: `/api/method/landmarkops.api.driver_delivery_status`
**Method**: POST
**Payload**:
```json
{
  "delivery_note_name": "LDEL-0001",
  "action": "delivered_cash"
}
```
Actions: `delivered_cash` or `delivered_credit`

**cURL Example**:
```bash
curl -X POST "https://landmark.leet.ae/api/method/landmarkops.api.driver_delivery_status" \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d '{
    "delivery_note_name": "LDEL-0001",
    "action": "delivered_cash"
  }'
```

## Workflow

1. **Image Received**: Driver sends photo via WhatsApp → Creates Landmark Delivery Note with status "Image Received"
2. **Parsing**: Background job calls Azure Document Intelligence → Status changes to "Parsed"
3. **Driver Review**: WhatsApp Flow sent to driver with editable item quantities → Status "Awaiting Driver Confirmation"
4. **Confirmation**: Driver submits edited quantities → Status "Confirmed by Driver"
5. **Delivery**: Driver selects Cash/Credit button → Status "Delivered – Cash Received" or "Delivered – Credit"

## DocTypes Created

- **Landmark Ops Settings** (Single) - Configuration
- **Landmark Delivery Note** - Main document with header and child items
- **Landmark Delivery Item** - Child table for line items
- **Landmark WhatsApp Capture** - Log of inbound WhatsApp messages

## Status Flow

```
Image Received
    ↓
Parsed
    ↓
Awaiting Driver Confirmation
    ↓
Confirmed by Driver
    ↓
Delivered – Cash Received / Delivered – Credit
```

## Troubleshooting

### Check Background Jobs
```bash
# Monitor the queue
bench --site landmark.leet.ae console
>>> frappe.get_all("RQ Job", fields=["*"], limit=10)
```

### Check Logs
```bash
tail -f /home/frappe/frappe-bench/sites/landmark.leet.ae/logs/web.log
tail -f /home/frappe/frappe-bench/sites/landmark.leet.ae/logs/worker.log
```

### Test Azure Connection
```python
bench --site landmark.leet.ae console
from landmarkops.utils.azure_parser import test_azure_connection
test_azure_connection()
```

## Security Notes

- All API endpoints require authentication (API key/secret)
- Azure API key and WhatsApp token are stored encrypted in Settings
- Media files are stored securely in Frappe File system
- All webhook payloads are logged in Landmark WhatsApp Capture for audit

## Support

For issues or questions, contact the development team or check:
- Frappe docs: https://frappeframework.com/docs
- Azure Document Intelligence: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/

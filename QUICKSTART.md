# Landmark Ops - Quick Start Guide

## Prerequisites

1. **Frappe Bench** already set up at `/home/frappe/frappe-bench`
2. **Site** `landmark.leet.ae` already created
3. **Azure Document Intelligence** subscription with API key
4. **WhatsApp Business API** credentials
5. **Whatsapp Contact Link** DocType exists linking WhatsApp numbers to drivers

## Installation Steps

### Step 1: Install the App

The app files are already in `/home/frappe/frappe-bench/apps/landmarkops`. You just need to install it on your site:

```bash
cd /home/frappe/frappe-bench

# Install app on the site
bench --site landmark.leet.ae install-app landmarkops

# Build assets
bench build --app landmarkops

# Clear cache
bench --site landmark.leet.ae clear-cache

# Restart
bench restart
# OR if using supervisor:
sudo supervisorctl restart all
```

### Step 2: Configure Settings

1. Login to your Frappe desk at `https://landmark.leet.ae`

2. Go to: **Landmark Ops → Landmark Ops Settings**

3. Configure **Azure Document Intelligence**:
   ```
   Azure Endpoint: https://YOUR-RESOURCE.cognitiveservices.azure.com/
   Azure API Key: [Your Azure API Key]
   Azure Model ID: prebuilt-document
   Azure Timeout: 120
   Azure Max Retries: 3
   ```

4. Configure **WhatsApp Business API**:
   ```
   WhatsApp API Base URL: https://graph.facebook.com/v18.0
   WhatsApp API Token: [Your WhatsApp Access Token]
   WhatsApp Business Number: +971501234567
   WhatsApp Phone Number ID: [Your Phone Number ID from Meta]
   ```

5. Configure **Integration Settings**:
   ```
   Driver Link DocType: Whatsapp Contact Link
   Driver Link Fieldname: driver (or employee, depending on your setup)
   Auto Process Images: ✓ (checked)
   Send WhatsApp Flow After Parsing: ✓ (checked)
   ```

6. **Save** the settings

### Step 3: Set Up WhatsApp Webhook

Configure your WhatsApp Business API to send webhooks to:

```
POST https://landmark.leet.ae/api/method/landmarkops.api.whatsapp_inbound
```

**Required Headers**:
```
Content-Type: application/json
Authorization: token [YOUR_API_KEY]:[YOUR_API_SECRET]
```

**Webhook Payload Format**:
```json
{
  "from_number": "+9715xxxxxxxx",
  "media_url": "https://example.com/image.jpg",
  "message_id": "wamid.xxx",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Step 4: Generate API Keys

To allow WhatsApp to call your endpoints, generate API keys:

1. Go to **User** (e.g., Administrator or create a dedicated API user)
2. Scroll to **API Access** section
3. Click **Generate Keys**
4. Save the **API Key** and **API Secret** securely
5. Use these in the WhatsApp webhook configuration

### Step 5: Test the Integration

#### Test 1: WhatsApp Inbound

```bash
curl -X POST "https://landmark.leet.ae/api/method/landmarkops.api.whatsapp_inbound" \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d '{
    "from_number": "+971501234567",
    "media_url": "https://example.com/test-delivery-note.jpg",
    "message_id": "test123"
  }'
```

Expected response:
```json
{
  "success": true,
  "message": "Delivery note created successfully",
  "delivery_note": "LDEL-2025-0001"
}
```

#### Test 2: Driver Confirm Items

```bash
curl -X POST "https://landmark.leet.ae/api/method/landmarkops.api.driver_confirm_items" \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d '{
    "delivery_note_name": "LDEL-2025-0001",
    "items": [
      {"name": "LDEL-2025-0001-1", "qty": 5}
    ]
  }'
```

#### Test 3: Delivery Status

```bash
curl -X POST "https://landmark.leet.ae/api/method/landmarkops.api.driver_delivery_status" \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d '{
    "delivery_note_name": "LDEL-2025-0001",
    "action": "delivered_cash"
  }'
```

### Step 6: Verify in Frappe Desk

1. Go to **Landmark Ops → Landmark Delivery Note**
2. You should see the test delivery note
3. Check the status progression
4. View the **Azure Document Intelligence** section for raw OCR data
5. Check **Landmark WhatsApp Capture** for webhook logs

## Workflow in Production

### 1. Driver Sends Photo

Driver takes a photo of the delivery note and sends it via WhatsApp to your WhatsApp Business number.

### 2. Webhook Received

Your WhatsApp gateway sends a webhook to:
```
POST /api/method/landmarkops.api.whatsapp_inbound
```

### 3. System Processing

- Looks up driver from WhatsApp number
- Creates **Landmark Delivery Note** (Status: "Image Received")
- Downloads and attaches the image
- Enqueues background job for Azure processing

### 4. Azure OCR

- Background job calls Azure Document Intelligence
- Parses delivery note fields and line items
- Updates status to "Parsed"

### 5. Driver Review

- WhatsApp message sent to driver with item summary
- Driver can review quantities
- Driver confirms (calls `driver_confirm_items`)
- Status: "Confirmed by Driver"

### 6. Delivery Completion

- WhatsApp buttons sent: "Cash" or "Credit"
- Driver taps button (calls `driver_delivery_status`)
- Status: "Delivered - Cash Received" or "Delivered - Credit"
- Confirmation message sent to driver

## Status Flow

```
Image Received
    ↓ (Azure processing)
Parsed
    ↓ (WhatsApp flow sent)
Awaiting Driver Confirmation
    ↓ (Driver confirms)
Confirmed by Driver
    ↓ (Driver selects payment)
Delivered - Cash Received
    OR
Delivered - Credit
```

## Monitoring & Troubleshooting

### Check Logs

```bash
# Web logs
tail -f sites/landmark.leet.ae/logs/web.log

# Worker logs (for background jobs)
tail -f sites/landmark.leet.ae/logs/worker.log

# Scheduled job logs
tail -f sites/landmark.leet.ae/logs/schedule.log
```

### Check Background Jobs

```bash
bench --site landmark.leet.ae console
```

Then in the console:
```python
# Check recent jobs
jobs = frappe.get_all("RQ Job", fields=["*"], order_by="creation desc", limit=10)
print(jobs)

# Check failed jobs
failed = frappe.get_all("RQ Job", filters={"status": "failed"}, fields=["*"])
print(failed)
```

### Test Azure Connection

```bash
bench --site landmark.leet.ae console
```

```python
from landmarkops.utils.azure_parser import test_azure_connection
test_azure_connection()
```

### Manual Processing

If automatic processing fails, you can manually trigger it:

```bash
bench --site landmark.leet.ae console
```

```python
from landmarkops.utils.azure_parser import parse_delivery_note_image

# Replace with actual delivery note name
parse_delivery_note_image("LDEL-2025-0001")
```

## Common Issues

### Issue: "No driver found for WhatsApp number"

**Solution**: Ensure the WhatsApp Contact Link DocType has a record linking the driver's WhatsApp number to their Employee/Driver record.

### Issue: Azure timeout

**Solution**: Increase the timeout in **Landmark Ops Settings → Azure Timeout** (default: 120 seconds)

### Issue: WhatsApp messages not sending

**Solutions**:
- Verify WhatsApp API credentials in Settings
- Check that WhatsApp Phone Number ID is correct
- Ensure WhatsApp number format is correct (international format)
- Check web.log for API error details

### Issue: Background jobs not processing

**Solutions**:
```bash
# Check if workers are running
bench doctor

# Restart workers
bench restart

# Check worker status
ps aux | grep frappe
```

## Security Best Practices

1. **API Keys**: Keep API keys secure, never commit to git
2. **HTTPS**: Always use HTTPS in production
3. **Rate Limiting**: Configure rate limiting on webhook endpoints
4. **Validation**: All inputs are validated before processing
5. **Audit Trail**: All operations logged in Landmark WhatsApp Capture

## Support

For issues:
1. Check logs first (web.log, worker.log)
2. Review Error Log DocType in Frappe
3. Check Landmark WhatsApp Capture for webhook data
4. Review Azure raw JSON in Landmark Delivery Note

## Next Steps

- Configure WhatsApp Business API webhook subscription
- Set up proper driver records in Whatsapp Contact Link
- Train drivers on the WhatsApp workflow
- Monitor initial deliveries closely
- Adjust Azure parsing logic if needed based on your delivery note format

---

**Ready to go live!** 🚀

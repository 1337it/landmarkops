# Landmark Ops App - Files Created

## Complete File Structure

```
/home/frappe/frappe-bench/apps/landmarkops/
├── landmarkops/
│   ├── __init__.py                                    # App version
│   ├── hooks.py                                       # Frappe hooks configuration
│   ├── modules.txt                                    # Module definition
│   ├── api.py                                         # WhatsApp API endpoints (whitelisted)
│   │
│   ├── utils/                                         # Utility modules
│   │   ├── __init__.py
│   │   ├── azure_parser.py                            # Azure Document Intelligence integration
│   │   └── whatsapp_sender.py                         # WhatsApp message/flow sender
│   │
│   └── landmark_ops/                                  # Main module
│       ├── __init__.py
│       └── doctype/
│           ├── __init__.py
│           │
│           ├── landmark_ops_settings/                 # Settings DocType (Single)
│           │   ├── __init__.py
│           │   ├── landmark_ops_settings.json
│           │   └── landmark_ops_settings.py
│           │
│           ├── landmark_delivery_note/                # Main delivery note DocType
│           │   ├── __init__.py
│           │   ├── landmark_delivery_note.json
│           │   └── landmark_delivery_note.py
│           │
│           ├── landmark_delivery_item/                # Child table DocType
│           │   ├── __init__.py
│           │   ├── landmark_delivery_item.json
│           │   └── landmark_delivery_item.py
│           │
│           └── landmark_whatsapp_capture/             # WhatsApp webhook log DocType
│               ├── __init__.py
│               ├── landmark_whatsapp_capture.json
│               └── landmark_whatsapp_capture.py
│
├── setup.py                                           # Python package setup
├── requirements.txt                                   # Python dependencies
├── MANIFEST.in                                        # Package manifest
├── .gitignore                                         # Git ignore rules
├── license.txt                                        # MIT License
├── README.md                                          # App overview
├── INSTALLATION.md                                    # Detailed installation guide
├── QUICKSTART.md                                      # Quick start guide
└── FILES_CREATED.md                                   # This file

```

## Key Components

### 1. DocTypes (4 Total)

#### Landmark Ops Settings (Single)
- **File**: `landmarkops/landmark_ops/doctype/landmark_ops_settings/`
- **Purpose**: Configuration for Azure and WhatsApp API
- **Fields**:
  - Azure endpoint, API key, model ID, timeout, retries
  - WhatsApp API URL, token, business number, phone number ID
  - Integration settings (driver lookup DocType and field)

#### Landmark Delivery Note
- **File**: `landmarkops/landmark_ops/doctype/landmark_delivery_note/`
- **Purpose**: Main document for delivery operations
- **Fields**:
  - Driver info (driver link, WhatsApp number)
  - Status tracking (6 states)
  - Delivery note details (DN number, date, sales order, etc.)
  - Customer info (code, name, phone, address, reference)
  - Child table for line items
  - Azure data (source file, operation ID, raw JSON)
  - Timestamps (driver confirmed, delivered)

#### Landmark Delivery Item (Child Table)
- **File**: `landmarkops/landmark_ops/doctype/landmark_delivery_item/`
- **Purpose**: Line items in delivery note
- **Fields**: Sr No, Item ID, Flexi Code, Item Name, Item Name Short, Unit, Qty, Cartons

#### Landmark WhatsApp Capture
- **File**: `landmarkops/landmark_ops/doctype/landmark_whatsapp_capture/`
- **Purpose**: Audit log of inbound WhatsApp messages
- **Fields**: Message ID, WhatsApp number, media URL, payload JSON, delivery note link, timestamp

### 2. API Endpoints (3 Total)

All in `landmarkops/api.py`:

1. **whatsapp_inbound** (`@frappe.whitelist(allow_guest=True)`)
   - Receives WhatsApp webhook with image
   - Looks up driver
   - Creates Landmark Delivery Note
   - Enqueues Azure processing

2. **driver_confirm_items** (`@frappe.whitelist(allow_guest=False)`)
   - Receives driver confirmation from WhatsApp Flow
   - Updates item quantities
   - Sends Cash/Credit buttons

3. **driver_delivery_status** (`@frappe.whitelist(allow_guest=False)`)
   - Receives delivery status (Cash/Credit)
   - Updates final status
   - Sends confirmation message

### 3. Utility Modules (2 Total)

#### Azure Parser (`landmarkops/utils/azure_parser.py`)
- `parse_delivery_note_image()`: Main parsing function
- `call_azure_document_intelligence()`: API call to Azure
- `poll_for_results()`: Poll for async results
- `parse_azure_response()`: Extract fields from Azure JSON
- `extract_key_value_pairs()`: Parse key-value pairs
- `parse_items_table()`: Parse line items table
- `test_azure_connection()`: Test Azure connectivity

#### WhatsApp Sender (`landmarkops/utils/whatsapp_sender.py`)
- `send_driver_review_flow()`: Send review message with items
- `send_delivery_status_buttons()`: Send Cash/Credit buttons
- `send_whatsapp_message()`: Send text message
- `send_whatsapp_buttons()`: Send interactive buttons
- `send_confirmation_message()`: Send final confirmation

### 4. Python Controllers

Each DocType has a Python controller with business logic:

- **LandmarkOpsSettings**: Helper function `get_settings()`
- **LandmarkDeliveryNote**: Validation logic, status flow enforcement, helper methods
- **LandmarkDeliveryItem**: Simple child table (no custom logic)
- **LandmarkWhatsappCapture**: Simple log (no custom logic)

### 5. Documentation

- **README.md**: App overview and architecture
- **INSTALLATION.md**: Detailed installation and API documentation
- **QUICKSTART.md**: Step-by-step guide for getting started
- **FILES_CREATED.md**: This file - complete file listing

## Installation Commands

These commands are NOT executed automatically. You must run them manually:

```bash
cd /home/frappe/frappe-bench

# The app is already created in apps/landmarkops
# No need to run: bench new-app landmarkops

# Install the app on the site
bench --site landmark.leet.ae install-app landmarkops

# Build assets
bench build --app landmarkops

# Clear cache
bench --site landmark.leet.ae clear-cache

# Restart services
bench restart
# OR if using supervisor:
sudo supervisorctl restart all
```

## Configuration Required

After installation, configure in **Landmark Ops Settings**:

1. **Azure Document Intelligence**:
   - Endpoint URL
   - API Key
   - Model ID (default: `prebuilt-document`)

2. **WhatsApp Business API**:
   - API Base URL (e.g., `https://graph.facebook.com/v18.0`)
   - API Token
   - Business Number
   - Phone Number ID

3. **Integration**:
   - Driver Link DocType (default: `Whatsapp Contact Link`)
   - Driver Link Fieldname (default: `driver`)

## API Endpoints URLs

All endpoints accessible at:

```
https://landmark.leet.ae/api/method/landmarkops.api.[endpoint_name]
```

1. `landmarkops.api.whatsapp_inbound`
2. `landmarkops.api.driver_confirm_items`
3. `landmarkops.api.driver_delivery_status`

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
Delivered - Cash Received / Delivered - Credit
```

## Dependencies

- frappe (framework)
- requests (HTTP client)

## Next Steps

1. Run installation commands above
2. Configure Landmark Ops Settings in Frappe desk
3. Set up WhatsApp webhook pointing to `whatsapp_inbound` endpoint
4. Create Whatsapp Contact Link records for drivers
5. Test with sample delivery note image
6. Monitor logs and adjust as needed

---

**All files are ready!** The app is complete and ready for installation on `landmark.leet.ae`.

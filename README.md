# Landmark Ops

Frappe app for Landmark Auto Spare Parts delivery operations with WhatsApp Business API integration and Azure Document Intelligence OCR.

## Features

- **WhatsApp Integration**: Receive delivery note photos from drivers via WhatsApp
- **OCR Processing**: Automatically extract delivery note data using Azure Document Intelligence
- **Driver Confirmation**: Interactive WhatsApp flows for drivers to review and confirm item quantities
- **Delivery Tracking**: Track delivery status (Cash/Credit) through WhatsApp buttons
- **Audit Trail**: Complete logging of all WhatsApp interactions and document processing

## Architecture

### DocTypes

1. **Landmark Ops Settings** (Single)
   - Configuration for Azure Document Intelligence and WhatsApp API
   - Integration settings for driver lookup

2. **Landmark Delivery Note**
   - Main document for delivery operations
   - Contains header info (customer, delivery details) and line items
   - Tracks status flow from image receipt to final delivery

3. **Landmark Delivery Item** (Child Table)
   - Line items with quantities and product details

4. **Landmark WhatsApp Capture**
   - Audit log of all inbound WhatsApp messages

### Workflow

```
1. Driver → WhatsApp Photo
   ↓
2. WhatsApp Webhook → Frappe
   ↓
3. Create Delivery Note (Status: Image Received)
   ↓
4. Azure Document Intelligence (OCR)
   ↓
5. Parse & Update (Status: Parsed)
   ↓
6. Send WhatsApp Flow to Driver
   ↓
7. Driver Reviews & Confirms Items
   ↓
8. Status: Confirmed by Driver
   ↓
9. Send Cash/Credit Buttons
   ↓
10. Driver Selects → Final Status
```

### API Endpoints

All endpoints are accessible at `/api/method/landmarkops.api.*`

- **whatsapp_inbound**: Receive WhatsApp messages
- **driver_confirm_items**: Process driver confirmations
- **driver_delivery_status**: Update delivery status (Cash/Credit)

## Installation

See [INSTALLATION.md](INSTALLATION.md) for detailed setup instructions.

## Requirements

- Frappe Framework v13+
- Azure Document Intelligence API subscription
- WhatsApp Business API access
- Existing "Whatsapp Contact Link" DocType linking WhatsApp numbers to drivers

## Configuration

After installation, configure in **Landmark Ops Settings**:

- Azure Document Intelligence credentials
- WhatsApp Business API credentials
- Driver integration settings

## Security

- All API endpoints require authentication
- Sensitive credentials stored encrypted in Settings
- Complete audit trail of all operations
- File attachments secured in Frappe File system

## License

MIT

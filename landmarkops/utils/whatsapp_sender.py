# -*- coding: utf-8 -*-
# Copyright (c) 2025, Landmark and contributors
# For license information, please see license.txt

"""
WhatsApp Business API integration for sending messages and flows
"""

from __future__ import unicode_literals
import frappe
from frappe import _
import requests
import json
from typing import Dict, Any, List, Optional


def send_driver_review_flow(delivery_note_name: str) -> Dict[str, Any]:
	"""
	Send WhatsApp Flow to driver for reviewing and confirming items

	Args:
		delivery_note_name: Name of the Landmark Delivery Note

	Returns:
		Response from WhatsApp API
	"""
	doc = frappe.get_doc("Landmark Delivery Note", delivery_note_name)
	settings = frappe.get_single("Landmark Ops Settings")

	if not doc.whatsapp_number:
		frappe.throw(_("No WhatsApp number associated with this delivery note"))

	# Prepare items summary for display
	items_text = _build_items_summary(doc)

	# Build the message
	message = f"""📦 *Delivery Confirmation Required*

*Delivery Note:* {doc.delivery_note_no or 'N/A'}
*Customer:* {doc.customer_name or 'N/A'}
*Date:* {frappe.utils.formatdate(doc.delivery_date) if doc.delivery_date else 'N/A'}

*Items:*
{items_text}

Please review the items and quantities. Tap the button below to confirm or update quantities."""

	# Send interactive message with Flow button
	# Note: WhatsApp Flow requires a pre-configured Flow ID in WhatsApp Manager
	# For now, we'll send a simple text message with list
	response = send_whatsapp_message(
		to_number=doc.whatsapp_number,
		message=message,
		message_type="text"
	)

	# Update document status
	doc.status = "Awaiting Driver Confirmation"
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return response


def send_delivery_status_buttons(delivery_note_name: str) -> Dict[str, Any]:
	"""
	Send WhatsApp message with buttons for delivery status (Cash/Credit)

	Args:
		delivery_note_name: Name of the Landmark Delivery Note

	Returns:
		Response from WhatsApp API
	"""
	doc = frappe.get_doc("Landmark Delivery Note", delivery_note_name)
	settings = frappe.get_single("Landmark Ops Settings")

	if not doc.whatsapp_number:
		frappe.throw(_("No WhatsApp number associated with this delivery note"))

	message = f"""✅ *Items Confirmed*

*Delivery Note:* {doc.delivery_note_no or 'N/A'}
*Customer:* {doc.customer_name or 'N/A'}

Please select payment status:"""

	# Send interactive button message
	response = send_whatsapp_buttons(
		to_number=doc.whatsapp_number,
		message=message,
		buttons=[
			{
				"type": "reply",
				"reply": {
					"id": f"delivered_cash_{doc.name}",
					"title": "💵 Cash Received"
				}
			},
			{
				"type": "reply",
				"reply": {
					"id": f"delivered_credit_{doc.name}",
					"title": "📝 Credit"
				}
			}
		]
	)

	return response


def send_whatsapp_message(
	to_number: str,
	message: str,
	message_type: str = "text"
) -> Dict[str, Any]:
	"""
	Send a WhatsApp text message

	Args:
		to_number: Recipient WhatsApp number (with country code)
		message: Message text
		message_type: Type of message (default: "text")

	Returns:
		API response
	"""
	settings = frappe.get_single("Landmark Ops Settings")

	if not settings.whatsapp_api_base_url or not settings.whatsapp_api_token:
		frappe.throw(_("WhatsApp API not configured in Landmark Ops Settings"))

	# Clean phone number
	to_number = _clean_phone_number(to_number)

	# Construct API URL
	phone_number_id = settings.whatsapp_phone_number_id
	if not phone_number_id:
		frappe.throw(_("WhatsApp Phone Number ID not configured"))

	url = f"{settings.whatsapp_api_base_url.rstrip('/')}/{phone_number_id}/messages"

	headers = {
		"Authorization": f"Bearer {settings.get_password('whatsapp_api_token')}",
		"Content-Type": "application/json"
	}

	payload = {
		"messaging_product": "whatsapp",
		"recipient_type": "individual",
		"to": to_number,
		"type": message_type,
		"text": {
			"preview_url": False,
			"body": message
		}
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		response.raise_for_status()
		return response.json()
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			message=f"WhatsApp API Error: {str(e)}\n\nResponse: {getattr(e.response, 'text', 'No response')}",
			title="WhatsApp Send Error"
		)
		frappe.throw(_("Failed to send WhatsApp message: {0}").format(str(e)))


def send_whatsapp_buttons(
	to_number: str,
	message: str,
	buttons: List[Dict[str, Any]]
) -> Dict[str, Any]:
	"""
	Send WhatsApp interactive button message

	Args:
		to_number: Recipient WhatsApp number
		message: Header/body message
		buttons: List of button objects

	Returns:
		API response
	"""
	settings = frappe.get_single("Landmark Ops Settings")

	if not settings.whatsapp_api_base_url or not settings.whatsapp_api_token:
		frappe.throw(_("WhatsApp API not configured in Landmark Ops Settings"))

	to_number = _clean_phone_number(to_number)

	phone_number_id = settings.whatsapp_phone_number_id
	if not phone_number_id:
		frappe.throw(_("WhatsApp Phone Number ID not configured"))

	url = f"{settings.whatsapp_api_base_url.rstrip('/')}/{phone_number_id}/messages"

	headers = {
		"Authorization": f"Bearer {settings.get_password('whatsapp_api_token')}",
		"Content-Type": "application/json"
	}

	payload = {
		"messaging_product": "whatsapp",
		"recipient_type": "individual",
		"to": to_number,
		"type": "interactive",
		"interactive": {
			"type": "button",
			"body": {
				"text": message
			},
			"action": {
				"buttons": buttons[:3]  # WhatsApp allows max 3 buttons
			}
		}
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
		response.raise_for_status()
		return response.json()
	except requests.exceptions.RequestException as e:
		frappe.log_error(
			message=f"WhatsApp API Error: {str(e)}\n\nResponse: {getattr(e.response, 'text', 'No response')}",
			title="WhatsApp Button Send Error"
		)
		frappe.throw(_("Failed to send WhatsApp buttons: {0}").format(str(e)))


def _build_items_summary(doc) -> str:
	"""Build a text summary of items for WhatsApp message"""
	if not doc.items:
		return "_No items_"

	lines = []
	for idx, item in enumerate(doc.items, 1):
		item_name = item.item_name_short or item.item_name or "Item"
		qty = item.qty or 0
		lines.append(f"{idx}. {item_name} - *Qty: {qty}*")

	return "\n".join(lines)


def _clean_phone_number(phone: str) -> str:
	"""Clean and format phone number for WhatsApp API"""
	if not phone:
		return ""

	# Remove common separators
	phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

	# Ensure it starts with country code (assume UAE +971 if missing)
	if not phone.startswith("+"):
		if phone.startswith("971"):
			phone = "+" + phone
		elif phone.startswith("0"):
			phone = "+971" + phone[1:]
		else:
			phone = "+971" + phone

	# Remove + for API (some APIs need it without +, adjust based on your gateway)
	if phone.startswith("+"):
		phone = phone[1:]

	return phone


def send_confirmation_message(delivery_note_name: str, payment_type: str) -> Dict[str, Any]:
	"""
	Send final confirmation message to driver

	Args:
		delivery_note_name: Name of the Landmark Delivery Note
		payment_type: "Cash" or "Credit"

	Returns:
		API response
	"""
	doc = frappe.get_doc("Landmark Delivery Note", delivery_note_name)

	message = f"""✅ *Delivery Confirmed*

*Delivery Note:* {doc.delivery_note_no or 'N/A'}
*Customer:* {doc.customer_name or 'N/A'}
*Payment Type:* {payment_type}

Thank you! The delivery has been marked as complete."""

	return send_whatsapp_message(
		to_number=doc.whatsapp_number,
		message=message
	)

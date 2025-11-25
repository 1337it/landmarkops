# -*- coding: utf-8 -*-
# Copyright (c) 2025, Landmark and contributors
# For license information, please see license.txt

"""
API endpoints for WhatsApp integration
All endpoints are whitelisted for external access
"""

from __future__ import unicode_literals
import frappe
from frappe import _
import json
from typing import Dict, Any, Optional
from landmarkops.utils.azure_parser import parse_delivery_note_image
from landmarkops.utils.whatsapp_sender import (
	send_driver_review_flow,
	send_delivery_status_buttons,
	send_confirmation_message
)


@frappe.whitelist(allow_guest=True)
def whatsapp_inbound(**kwargs):
	"""
	Inbound WhatsApp webhook endpoint
	Receives messages from WhatsApp Business API

	Expected payload:
	{
		"from_number": "+9715xxxxxxxx",
		"media_url": "https://example.com/image.jpg",
		"message_id": "wamid.xxx",
		"timestamp": "2025-01-15T10:30:00Z"
	}

	Returns:
		Success/error response
	"""
	try:
		# Get payload from kwargs or request
		if not kwargs:
			kwargs = frappe.local.form_dict

		from_number = kwargs.get("from_number")
		media_url = kwargs.get("media_url")
		message_id = kwargs.get("message_id", "")
		timestamp = kwargs.get("timestamp", "")

		# Validate required fields
		if not from_number or not media_url:
			return {
				"success": False,
				"message": "Missing required fields: from_number and media_url"
			}

		# Log the inbound message
		capture_doc = frappe.get_doc({
			"doctype": "Landmark WhatsApp Capture",
			"whatsapp_message_id": message_id,
			"whatsapp_number": from_number,
			"media_url": media_url,
			"payload_json": json.dumps(kwargs, indent=2),
			"timestamp": timestamp or frappe.utils.now()
		})
		capture_doc.insert(ignore_permissions=True)

		# Look up driver from WhatsApp number
		driver_info = _lookup_driver_from_whatsapp(from_number)

		if not driver_info:
			frappe.log_error(
				message=f"No driver found for WhatsApp number: {from_number}",
				title="Driver Lookup Failed"
			)
			return {
				"success": False,
				"message": f"No driver found for WhatsApp number: {from_number}"
			}

		# Download and attach the image
		file_doc = _download_whatsapp_media(media_url, from_number)

		# Create Landmark Delivery Note
		delivery_note = frappe.get_doc({
			"doctype": "Landmark Delivery Note",
			"driver": driver_info.get("driver"),
			"whatsapp_number": from_number,
			"status": "Image Received",
			"source_file": file_doc.file_url if file_doc else media_url
		})
		delivery_note.insert(ignore_permissions=True)
		frappe.db.commit()

		# Link to capture log
		capture_doc.delivery_note = delivery_note.name
		capture_doc.save(ignore_permissions=True)
		frappe.db.commit()

		# Enqueue background job to process with Azure
		settings = frappe.get_single("Landmark Ops Settings")
		if settings.auto_process_images:
			frappe.enqueue(
				method="_process_delivery_note_async",
				queue="default",
				timeout=300,
				delivery_note_name=delivery_note.name,
				is_async=True
			)

		return {
			"success": True,
			"message": "Delivery note created successfully",
			"delivery_note": delivery_note.name
		}

	except Exception as e:
		frappe.log_error(
			message=f"WhatsApp Inbound Error: {str(e)}",
			title="WhatsApp Inbound API Error"
		)
		return {
			"success": False,
			"message": str(e)
		}


@frappe.whitelist(allow_guest=False)
def driver_confirm_items(**kwargs):
	"""
	Driver confirms/updates item quantities
	Called from WhatsApp Flow response

	Expected payload:
	{
		"delivery_note_name": "LDEL-0001",
		"items": [
			{"name": "LDEL-0001-1", "qty": 5},
			{"name": "LDEL-0001-2", "qty": 3}
		]
	}

	Returns:
		Success/error response
	"""
	try:
		if not kwargs:
			kwargs = frappe.local.form_dict

		delivery_note_name = kwargs.get("delivery_note_name")
		items = kwargs.get("items", [])

		if not delivery_note_name:
			return {
				"success": False,
				"message": "Missing delivery_note_name"
			}

		# Get the delivery note
		doc = frappe.get_doc("Landmark Delivery Note", delivery_note_name)

		# Update item quantities
		if items:
			for item_update in items:
				item_name = item_update.get("name")
				new_qty = item_update.get("qty")

				if item_name and new_qty is not None:
					for item in doc.items:
						if item.name == item_name:
							item.qty = float(new_qty)
							break

		# Mark as confirmed by driver
		doc.set_driver_confirmed()
		frappe.db.commit()

		# Send delivery status buttons (Cash/Credit)
		send_delivery_status_buttons(delivery_note_name)

		return {
			"success": True,
			"message": "Items confirmed successfully",
			"delivery_note": delivery_note_name
		}

	except Exception as e:
		frappe.log_error(
			message=f"Driver Confirm Items Error: {str(e)}",
			title="Driver Confirm API Error"
		)
		return {
			"success": False,
			"message": str(e)
		}


@frappe.whitelist(allow_guest=False)
def driver_delivery_status(**kwargs):
	"""
	Driver selects delivery status (Cash/Credit)
	Called from WhatsApp button callback

	Expected payload:
	{
		"delivery_note_name": "LDEL-0001",
		"action": "delivered_cash" or "delivered_credit"
	}

	Returns:
		Success/error response
	"""
	try:
		if not kwargs:
			kwargs = frappe.local.form_dict

		delivery_note_name = kwargs.get("delivery_note_name")
		action = kwargs.get("action", "").lower()

		if not delivery_note_name or not action:
			return {
				"success": False,
				"message": "Missing delivery_note_name or action"
			}

		# Get the delivery note
		doc = frappe.get_doc("Landmark Delivery Note", delivery_note_name)

		# Update delivery status based on action
		if action == "delivered_cash":
			doc.set_delivered("Cash")
			payment_type = "Cash"
		elif action == "delivered_credit":
			doc.set_delivered("Credit")
			payment_type = "Credit"
		else:
			return {
				"success": False,
				"message": f"Invalid action: {action}. Use 'delivered_cash' or 'delivered_credit'"
			}

		frappe.db.commit()

		# Send confirmation message
		send_confirmation_message(delivery_note_name, payment_type)

		return {
			"success": True,
			"message": f"Delivery marked as {payment_type}",
			"delivery_note": delivery_note_name,
			"payment_type": payment_type
		}

	except Exception as e:
		frappe.log_error(
			message=f"Driver Delivery Status Error: {str(e)}",
			title="Delivery Status API Error"
		)
		return {
			"success": False,
			"message": str(e)
		}


def _lookup_driver_from_whatsapp(whatsapp_number: str) -> Optional[Dict[str, Any]]:
	"""
	Look up driver from WhatsApp number using Whatsapp Contact Link

	Args:
		whatsapp_number: WhatsApp number to lookup

	Returns:
		Dictionary with driver info or None
	"""
	settings = frappe.get_single("Landmark Ops Settings")
	link_doctype = settings.driver_link_doctype or "Whatsapp Contact Link"
	driver_field = settings.driver_link_fieldname or "driver"

	# Clean phone number for comparison
	clean_number = whatsapp_number.replace("+", "").replace(" ", "").replace("-", "")

	# Try to find matching contact
	# Note: Adjust the field names based on actual Whatsapp Contact Link structure
	contacts = frappe.get_all(
		link_doctype,
		filters={
			"whatsapp_number": ["like", f"%{clean_number[-10:]}%"]  # Match last 10 digits
		},
		fields=["name", driver_field, "whatsapp_number"],
		limit=1
	)

	if contacts:
		contact = contacts[0]
		return {
			"driver": contact.get(driver_field),
			"contact_link": contact.name,
			"whatsapp_number": contact.whatsapp_number
		}

	return None


def _download_whatsapp_media(media_url: str, whatsapp_number: str) -> Optional[Any]:
	"""
	Download media from WhatsApp and save as File in Frappe

	Args:
		media_url: URL to the media file
		whatsapp_number: WhatsApp number (for logging)

	Returns:
		File document or None
	"""
	try:
		import requests
		from frappe.utils.file_manager import save_url

		# Download and save the file
		file_doc = save_url(
			file_url=media_url,
			docname=None,
			folder="Home/Attachments"
		)

		return file_doc

	except Exception as e:
		frappe.log_error(
			message=f"Media Download Error: {str(e)}\nURL: {media_url}",
			title="WhatsApp Media Download Error"
		)
		return None


def _process_delivery_note_async(delivery_note_name: str):
	"""
	Background job to process delivery note with Azure Document Intelligence

	Args:
		delivery_note_name: Name of the Landmark Delivery Note
	"""
	try:
		# Call Azure to parse the document
		parse_delivery_note_image(delivery_note_name)

		# Send WhatsApp Flow to driver
		settings = frappe.get_single("Landmark Ops Settings")
		if settings.send_flow_after_parse:
			send_driver_review_flow(delivery_note_name)

	except Exception as e:
		frappe.log_error(
			message=f"Processing Error: {str(e)}\nDelivery Note: {delivery_note_name}",
			title="Delivery Note Processing Error"
		)
		# Update status to indicate error
		doc = frappe.get_doc("Landmark Delivery Note", delivery_note_name)
		doc.add_comment("Comment", f"Processing failed: {str(e)}")
		frappe.db.commit()


# Register the async method for enqueue
frappe.whitelist()
def process_delivery_note_async(delivery_note_name: str):
	"""Public wrapper for background processing"""
	return _process_delivery_note_async(delivery_note_name)

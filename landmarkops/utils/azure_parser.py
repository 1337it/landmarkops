# -*- coding: utf-8 -*-
# Copyright (c) 2025, Landmark and contributors
# For license information, please see license.txt

"""
Azure Document Intelligence integration for parsing delivery notes
"""

from __future__ import unicode_literals
import frappe
from frappe import _
import requests
import json
import time
from typing import Dict, Any, Optional


def parse_delivery_note_image(delivery_note_name: str) -> Dict[str, Any]:
	"""
	Parse delivery note image using Azure Document Intelligence

	Args:
		delivery_note_name: Name of the Landmark Delivery Note document

	Returns:
		Dictionary with parsed results
	"""
	doc = frappe.get_doc("Landmark Delivery Note", delivery_note_name)
	settings = frappe.get_single("Landmark Ops Settings")

	# Validate settings
	if not settings.azure_endpoint or not settings.azure_api_key:
		frappe.throw(_("Azure Document Intelligence not configured in Landmark Ops Settings"))

	# Get the image file URL
	if not doc.source_file:
		frappe.throw(_("No source file attached to delivery note"))

	file_url = frappe.utils.get_url(doc.source_file)

	# Call Azure Document Intelligence
	azure_result = call_azure_document_intelligence(
		endpoint=settings.azure_endpoint,
		api_key=settings.get_password("azure_api_key"),
		model_id=settings.azure_model_id or "prebuilt-document",
		document_url=file_url,
		timeout=settings.azure_timeout or 120,
		max_retries=settings.azure_max_retries or 3
	)

	# Save raw JSON to the document
	doc.raw_azure_json = json.dumps(azure_result, indent=2)
	doc.azure_operation_id = azure_result.get("operation_id", "")

	# Parse the Azure response and update fields
	parse_azure_response(doc, azure_result)

	# Update status
	doc.status = "Parsed"
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {"success": True, "message": "Document parsed successfully"}


def call_azure_document_intelligence(
	endpoint: str,
	api_key: str,
	model_id: str,
	document_url: str,
	timeout: int = 120,
	max_retries: int = 3
) -> Dict[str, Any]:
	"""
	Call Azure Document Intelligence API to analyze document

	Args:
		endpoint: Azure endpoint URL
		api_key: Azure API key
		model_id: Model ID (e.g., 'prebuilt-document')
		document_url: URL to the document image
		timeout: Request timeout in seconds
		max_retries: Maximum number of retries

	Returns:
		Parsed JSON response from Azure
	"""
	# Remove trailing slash from endpoint
	endpoint = endpoint.rstrip("/")

	# Construct the analyze URL
	analyze_url = f"{endpoint}/formrecognizer/documentModels/{model_id}:analyze?api-version=2023-07-31"

	headers = {
		"Ocp-Apim-Subscription-Key": api_key,
		"Content-Type": "application/json"
	}

	payload = {
		"urlSource": document_url
	}

	# Submit the analysis request
	for attempt in range(max_retries):
		try:
			response = requests.post(
				analyze_url,
				headers=headers,
				json=payload,
				timeout=30
			)
			response.raise_for_status()
			break
		except requests.exceptions.RequestException as e:
			if attempt == max_retries - 1:
				frappe.log_error(
					message=f"Azure API request failed after {max_retries} attempts: {str(e)}",
					title="Azure Document Intelligence Error"
				)
				frappe.throw(_("Failed to submit document to Azure: {0}").format(str(e)))
			time.sleep(2 ** attempt)  # Exponential backoff

	# Get the operation location from the response headers
	operation_location = response.headers.get("Operation-Location") or response.headers.get("apim-request-id")

	if not operation_location and "Operation-Location" not in response.headers:
		# For some API versions, we need to construct the result URL
		operation_location = response.headers.get("apim-request-id")

	# Poll for results
	if operation_location:
		result = poll_for_results(operation_location, api_key, timeout)
	else:
		# Some versions return results directly
		result = response.json()

	result["operation_id"] = operation_location or ""
	return result


def poll_for_results(operation_location: str, api_key: str, timeout: int) -> Dict[str, Any]:
	"""
	Poll Azure for analysis results

	Args:
		operation_location: URL to poll for results
		api_key: Azure API key
		timeout: Maximum time to wait in seconds

	Returns:
		Analysis results
	"""
	headers = {
		"Ocp-Apim-Subscription-Key": api_key
	}

	start_time = time.time()
	while time.time() - start_time < timeout:
		try:
			response = requests.get(operation_location, headers=headers, timeout=30)
			response.raise_for_status()
			result = response.json()

			status = result.get("status", "").lower()

			if status == "succeeded":
				return result
			elif status == "failed":
				error = result.get("error", {})
				frappe.throw(_("Azure analysis failed: {0}").format(error.get("message", "Unknown error")))
			elif status in ["running", "notstarted"]:
				time.sleep(2)
			else:
				frappe.throw(_("Unexpected status from Azure: {0}").format(status))

		except requests.exceptions.RequestException as e:
			frappe.log_error(
				message=f"Error polling Azure results: {str(e)}",
				title="Azure Polling Error"
			)
			time.sleep(2)

	frappe.throw(_("Azure analysis timed out after {0} seconds").format(timeout))


def parse_azure_response(doc, azure_result: Dict[str, Any]) -> None:
	"""
	Parse Azure Document Intelligence response and update Landmark Delivery Note

	Args:
		doc: Landmark Delivery Note document
		azure_result: Raw Azure response
	"""
	try:
		analyze_result = azure_result.get("analyzeResult", {})

		# Extract key-value pairs
		key_value_pairs = extract_key_value_pairs(analyze_result)

		# Map fields from Azure response to document fields
		field_mapping = {
			"delivery note number": "delivery_note_no",
			"delivery note no": "delivery_note_no",
			"dn no": "delivery_note_no",
			"date": "delivery_date",
			"sales order number": "sales_order_no",
			"sales order no": "sales_order_no",
			"so no": "sales_order_no",
			"sales responsible": "sales_responsible",
			"delivery mode": "delivery_mode",
			"customer code": "customer_code",
			"customer name": "customer_name",
			"phone": "customer_phone",
			"customer reference": "customer_reference",
			"delivery address": "delivery_address",
			"address": "delivery_address"
		}

		# Update header fields
		for azure_key, doc_field in field_mapping.items():
			value = key_value_pairs.get(azure_key.lower())
			if value and not doc.get(doc_field):
				doc.set(doc_field, value)

		# Extract table data for line items
		tables = analyze_result.get("tables", [])
		if tables:
			parse_items_table(doc, tables[0])  # Assuming first table is items

	except Exception as e:
		frappe.log_error(
			message=f"Error parsing Azure response: {str(e)}\n\nResponse: {json.dumps(azure_result, indent=2)}",
			title="Azure Response Parsing Error"
		)
		frappe.throw(_("Failed to parse Azure response: {0}").format(str(e)))


def extract_key_value_pairs(analyze_result: Dict[str, Any]) -> Dict[str, str]:
	"""Extract key-value pairs from Azure response"""
	pairs = {}

	# Try keyValuePairs first (prebuilt-document model)
	for kv in analyze_result.get("keyValuePairs", []):
		if kv.get("key") and kv.get("value"):
			key_text = kv["key"].get("content", "").lower().strip()
			value_text = kv["value"].get("content", "").strip()
			if key_text and value_text:
				pairs[key_text] = value_text

	# Also try documents/fields structure
	for document in analyze_result.get("documents", []):
		for field_name, field_data in document.get("fields", {}).items():
			if isinstance(field_data, dict) and "content" in field_data:
				pairs[field_name.lower()] = field_data["content"]
			elif isinstance(field_data, dict) and "valueString" in field_data:
				pairs[field_name.lower()] = field_data["valueString"]

	return pairs


def parse_items_table(doc, table: Dict[str, Any]) -> None:
	"""
	Parse items table from Azure response

	Args:
		doc: Landmark Delivery Note document
		table: Table data from Azure
	"""
	# Clear existing items
	doc.items = []

	# Get table structure
	row_count = table.get("rowCount", 0)
	column_count = table.get("columnCount", 0)
	cells = table.get("cells", [])

	if row_count == 0 or column_count == 0:
		return

	# Build table grid
	grid = [[None for _ in range(column_count)] for _ in range(row_count)]

	for cell in cells:
		row_idx = cell.get("rowIndex", 0)
		col_idx = cell.get("columnIndex", 0)
		content = cell.get("content", "").strip()

		if row_idx < row_count and col_idx < column_count:
			grid[row_idx][col_idx] = content

	# Identify column headers (first row)
	headers = [str(h).lower().strip() if h else "" for h in grid[0]]

	# Map column indices
	col_map = {}
	for idx, header in enumerate(headers):
		if "sr" in header or "no" in header and len(header) < 10:
			col_map["sr_no"] = idx
		elif "item id" in header or "itemid" in header:
			col_map["item_id"] = idx
		elif "flexi" in header:
			col_map["flexi_code"] = idx
		elif "item name" in header or "description" in header:
			col_map["item_name"] = idx
		elif "unit" in header and "qty" not in header:
			col_map["unit"] = idx
		elif "qty" in header or "quantity" in header:
			col_map["qty"] = idx
		elif "carton" in header:
			col_map["cartons"] = idx

	# Parse data rows (skip header)
	for row_idx in range(1, row_count):
		row = grid[row_idx]

		# Skip empty rows
		if not any(row):
			continue

		item = {
			"sr_no": safe_int(row[col_map.get("sr_no", 0)]) if "sr_no" in col_map else row_idx,
			"item_id": row[col_map.get("item_id", 1)] if "item_id" in col_map else "",
			"flexi_code": row[col_map.get("flexi_code", -1)] if "flexi_code" in col_map else "",
			"item_name": row[col_map.get("item_name", 2)] if "item_name" in col_map else "",
			"unit": row[col_map.get("unit", -1)] if "unit" in col_map else "",
			"qty": safe_float(row[col_map.get("qty", 3)]) if "qty" in col_map else 0.0,
			"cartons": safe_float(row[col_map.get("cartons", -1)]) if "cartons" in col_map else 0.0
		}

		# Only add if we have at least item name or item ID
		if item["item_name"] or item["item_id"]:
			doc.append("items", item)


def safe_int(value: Any, default: int = 0) -> int:
	"""Safely convert value to integer"""
	if value is None or value == "":
		return default
	try:
		return int(float(str(value).replace(",", "")))
	except (ValueError, TypeError):
		return default


def safe_float(value: Any, default: float = 0.0) -> float:
	"""Safely convert value to float"""
	if value is None or value == "":
		return default
	try:
		return float(str(value).replace(",", ""))
	except (ValueError, TypeError):
		return default


def test_azure_connection():
	"""Test Azure Document Intelligence connection"""
	settings = frappe.get_single("Landmark Ops Settings")

	if not settings.azure_endpoint or not settings.azure_api_key:
		print("Azure Document Intelligence not configured")
		return

	print(f"Testing connection to: {settings.azure_endpoint}")
	print(f"Model ID: {settings.azure_model_id}")

	# Test with a simple API call
	try:
		url = f"{settings.azure_endpoint.rstrip('/')}/formrecognizer/documentModels?api-version=2023-07-31"
		headers = {
			"Ocp-Apim-Subscription-Key": settings.get_password("azure_api_key")
		}
		response = requests.get(url, headers=headers, timeout=10)
		response.raise_for_status()
		print("✓ Connection successful!")
		return True
	except Exception as e:
		print(f"✗ Connection failed: {str(e)}")
		return False

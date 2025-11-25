# -*- coding: utf-8 -*-
# Copyright (c) 2025, Landmark and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now, get_datetime

class LandmarkDeliveryNote(Document):
	"""Main DocType for Landmark delivery notes from WhatsApp"""

	def validate(self):
		"""Validate the document before saving"""
		self.validate_status_flow()
		self.validate_items_for_confirmation()
		self.validate_payment_type()
		self.generate_short_item_names()

	def validate_status_flow(self):
		"""Ensure status changes follow logical flow"""
		valid_status_flow = {
			"Image Received": ["Parsed", "Awaiting Driver Confirmation"],
			"Parsed": ["Awaiting Driver Confirmation"],
			"Awaiting Driver Confirmation": ["Confirmed by Driver"],
			"Confirmed by Driver": ["Delivered - Cash Received", "Delivered - Credit"],
			"Delivered - Cash Received": [],  # Terminal state
			"Delivered - Credit": []  # Terminal state
		}

		if self.is_new():
			return

		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.status != self.status:
			allowed_statuses = valid_status_flow.get(old_doc.status, [])
			if self.status not in allowed_statuses:
				frappe.throw(
					_("Cannot change status from {0} to {1}").format(
						old_doc.status, self.status
					)
				)

	def validate_items_for_confirmation(self):
		"""Ensure at least one item exists before confirming"""
		confirmation_statuses = [
			"Confirmed by Driver",
			"Delivered - Cash Received",
			"Delivered - Credit"
		]

		if self.status in confirmation_statuses and not self.items:
			frappe.throw(_("Cannot confirm delivery without any items"))

	def validate_payment_type(self):
		"""Ensure payment type is set for delivered status"""
		if self.status in ["Delivered - Cash Received", "Delivered - Credit"]:
			if self.status == "Delivered - Cash Received" and self.payment_type != "Cash":
				self.payment_type = "Cash"
			elif self.status == "Delivered - Credit" and self.payment_type != "Credit":
				self.payment_type = "Credit"

	def generate_short_item_names(self):
		"""Generate shortened item names for WhatsApp display"""
		for item in self.items:
			if item.item_name and not item.item_name_short:
				# Truncate to 40 characters for WhatsApp display
				item.item_name_short = item.item_name[:40]
				if len(item.item_name) > 40:
					item.item_name_short += "..."

	def set_driver_confirmed(self):
		"""Mark as confirmed by driver"""
		self.status = "Confirmed by Driver"
		self.driver_confirmed_at = now()
		self.save(ignore_permissions=True)

	def set_delivered(self, payment_type):
		"""Mark as delivered with payment type"""
		if payment_type == "Cash":
			self.status = "Delivered - Cash Received"
			self.payment_type = "Cash"
		elif payment_type == "Credit":
			self.status = "Delivered - Credit"
			self.payment_type = "Credit"
		else:
			frappe.throw(_("Invalid payment type: {0}").format(payment_type))

		self.delivered_at = now()
		self.save(ignore_permissions=True)

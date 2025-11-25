# -*- coding: utf-8 -*-
# Copyright (c) 2025, Landmark and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class LandmarkOpsSettings(Document):
	"""Single DocType for Landmark Ops configuration"""
	pass

def get_settings():
	"""Helper function to get Landmark Ops Settings"""
	if not frappe.db.exists("Landmark Ops Settings", "Landmark Ops Settings"):
		settings = frappe.new_doc("Landmark Ops Settings")
		settings.insert(ignore_permissions=True)

	return frappe.get_single("Landmark Ops Settings")

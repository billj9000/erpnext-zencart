# Copyright (c) 2022, Bill Jones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

class ZenCartStore(Document):
	def validate(self):
		if self.enabled == 1:
			setup_custom_fields()
			self.validate_access_credentials()

	def validate_access_credentials(self):
		if not (self.get_password('zencart_password') and self.zencart_user and self.zencart_url):
			frappe.msgprint(
				_("Missing value for User Name, Password, or Zen Cart URL"), raise_exception=frappe.ValidationError
			)


def setup_custom_fields():
	custom_fields = {
		"Sales Order": [
			dict(
				fieldname="zencart_order",
				label="Zen Cart Order",
				fieldtype="Data",
				insert_after="title",
				read_only=1,
				print_hide=1,
			),
			dict(
				fieldname="zencart_id",
				label="Zen Cart Store",
				fieldtype="Link",
				options="Zen Cart Store",
				insert_after="zencart_order",
				read_only=1,
				print_hide=1,
			),
		],
	}

	create_custom_fields(custom_fields)

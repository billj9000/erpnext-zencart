# Copyright (c) 2022, Bill Jones and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import logger, get_url
from frappe.geo.country_info import get_country_info

import erpnext
from erpnext.stock.utils import get_latest_stock_qty
from erpnext.utilities.product import get_price
import requests
import json
import base64
import os
from urllib.parse import urlparse

from zencart.orders import process_orders

# Test connection by retrieving version information from Zen Cart
@frappe.whitelist()
def test( store_name ):
#	logger = frappe.logger("zencart", allow_site=True, file_count=50)
#	logger.debug( f"Settings: " + settings_name )
	
	store = frappe.get_doc( "Zen Cart Store", store_name )
	url = store.zencart_url + '/erpnext-zencart.php?user=' + store.zencart_user + '&pass=' + store.get_password('zencart_password') + '&task=version'
	x = requests.get( url )

	return x.text

# Poll the Zen Cart server
def poll_connection( store_name ):
	store = frappe.get_doc( "Zen Cart Store", store_name )
#	logger = frappe.logger("zencart", allow_site=True, file_count=50)
#	logger.debug( f"Polling Zen Cart: " + store.name )
	if( store.enabled ):
		url = store.zencart_url + '/erpnext-zencart.php?user=' + store.zencart_user + '&pass=' + store.get_password('zencart_password') + '&task=orders&last_order=' + str(store.last_order_number)
		x = requests.get( url )
		process_orders( store, json.loads(x.text)['orders'] )

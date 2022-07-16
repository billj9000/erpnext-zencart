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

# Update item quantities
# items is a list of Item SKUs
@frappe.whitelist()
def updateItemQuantity( items ):
	# For some reason, the array might come through as a JSON string
	# instead of a Python object
	if isinstance(items, str):
		items = json.loads(items)

	x = ''
	store_list = frappe.get_all( "Zen Cart Store" )
	for s in store_list:
		store = frappe.get_doc( "Zen Cart Store", s )
		if store.enabled:
			url = store.zencart_url + '/erpnext-zencart.php?user=' + store.zencart_user + '&pass=' + store.get_password('zencart_password') + '&task=updateProductsQty'
			products = []
			for item_code in items:
				website_item = frappe.get_last_doc( 'Website Item', filters={"item_code": item_code} )
				if website_item.published:
					qty = erpnext.stock.utils.get_latest_stock_qty( item_code, store.stock_warehouse )
					products.append( {'products_model': item_code, 'quantity': qty} )

			postdata = {'products': products}

			x += requests.post( url, data = json.dumps(postdata) ).text

	return x


# Update items
# items is a list of Item SKUs
@frappe.whitelist()
def updateItem( items ):
	# For some reason, the array might come through as a JSON string
	# instead of a Python object
	# If so, decode it
	if isinstance(items, str):
		items = json.loads(items)

	x = ''
	store_list = frappe.get_all( "Zen Cart Store" )
	for s in store_list:
		store = frappe.get_doc( "Zen Cart Store", s )
		if store.enabled:
			url = store.zencart_url + '/erpnext-zencart.php?user=' + store.zencart_user + '&pass=' + store.get_password('zencart_password') + '&task=updateProducts'
			products = []
			for item_code in items:
				website_item = frappe.get_last_doc( 'Website Item', filters={"item_code": item_code} )
				if website_item.published:
					item = frappe.get_doc( "Item", item_code )
					qty = erpnext.stock.utils.get_latest_stock_qty( item_code, store.stock_warehouse )

					# Get the image:
					#	1st choice, the uploaded website image
					#	2nd choice, the Website Item document image
					#	3rd choice, the document image for the linked Item document
					if website_item.website_image:
						image = website_item.website_image
					elif website_item.image:
						image = website_item.image
					else:
						image = item.image

					# Other bits and pieces
					if item.country_of_origin:
						coo = get_country_info( item.country_of_origin )['code'].upper()
					else:
						coo = ''

					if item.customs_tariff_number:
						hs_code = item.customs_tariff_number
					else:
						hs_code = ''

					products.append(
						{
							'products_model': item_code,
							'productVirtual': 0,
							'productStatus': 0 if item.disabled else 1,
							'productFreeShipping': 0,
							'productHidePrice': 0,
							'productCategory': store.zen_cart_category,
							#'productSortOrder': 0,										# Todo: - need to add sort order to document - custom field in website_item?
							'productType': 'Product - General',
							'productName': website_item.short_description,
							'productDescription': website_item.short_description,
							#'productURL': $result->fields['ProductURL'],				# Todo: - need to add product URL to document
							'productImageDirectory': '',								# Put all images in top-level 'images' directory
							'productImageFileName': os.path.basename(urlparse(frappe.utils.get_url(image)).path) if image else '',
							'productImageData': base64.urlsafe_b64encode(requests.get(frappe.utils.get_url(image)).content).decode() if image else '',
							'productTaxable': True,										# Todo: - need to work out if product is taxable - custom field in website_item?
							'taxClassType': 'VAT',										# Todo: - need to figure out what the tax class is - custom field in website_item?
							'msrPrice': erpnext.utilities.product.get_price( item_code, store.price_list, store.customer_group, store.company, 1 ).price_list_rate,
							'retailPrice': erpnext.utilities.product.get_price( item_code, store.price_list, store.customer_group, store.company, 1 ).price_list_rate,
							'priceDiscountType': 0,										# Clear qty discount flag
							'productWeight': item.weight_per_unit,
							'dateAdded': str(item.creation),
							'dateUpdated': str(item.modified),
		#					'dateAvailable': ,											# Todo: Work out when product will be available
							'quantity': qty if qty>= 0 else 0,
							'manufacturer': item.brand,

							# CUSTOM FIELDS

							# Set the inventory type. This is a standard inventory field but is not exported
							# to ZenCart by default.
							# Will be 'si' for a stock item, 'ns' for a non-stock item. May be some other type.
							# Need to set quantity to 9999 for 'ns', or to supplied qty for any other type
							# Todo:
							# 'productInventoryType': $result->fields['inventory_type'],

							# Set the ZenCart HTML description
							'productZencartDescription': website_item.web_long_description,

							# Set the ZenCart sort order
							# Todo:
							# 'productZencartSortOrder': $result->fields['zencart_sort_order'],

							# Set the ZenCart OEM part numbers
							'productZencartOemPartnumbers': item.oem_part_numbers,

							# Set the ZenCart Condition field
							# Todo:
							# 'productZencartCondition': $result->fields['zencart_condition'],

							# Set the product Dimension units
							# Todo: do we need this?
							# 'productZencartDimUnits': $result->fields['zencart_dim_unit'],

							# Set the product Length
							'productZencartLength': item.length,

							# Set the product Width
							'productZencartWidth': item.width,

							# Set the product Height
							'productZencartHeight': item.height,

							# Set the "ready to ship" field
							# Todo: do we need this?
							# 'productZencartReadyToShip': $result->fields['zencart_ready_to_ship'],

							# Set the HS code
							'productHsCode': hs_code,

							# Set the country of origin
							'productCountryOrigin': coo,
							}
							)

			postdata = {'products': products}

			x += requests.post( url, data = json.dumps(postdata) ).text

	return x


# Called when item bin has changed (usually the quantity)
def bin_on_change( doc, handler="" ):
	store_list = frappe.get_all( "Zen Cart Store" )
	for s in store_list:
		store = frappe.get_doc( "Zen Cart Store", s )
		if store.update_stock and store.stock_warehouse == doc.warehouse:
			items = [doc.item_code]
			updateItemQuantity( store.name, items )
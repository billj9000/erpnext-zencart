# Copyright (c) 2022, Bill Jones and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import logger, get_url
from frappe.geo.country_info import get_country_info
from frappe.desk.form.linked_with import get_linked_docs, get_linked_doctypes

import erpnext
from erpnext.stock.utils import get_latest_stock_qty
from erpnext.utilities.product import get_price
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
import json

import time
import random


def create_address( customer, address, type, email_id, phone ):
    doc = frappe.get_doc( {
        'doctype': 'Address',
        'name': customer.customer_name,
        'address_title': customer.customer_name,
        'email_id': email_id,
        'address_type': type,
        'phone': phone,
        'business_name': address['company'],
        'address_line1': address['addr1'],
        'address_line2': address['addr2'],
        'city': address['city'],
        'state': address['state'],
        'country': address['country'],
        'pincode': address['postalCode'],
        'links': [{'link_doctype': 'Customer', 'link_name': customer.name, 'link_title': customer.customer_name}],
    })

    doc.insert()
    return doc

def create_customer( order, store ):
    doc = frappe.get_doc({
        "doctype": "Customer",
        "name": order["email"],
        "title": order["email"],
        "customer_name": order['customerAddress']['name'],
        "customer_group": store.customer_group,
        "territory": store.territory,
        "type": "Individual" if order['customerAddress']['company']  == '' else "Company",
        "customer_primary_contact": {
            "first_name": order['customerAddress']['name'],
            "email_id": order['email'],
            "mobile_no": order['phone'],
        },
        "customer_primary_address": {
            "email_id": order['email'],
            "phone": order['phone'],
            "address_type": 'Other',
            "is_primary_address": 0,
            "is_shipping_address": 0,
            "business_name": order['customerAddress']['company'],
            "address_line1": order['customerAddress']['addr1'],
            "address_line2": order['customerAddress']['addr2'],
            "city": order['customerAddress']['city'],
            "state": order['customerAddress']['state'],
            "country": order['customerAddress']['country'],
            "pincode": order['customerAddress']['postalCode'],
        },
    })

    doc.insert()
    return doc

# Get all addresses linked to a customer with supplied name
def get_customer_addresses( customer, order ):
    logger = frappe.logger("zencart", allow_site=True, file_count=50)
    logger.propagate=False
    logger.debug( 'Searching for addresses for customer: ' + customer.name )

    billing_address = None
    shipping_address = None
    address_links = frappe.get_all('Address', filters=[['Dynamic Link','link_name','=',customer.name]] )
    for address_link in address_links:
        doc = frappe.get_doc( 'Address', address_link.name )
        logger.debug( ' Address name: ' + doc.name )
        logger.debug( ' Address: ' + str(doc) )
        logger.debug( ' Line 1: ' + str(doc.address_line1) )
        logger.debug( ' Country: ' + str(doc.country) )
        logger.debug( ' Postcode: ' + str(doc.pincode) )
        # See if we already have the shipping and billing addresses
        # Check if it is shipping/billing and if it matches the order's shipping/billing addresses
        if doc.address_type == 'Billing':
            if billing_address is None:
                if doc.address_line1.lower() == order['billingAddress']['addr1'].lower() and doc.pincode.lower() == order['billingAddress']['postalCode'].lower() and doc.country.lower() == order['billingAddress']['country'].lower():
                    billing_address = doc
                    logger.debug( 'Billing address match: ' + doc.name )
        elif doc.address_type == 'Shipping':
            if shipping_address is None:
                if doc.address_line1.lower() == order['shippingAddress']['addr1'].lower() and doc.pincode.lower() == order['shippingAddress']['postalCode'].lower() and doc.country.lower() == order['shippingAddress']['country'].lower():
                    shipping_address = doc
                    logger.debug( 'Shipping address match: ' + doc.name )

    # If either address is missing, create it
    if billing_address is None:
        billing_address = create_address( customer, order['billingAddress'], 'Billing', order['email'], order['phone'] )
        logger.debug( 'Created new billing address: ' + billing_address.name )

    if shipping_address is None:
        shipping_address = create_address( customer, order['shippingAddress'], 'Shipping', order['email'], order['phone'] )
        logger.debug( 'Created new shipping address: ' + shipping_address.name )

    return {'billing': billing_address, 'shipping': shipping_address}


# Get the customer from the customer ID in the order (or create it if not found)
# We use the e-mail address as customer ID as it should be unique
def get_customer( order, store ):
    if not frappe.db.exists('Customer', order["email"]):
        customer = create_customer( order, store )
    else:
        customer = frappe.get_doc( 'Customer', order["email"] )

    return customer


def get_item_tax( zc_tax, store ):
    for tax in store.item_tax:
        if float(zc_tax) == tax.zen_cart_tax:
            return tax.tax_template

    # No tax found if get to here
    return ''

def process_orders( store, orders ):
    frappe.utils.logger.set_log_level("DEBUG")
    logger = frappe.logger("zencart", allow_site=True, file_count=50)
    if len(orders) > 0:
        logger.debug( 'Number of orders: ' + str(len(orders)) )

    for order in orders:
        logger.debug( 'Creating Sales Order: ' + store.order_number_prefix + str(order['orderId']) )
        logger.debug( 'Transaction date/time: ' + order['orderDate'] )
        logger.debug( 'Country code: ' + order['customerAddress']['country'] )
 
        items = []
        max_tax_rate = 0.0
        for item in order['items']:
            tax_rate = float(item['tax'])
            if tax_rate > max_tax_rate:
                max_tax_rate = tax_rate

            new_item = {
                    # SAABits-specific - remove 'SAAB-' prefix from special-order items
                    "item_code": item['sku'].replace( 'SAAB-', ''),
                    "qty": item['quantity'],
                    "rate": item['unitPrice'],
                }

            # SAABits-specific: only use supplied description if item is not special-order part
            if not 'SAAB-' in item['sku']:
                new_item["description"] = item['name']
            elif not frappe.db.exists( 'Item', new_item['item_code'] ):
                # Is a special-order part and we don't yet have it in the inventory
                # create new item new_item['item_code'] with description item['name']
                item_doc = frappe.get_doc({
                    'doctype': 'Item',
                    'item_code': new_item['item_code'],
                    'item_name': item['name'],
                    'item_group': 'Stock',
                    'stock_uom': 'Each',
                    'is_stock_item': 1,
                    'brand': 'SAAB',
                    'description': item['name'],
                    'default_material_request_type': 'Purchase',
                    'item_defaults': [{
                        'company': store.company,
                        'default_warehouse': store.stock_warehouse,
                        'default_supplier': 'Orio',
                    }],
                    'is_purchase_item': 1,
                    'supplier_items': [{
                        'supplier': 'Orio',
                        'supplier_part_no': new_item['item_code'],
                    }],
                    'is_sales_item': 1,
                })

                item_doc.insert()

            items.append( new_item )


        tax_template_name = get_item_tax( max_tax_rate, store )
        logger.debug( 'Max tax rate: ' + str(max_tax_rate) + ' Tax template: ' + tax_template_name )

        customer = get_customer( order, store )
        logger.debug( 'Customer: ' + customer.name )
        addresses = get_customer_addresses( customer, order )

        so = frappe.get_doc({
            "doctype": "Sales Order",
            "order_type": "Sales",
#            "name": store.order_number_prefix + str(order['orderId']),
            "title": store.order_number_prefix + str(order['orderId']),
            "zencart_order": str(order['orderId']),
            "zencart_id": store.name,
            "conversion_rate": float(order['conversion_rate']),
            "customer": customer.name,
            "customer_address": addresses['billing'].name,
            "shipping_address_name": addresses['shipping'].name,
            "company": store.company,
            "transaction_date": order['orderDate'],
            "currency": order['currency'],
            "status": "To Deliver",
            "set_warehouse": store.stock_warehouse,
            "ignore_pricing_rule": 1,
            "delivery_date": order['orderDate'],
            "taxes_and_charges": tax_template_name,
            "items": items,
#            "discount_amount": float(order['net_discount']),    # Currently not working. Need to add discount percentage too?
#            "apply_discount_on": 'Net Total',
        })

        # Add taxes
        _set_sales_taxes_and_charges( so )

        logger.debug( 'Created' )

        # TODO: Compare Grand Total with order['totalAmount'] and add an adjustment if different
        ###### Do this as a payment correction in payment entry instead! #######
        # Adjustment = order['totalAmount'] - so.grand_total
        # If can't find an adjustment field, perhaps add as an item with an item tax rate of 0%?
        # Think this may need to be done after insert() as grand_total doesn't seem to exist before then


        so.insert()
        logger.debug( 'Inserted ' + so.name + ', total £' + str(so.grand_total) )
        so.submit()
        logger.debug( 'Submitted ' + so.name + ', total £' + str(so.grand_total) )

        if store.create_invoice:
            # Create invoice
            si = make_sales_invoice( so.name )
            si.posting_date = so.transaction_date
            if store.create_dn == 0:
                si.update_stock = store.invoice_update_stock

            si.insert()
            logger.debug( 'Inserted ' + si.name + ', total £' + str(si.grand_total) )
            si.submit()
            logger.debug( 'Submitted ' + si.name + ', total £' + str(si.grand_total) )

            # Create payment entry

            # Find the payment method if we have one
            for payment_method in store.payment_method:
                if order["paymentModule"] == payment_method.payment_module_code and order["currency"] == payment_method.currency:
                    mop = frappe.get_doc( 'Mode of Payment', payment_method.mode_of_payment )

                    # If we have a mode of payment for this order, then create a payment entry
                    for account in mop.accounts:
                        if account.company == store.company:
                            payment_reference_list = [{
                                "reference_doctype":"Sales Invoice",
                                "reference_name" : si.name,
                                'total_amount': order['totalAmount'],
                                'outstanding_amount': order['totalAmount'],
                                "allocated_amount": order['totalAmount'],
                            }]

                            pe = frappe.get_doc({
                                'doctype': 'Payment Entry',
                                'payment_type': 'Receive',
                                'posting_date': so.transaction_date,
                                'mode_of_payment': mop.name,
                                'party_type': 'Customer',
                                'party': customer.name,
                                'party_name': customer.customer_name,
                                'paid_to': account.default_account,
                                'paid_to_account_currency': si.currency,
                                'paid_amount': order['totalAmount'],
                                'received_amount': order['totalAmount'],
                                'reference_no': order['paymentRef'],
                                'reference_date': so.transaction_date,
                                'references': payment_reference_list,
                            })

                            logger.debug( 'Created payment entry')
                            pe.insert()
                            logger.debug( 'Inserted payment entry ' + pe.name )
                            pe.submit()
                            logger.debug( 'Submitted payment entry ' + pe.name )
                            # uncomment to import only one order per poll
#                            break

                    break

        # Create draft delivery note?
        if store.create_dn:
            dn = make_delivery_note( so.name )
            if store.ship_from_warehouse:
                dn.set_warehouse = store.ship_from_warehouse

            logger.debug( 'Created delivery note')
            dn.insert()
            logger.debug( 'Inserted delivery note ' + dn.name )


        # Update last order number
        store.db_set( 'last_order_number', int(order['orderId']), notify=True)
        store.notify_update
        #DEBUG!!!
        break

# Set sales taxes and charges
#
# When creating a sales order via the UI, the tax table is populated from the tax template automatically
# However, this is not the case here so we need to do it ourselves
#
def _set_sales_taxes_and_charges( sales_order ):
    if not sales_order.taxes_and_charges:
        return

    taxes_and_charges_template = frappe.get_doc('Sales Taxes and Charges Template', sales_order.taxes_and_charges)
    # taxes = []
    tax_fields = [
        "charge_type",
        "account_head",
        "description",
        "cost_center",
        "rate",
        "row_id",
        "idx",
        ]    
    for tax in taxes_and_charges_template.taxes:
        sales_order_tax_dict = sales_order.append('taxes', {})
        for field_name in tax_fields:
            sales_order_tax_dict.set(field_name, tax.get(field_name))


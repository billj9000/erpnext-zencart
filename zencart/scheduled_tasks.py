
from ast import Store
import frappe
from frappe.utils import logger
from frappe.utils.background_jobs import enqueue
from frappe.core.page.background_jobs.background_jobs import get_info
from zencart.api import (
    poll_request,
)
# Scheduler task
# Called every 5 minutes as defined in hooks.py
def schedule_poll():
    # Request a poll of the Zen Cart systems, if enabled in settings for each system
	store_list = frappe.get_all( "Zen Cart Store" )
	for s in store_list:
		store = frappe.get_doc( "Zen Cart Store", s['name'] )
		if store.auto_poll:
			poll_request( store.name )

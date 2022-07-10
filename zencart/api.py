# Copyright (c) 2022, Bill Jones and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import logger
from frappe.utils.background_jobs import enqueue
from frappe.core.page.background_jobs.background_jobs import get_info

# Request a poll
# Called by
#   https:/servername/api/method/zencart.api.poll_request
@frappe.whitelist()
def poll_request( zencart_id ):
    # logger = frappe.logger("zencart", allow_site=True, file_count=50)
    # logger.debug( f"Polling Zen Cart ID: '" + zencart_id + "'" )
    if frappe.db.exists( "Zen Cart Store", zencart_id ):
        store = frappe.get_doc( "Zen Cart Store", zencart_id )
    else:
        return 'Poll request failed - ' + zencart_id + ' not recognised'

    if( store.enabled and not is_queue_running("zencart.connect.poll_connection") ):
        enqueue('zencart.connect.poll_connection', timeout=1000, queue="long", store_name=zencart_id)
        return 'Poll request queued'
     

def get_job_queue(job_name):
    queue_info = get_info()
    queue_by_job_name = [queue for queue in queue_info if queue.get("job_name") == job_name]
    return queue_by_job_name


def is_queue_running(job_name):
    queue = get_job_queue(job_name)
    return queue and len(queue) > 0 and queue[0].get("status") in ["started", "queued"]

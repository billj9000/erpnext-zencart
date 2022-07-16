// Copyright (c) 2022, Bill Jones and contributors
// For license information, please see license.txt

// Item actions

function updateItemQuantity()
{
    var items = [cur_frm.doc.item_code];
	frappe.call({
		method: "zencart.items.updateItemQuantity",
        args: {
            // This only works for website item, not item
            // Might need to split .js files for item and website item
            items: items
        },
        freeze: true,
		freeze_message: __("Updating quantities"),

        callback: function(r) {
			if (r.message && r.message.length) {
				frappe.msgprint({message:__("Update returned: ") + r.message, title:__("Update Item Quantity")});
			}
			else {
				frappe.msgprint({message:__("No response"), title:__("Update Item Quantity")});
			}
		}
	});

}


function updateItem()
{
    var items = [cur_frm.doc.item_code];
	frappe.call({
		method: "zencart.items.updateItem",
        args: {
            // This only works for website item, not item
            // Might need to split .js files for item and website item
            items: items
        },
        freeze: true,
		freeze_message: __("Updating item"),

        callback: function(r) {
			if (r.message && r.message.length) {
				frappe.msgprint({message:__("Update returned: ") + r.message, title:__("Update Item")});
			}
			else {
				frappe.msgprint({message:__("No response"), title:__("Update Item")});
			}
		}
	});

}


function item_add_buttons(frm)
{
    // Add the Zen Cart "Upload" buttons
    frm.page.add_action_item(__("Update quantity in Zen Cart"), function() {
        return updateItemQuantity();
    });

    frm.page.add_action_item(__("Upload to Zen Cart"), function() {
        return updateItem();
    });
}

frappe.ui.form.on("Website Item", {
    refresh: function(frm) {
        item_add_buttons(frm);
    },
});

frappe.ui.form.on("Item", {
    refresh: function(frm) {
        // Check whether or not this Item is also a Website Item
        frappe.db.get_list (
            'Website Item', {
            fields: ['web_item_name'],
            filters: { web_item_name: frm.doc.name }
        })    
        .then(records => {
            if( records.length > 0 )
                item_add_buttons(frm);
        })
    },
});
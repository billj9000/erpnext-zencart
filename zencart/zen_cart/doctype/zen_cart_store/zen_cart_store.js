// Copyright (c) 2022, Bill Jones and contributors
// For license information, please see license.txt

frappe.ui.form.on('Zen Cart Store', {
	refresh: function(frm) {
		// Add "Test" button
		frm.add_custom_button(__('Check connection'), function() {
			return test_connection( frm );
		});
	 }
 });

function test_connection( frm )
{
   frappe.call({
	   method: "zencart.connect.test",
	   freeze: true,
	   freeze_message: __("Testing connection"),
	   args: {
		   'store_name': frm.doc.name,
	   },
	   callback: function(r) {
		   if (r.message && r.message.length) {
			   frappe.msgprint({message:__("Test returned: ") + r.message, title:__("Check connection")});
		   }
		   else {
			   frappe.msgprint({message:__("No response"), title:__("Check connection")});
		   }
	   }
   });
}


from syscore.constants import named_object

missing_order = named_object("missing order")
locked_order = named_object("locked order")
duplicate_order = named_object("duplicate order")
zero_order = named_object("zero order")
order_is_in_status_finished = named_object("order status is modification close")
order_is_in_status_modified = named_object("order status is being modified")
order_is_in_status_not_modified = named_object("order status is not currently modified")
order_is_in_status_reject_modification = named_object(
    "order status is modification rejected"
)
no_order_id = named_object("no order ID")
no_children = named_object("no_children")
no_parent = named_object("no parent")

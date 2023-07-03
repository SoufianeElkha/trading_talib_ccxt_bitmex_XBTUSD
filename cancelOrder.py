import varGlobal as glo
from databaseSendMSG import handle_error, save_info_error, save_info_info
from config.configExchange import exchange
from config.configSetup import symbol
from getter import get_stop_loss_ID, get_take_profit_ID


def cancel_order(order_id_getter, order_id_global_name, action_name):
    """
    Cancels an order for the specified trading symbol.

    Args:
        order_id_getter (function): function to get order id.
        order_id_global_name (str): Name of the order id in global vars.
        action_name (str): The name of the action to cancel the order.

    Note:
        This function attempts to cancel the order twice if an error occurs during the first attempt.
    """
    try:
        order_id = getattr(glo, order_id_global_name)
        exchange.cancel_order(order_id, symbol)
        save_info_info(f"{action_name}: Cancelled pending order.")
        setattr(glo, order_id_global_name, None)
    except Exception as e:
        save_info_error(f"{action_name}: Error while cancelling the order (attempt 1): {str(e)}")
        try:
            order_id = order_id_getter()
            exchange.cancel_order(order_id, symbol)
            setattr(glo, order_id_global_name, None)
        except Exception as e:
            handle_error(f"{action_name}: Error while cancelling the order (final attempt): {str(e)}")


def cancel_stop_loss_order():
    cancel_order(get_stop_loss_ID, 'stop_loss_order_id', 'cancel_stop_loss_order')


def cancel_take_profit_order():
    cancel_order(get_take_profit_ID, 'take_profit_order_id', 'cancel_take_profit_order')


def cancel_trailing_stop_order():
    cancel_order(None, 'trailing_stop_order_id', 'cancel_trailing_stop_order')

import time
import varGlobal as glo
from config.configSetup import Active_stop_loss, Active_take_profit, control_sl_tp_tsl, leverage
from databaseSendMSG import save_info_info, save_to_file, handle_error
from getter import *
from cancelOrder import *


def check_and_cancel_pending_orders():
    while True:
        glo.blocco.acquire()
        temp_entry_price = glo.entry_price
        try:

            # Verifico se posso controllare
            if glo.executing_cancel_order_st_tp is True:
                current_position = get_current_position()
                current_position_side = (int(current_position["currentQty"]) > 0
                                         if current_position and int(current_position["currentQty"]) != 0 else None)
# Verifico posizione se attiva
                if current_position_side is None:
                    save_ok = True
                    if Active_stop_loss is True:
                        stop_loss_recuperato_bitmex = get_stop_loss_ID()
                    else:
                        stop_loss_recuperato_bitmex = None
                    if Active_take_profit is True:
                        take_profit_recuperato_bitmex = get_take_profit_ID()
                    else:
                        take_profit_recuperato_bitmex = None

                    if (stop_loss_recuperato_bitmex is not None and take_profit_recuperato_bitmex is not None):
                        save_ok = False

# Verifico Stop Loss
                    if stop_loss_recuperato_bitmex is not None:
                        save_info_info(f"Stop loss recupero = {str(stop_loss_recuperato_bitmex)}")
                        try:
                            glo.stop_loss_order_id = stop_loss_recuperato_bitmex
                            cancel_stop_loss_order()
                            save_info_info(f"Cancellato Stop_loss: ID_recuperato:{stop_loss_recuperato_bitmex}")
                            if save_ok:
                                exit_time = get_entry_time()
                                wallet_balance = get_balance()
                                pnl_percentage = ((wallet_balance - glo.tmp_wallet_balance) / glo.tmp_wallet_balance)*100
                                save_to_file(
                                    exit_time,
                                    "Take Profit",
                                    temp_entry_price,
                                    pnl_percentage,
                                    glo.current_position_size,
                                    leverage,
                                    0,
                                    0,
                                    wallet_balance,
                                    get_last_realised_pnl(retry=True),
                                )
                                glo.entry_price = None
                                temp_entry_price = None
                                pnl_percentage = None
                                wallet_balance = None
                                glo.tmp_wallet_balance = None

                        except Exception as e:
                            handle_error(f"check_and_cancel_pending_orders: Errore durante la cancellazione dell'ordine stop loss: {str(e)}")
                        finally:
                            glo.stop_loss_order_id = None
                            stop_loss_recuperato_bitmex = None
                            glo.position = None
# Verifico Take profit
                    if take_profit_recuperato_bitmex is not None:
                        save_info_info(f"Take Profit recupero = {str(take_profit_recuperato_bitmex)}")

                        try:
                            glo.take_profit_order_id = take_profit_recuperato_bitmex
                            cancel_take_profit_order()
                            save_info_info(f"Cancellato Take_profit: ID_recuperato:{take_profit_recuperato_bitmex}")
                            if save_ok:
                                exit_time = get_entry_time()
                                wallet_balance = get_balance()
                                pnl_percentage = ((wallet_balance - glo.tmp_wallet_balance) / glo.tmp_wallet_balance)*100
                                save_to_file(
                                    exit_time,
                                    "Stop Loss",
                                    temp_entry_price,
                                    pnl_percentage,
                                    glo.current_position_size,
                                    leverage,
                                    0,
                                    0,
                                    wallet_balance,
                                    get_last_realised_pnl(retry=True),
                                )
                                glo.entry_price = None
                                temp_entry_price = None
                                pnl_percentage = None
                                wallet_balance = None
                                glo.tmp_wallet_balance = None

                        except Exception as e:
                            handle_error(f"check_and_cancel_pending_orders: Errore durante la cancellazione dell'ordine di take profit: {str(e)}")
                        finally:
                            glo.take_profit_order_id = None
                            take_profit_recuperato_bitmex = None
                            glo.position = None
                    save_info_info("Fine Controllo, in attesa di una nuova apertura ordine")
                    glo.executing_cancel_order_st_tp = False
        finally:
            glo.blocco.release()
        time.sleep(control_sl_tp_tsl)

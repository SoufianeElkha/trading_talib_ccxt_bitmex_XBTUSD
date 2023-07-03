# Variabili globali
import threading

position = None
entry_price = None
last_trade_time = None
close_size_contracts = None
stop_loss_order_id = None
take_profit_order_id = None
trailing_stop_order_id = None
current_position_size = None
check_btc_thread = None
entry_timestamp = None

# Gestione Thread cancellazione ordine
blocco = threading.Semaphore(1)
executing_cancel_order_st_tp = False
tmp_wallet_balance = None

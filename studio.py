
import sched
import ccxt
import curses
from datetime import datetime, timedelta
import ccxt.base.errors
import time
import threading
import varGlobal as glo
from affichage.display import *
from config.configExchange import exchange
from config.configSetup import *
from databaseSendMSG import *
from idea.strategy import strategy
from cancelPendingOrder import check_and_cancel_pending_orders
from cancelOrder import *
from getter import *
from createOrder import *
import sqlite3

# from priceBTC import run_controllo_btc


def print_price_and_balance(window):
    while True:
        ticker = fetch_data_with_retry(exchange.fetch_ticker, symbol=symbol)

        balance = fetch_data_with_retry(exchange.fetch_balance)

        price = ticker["last"]
        wallet_balance = balance["free"]["BTC"]

        df = get_data()
        df = strategy(df)
        signal = df.iloc[-1]

        current_position = get_current_position()
        current_position_side = (
            int(current_position["currentQty"]) > 0
            if current_position and int(current_position["currentQty"]) != 0
            else None
        )
        glo.current_position_size = (
            abs(int(current_position["currentQty"])) if current_position else None)

        # Calcola la percentuale di guadagno o perdita
        pnl_percentage = get_pnl_percentage() if glo.position and glo.entry_price else None
        if current_position is not None:
            glo.entry_timestamp = get_entry_timestamp()

        try:
            update_display(
                window,
                price,
                wallet_balance,
                current_position_side,
                glo.current_position_size,
                signal,
                pnl_percentage,
                tmp_agg_display,
                glo.entry_price,
                glo.entry_timestamp,
            )

        except Exception as e:
            handle_error(
                f"print_price_and_balance: Errore durante l'aggiornamento del display : {str(e)}")
        except KeyboardInterrupt:
            pass

        time.sleep(tmp_agg_display)


def load_markets(exchange, attempt=1):
    """
    Load market data from the Bitmex exchange, automatically retrying the request in case of errors, using an exponential backoff strategy.

    Args:
        exchange (ccxt.Exchange): The ccxt exchange instance to use for loading market data.
        attempt (int, optional): The current attempt number. Defaults to 1.

    Raises:
        Exception: If the maximum number of attempts is reached.

    Note:
        This function helps prevent request failures due to temporary errors and employs an exponential backoff strategy to increase the delay between retries.
    """
    MAX_ATTEMPTS = 120
    if attempt > MAX_ATTEMPTS:
        raise Exception("load_markets: Maximum number of attempts reached")
    try:
        exchange.load_markets()
        attempt = 1  # Reset the attempt parameter if the execution is successful
    except ccxt.NetworkError as e:
        print(f"load_markets: NetworkError: {str(e)}")
        handle_error(f"NetworkError: {str(e)}")
        time.sleep(2**attempt)  # Use a progressive delay
        load_markets(exchange, attempt + 1)  # Increment the attempt parameter
    except ccxt.ExchangeError as e:
        print(f"load_markets: ExchangeError: {str(e)}")
        # Modify the error message
        handle_error(f"load_markets: ExchangeError: {str(e)}")
        time.sleep(2**attempt)  # Use a progressive delay
        load_markets(exchange, attempt + 1)  # Increment the attempt parameter


"""
def manage_thread_price_BTC(action, alerted_tp_sl=False):

    if action == "open":
        if Active_control_priceBTC:
            if glo.check_btc_thread is None or not glo.check_btc_thread.is_alive():
                try:
                    glo.check_btc_thread = start_controllo_btc_thread(
                        glo.entry_price, glo.position, alerted_tp_sl, glo.check_btc_thread
                    )
                except Exception as e:
                    handle_error(
                        f"manage_thread_price_BTC: Error starting the thread: {str(e)}"
                    )
                    glo.check_btc_thread = None

    elif action == "close":
        if (Active_control_priceBTC and glo.check_btc_thread is not None and glo.check_btc_thread.is_alive()):
            try:
                glo.check_btc_thread.join(timeout=2)
            except Exception as e:
                handle_error(f"manage_thread_price_BTC: Error closing the thread: {str(e)}")
                glo.check_btc_thread.join(timeout=1)
            else:
                if not glo.check_btc_thread.is_alive():
                    glo.check_btc_thread = None

    else:
        handle_error("manage_thread_price_BTC: Invalid action. Use 'open' to enter the market or 'close' to exit the market.")
"""


def process_manual_signal(manual_signal):
    signal_dict = {
        "Apri Long": {
            "long_condition": True,
            "short_condition": False,
            "exit_long": False,
            "exit_short": False,
        },
        "Apri Short": {
            "long_condition": False,
            "short_condition": True,
            "exit_long": False,
            "exit_short": False,
        },
        "Chiudi Long": {
            "long_condition": False,
            "short_condition": False,
            "exit_long": True,
            "exit_short": False,
        },
        "Chiudi Short": {
            "long_condition": False,
            "short_condition": False,
            "exit_long": False,
            "exit_short": True,
        },
    }
    return signal_dict.get(manual_signal, None)


def execute_trade(signal=None, manual_signal=None):

    if manual_signal:
        signal = process_manual_signal(manual_signal)
        if signal is None:
            raise ValueError("Segnale manuale non riconosciuto")
### long_condition
    if glo.position is None:
        if signal["long_condition"] and ActiveLong:
            open_long_position()
            glo.executing_cancel_order_st_tp = True
            print("Open Long")
### short_condition
        elif signal["short_condition"] and ActiveShort:
            open_short_position()
            glo.executing_cancel_order_st_tp = True
            print("Open Short")
### exit_long
    elif glo.position == "long":
        if signal["exit_long"] and ActiveLong:
            close_long_position()
            glo.executing_cancel_order_st_tp = True
            print("Close Long")
### exit_short
    elif glo.position == "short":
        if signal["exit_short"] and ActiveShort:
            close_short_position()
            glo.executing_cancel_order_st_tp = True
            print("Close Short")


def send_start_message():
    """
    Sends a start message with the current configuration to a Telegram account.
    """
    try:
        wallet_balance = get_balance(retry=True)

        print("Starting XBT/USD Strategy")

        # Format the message using an f-string for better readability
        message = f"""Program started with the following configurations:
        Market            : *{symbol}*
        Timeframe     : *{timeframe}*
        Leverage        : *x{leverage}*
        % Wallet         : *{balance_percentual}* %
        BTC Balance  : *{wallet_balance}* BTC
        """

        send_telegram_message(message)

    except ccxt.NetworkError as e:
        handle_error(f"send_start_message: Error fetching ticker: {str(e)}")


def setup_curses():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    return stdscr


def teardown_curses():
    curses.nocbreak()
    curses.echo()
    curses.endwin()


def initialize_position():
    current_position = get_current_position()

    if current_position and int(current_position["currentQty"]) != 0:
        glo.position = "long" if int(
            current_position["currentQty"]) > 0 else "short"
        glo.entry_price = get_open_position_entry_price()
        glo.entry_timestamp = get_entry_timestamp()
    else:
        glo.position = None
        glo.entry_price = None
        glo.entry_timestamp = None
        glo.check_btc_thread = True


def test_manuale_trade():
    tempo_entro_buy_close = 5

    time.sleep(tempo_entro_buy_close)
    manual_signal = "Apri Long"
    print(manual_signal)
    execute_trade(manual_signal=manual_signal)
    send_telegram_message(f"Segnale manuale: {manual_signal}")

    time.sleep(tempo_entro_buy_close)
    manual_signal = "Chiudi Long"
    print(manual_signal)
    execute_trade(manual_signal=manual_signal)
    send_telegram_message(f"Segnale manuale: {manual_signal}")


    time.sleep(tempo_entro_buy_close)
    manual_signal = "Apri Short"
    print(manual_signal)
    execute_trade(manual_signal=manual_signal)
    send_telegram_message(f"Segnale manuale: {manual_signal}")

    time.sleep(tempo_entro_buy_close)
    manual_signal = "Chiudi Short"
    print(manual_signal)
    execute_trade(manual_signal=manual_signal)
    send_telegram_message(f"Segnale manuale: {manual_signal}")


# Simula un'interruzione con un codice di uscita diverso da 0 per controllare se si riavvia
# time.sleep(5)
# sys.exit(1)
###################### ###################### ######################


def time_to_next_hour():
    """
    This function calculates the number of seconds remaining until the next hour.

    Return:
        The number of seconds (float) until the start of the next hour (i.e., when the time is 00:00:00).
    """

    # Get the current date and time
    now = datetime.now()

    # Replace the minute, second, and microsecond values of the current time with zero (making it the start of the current hour)
    # and add one hour to it, which gives the start of the next hour
    next_hour = now.replace(
        minute=0, second=0, microsecond=0) + timedelta(hours=1)

    # Subtract the current time from the next hour's start time and return the difference in seconds
    return (next_hour - now).total_seconds()


def run_periodically(scheduler):

    time_to_wait = time_to_next_hour()

    initialize_position()
    time.sleep(1)
    df = get_data()
    df = strategy(df)

    # Get the last row in the dataframe, which is the latest data point (signal for trade)
    signal = df.iloc[-1]
    glo.blocco.acquire()  # Acquire lock to prevent simultaneous access to shared resource
    try:

        execute_trade(signal)
        #test_manuale_trade()

        print(f"Execute Trade ok: {get_entry_time()}")
        send_telegram_message(f"Execute Trade ok: {get_entry_time()}")

        if Active_Plot:
            conn = sqlite3.connect('bitmex.db')  # puoi cambiare il nome del file del database come preferisci
            df.to_sql('bitmex_table', conn, if_exists='replace', index=False)
            conn.close()

    finally:
        # Release the lock, whether the trade was successful or not
        glo.blocco.release()
    


    # Print a message indicating the program is running and when the next candle (data point) will come
    save_info_info(f"Notice: Program is running. Next candle in {time_to_wait // 60:.0f} min {time_to_wait % 60:.2f} sec")

    # Schedule the next execution of this function at the end of the current hour
    scheduler.enter(time_to_wait, 1, run_periodically, (scheduler,))


# Thread per eseguire il controllo del prezzo BTC
"""
def start_controllo_btc_thread(entry_price, position, alerted_tp_sl, check_btc_thread):
    check_btc_thread = threading.Thread(target=run_controllo_btc, args=(entry_price, position, alerted_tp_sl, check_btc_thread))
    check_btc_thread.daemon = True
    check_btc_thread.start()
    return check_btc_thread
"""


def main():

    load_markets(exchange)
    initialize_position()
    try:
        send_start_message()

        # Thread per stampa display
        if Active_display:
            stdscr = setup_curses()
            price_and_balance_thread = threading.Thread(
                target=print_price_and_balance, args=(stdscr,))
            price_and_balance_thread.daemon = True
            price_and_balance_thread.start()
        # Thread per controllo exit stop loss e take profit
        if Active_stop_loss or Active_take_profit:
            check_and_cancel_pending_orders_thread = threading.Thread(
                target=check_and_cancel_pending_orders)
            check_and_cancel_pending_orders_thread.daemon = True
            check_and_cancel_pending_orders_thread.start()

        # Utilizza il modulo sched per pianificare la funzione run_periodically()
        scheduler = sched.scheduler(time.time, time.sleep)
        scheduler.enter(0, 1, run_periodically, (scheduler,))
        scheduler.run()

    finally:
        if Active_display:
            teardown_curses()


def run_with_retries():
    while True:
        try:
            main()
        except KeyboardInterrupt:
            handle_error(
                "run_with_retries: User interrupted the process. Exiting...")

            break
        except ccxt.NetworkError as e:
            handle_error(
                f"run_with_retries: Pausing for 1 min: Network error during code execution: {str(e)}")
            time.sleep(60)  # wait 1 minute before retrying
        except ccxt.ExchangeError as e:
            handle_error(
                f"run_with_retries: Pausing for 1 min: Exchange error during code execution: {str(e)}")
            time.sleep(60)  # wait 1 minute before retrying
        except Exception as e:
            print(f"run_with_retries: Exception type: {str(e)}")
            handle_error(
                f"run_with_retries: Pausing for 1 min: General error during code execution: {str(e)}")
            time.sleep(60)  # wait 1 minute before retrying


if __name__ == "__main__":
    run_with_retries()

from datetime import datetime, timedelta
import ccxt
import requests
import logging
from config.configSetup import Active_send_file_telegram, Active_stop_loss, Active_take_profit, fee, symbol
from config.configExchange import TELEGRAM_API_TOKEN, TELEGRAM_CHAT_ID, exchange
import os

name_file_cvs = "data/trading_data.csv"
error_file_log = "data/event.log"
path_data_OHLC = "data/data_OHLC.csv"


def ora_meno_una():
    return (datetime.now() - timedelta(hours=1)).strftime("%d-%m-%Y %H:%M")


logging.basicConfig(
    filename=error_file_log,
    level=logging.INFO,
    format="\n%(asctime)s\n %(message)s",
    datefmt="|--------------|  %d-%m-%Y %H:%M  |--------------|"
)


def handle_error(error_message):
    send_telegram_message(error_message)
    logging.error(error_message)
    send_telegram_file(error_file_log)


def handle_info(error_message):
    send_telegram_message(error_message)
    logging.info(error_message)


def save_info_error(error_message):
    logging.error(error_message)


def save_info_info(error_message):
    logging.info(error_message)


def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&parse_mode=Markdown&text={text}"
        response = requests.get(url)
        return response.json()
    except requests.exceptions.RequestException as e:
        save_info_error(f"Errore di rete durante l'invio del messaggio Telegram: {str(e)}")
    except Exception as e:
        save_info_error(f"Errore durante l'invio del messaggio Telegram: {str(e)}")
    return None


def send_telegram_file(path_file):
    if Active_send_file_telegram:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendDocument?chat_id={TELEGRAM_CHAT_ID}"
            with open(path_file, "rb") as f:
                response = requests.post(url, files={"document": f})
            return response.json()
        except requests.exceptions.RequestException as e:
            save_info_error(f"Errore di rete durante l'invio del file Telegram: {str(e)}")
        except Exception as e:
            save_info_error(f"Errore durante l'invio del file Telegram: {str(e)}")
        return None


def create_csv_file(name_file_cvs):
    if not os.path.exists(name_file_cvs):
        with open(name_file_cvs, "w") as file:
            file.write("Date,Posizion,Posizion Size,Entry price,Exit Price,Leverage,Stop Loss,Take Profit,Profit,Balance BTC\n")


def write_csv_line(entry_time, position, entry_price, pnl_percentage, current_position_size, leverage, stop_loss_percentage, take_profit_percentage, price, wallet_balance,):
    if pnl_percentage is not None:
        line = f"{entry_time},{position},{current_position_size} USD,{entry_price} USD,{price} USD,x{leverage},                        ,                           ,{float(pnl_percentage):.3f} %,{wallet_balance} BTC\n\n"
    else:
        line = f"{entry_time},{position},{current_position_size} USD,{entry_price} USD,           ,x{leverage},"
        if Active_stop_loss:
            line += f"- {stop_loss_percentage} %,"
        else:
            line += "                        ,"

        if Active_take_profit:
            line += f"{take_profit_percentage} %,"
        else:
            line += "                           ,"

        line += f"                             ,{wallet_balance} BTC\n"

    with open(name_file_cvs, "a") as file:
        file.write(line)


def save_to_file(entry_time, position, entry_price, pnl_percentage, current_position_size, leverage, stop_loss_percentage, take_profit_percentage, wallet_balance, get_last_realised_pnl):

    # Fetch ticker and balance
    try:
        ticker = exchange.fetch_ticker(symbol)
    except ccxt.NetworkError as e:
        handle_error(f"save_to_file: Error fetching ticker: {str(e)}")

    price = ticker["last"]

    # Create CSV file if it does not exist
    create_csv_file(name_file_cvs)

    try:
        # Write CSV line
        write_csv_line(entry_time, position, entry_price, pnl_percentage, current_position_size,
                       leverage, stop_loss_percentage, take_profit_percentage, price, wallet_balance,)
    except Exception as e:
        handle_error(f"Errore durante la scrittura file data_trading: {str(e)}")

    # Invia un messaggio tramite Telegram
    message = f"""*{position}*
    Date                : *{entry_time}*
    Position Size  : {current_position_size} USD
    Entry Price     : *{entry_price}* USD
    Leverage        : x{leverage}
    Stop Loss       : - {stop_loss_percentage} %
    Take Profit      :    {take_profit_percentage} %
    """

    if pnl_percentage is not None:
        message += f"""
    *Exit Price*        : *{price}* USD
    Profit               : *{float(pnl_percentage):.3f}%*
    Approx.           : {get_last_realised_pnl} BTC
    BTC Balance  :  *{wallet_balance:.8f}* BTC"""

    send_telegram_message(message)

import contextlib
from http.client import BAD_REQUEST
import time
from datetime import datetime
import ccxt
import pandas as pd
import pytz
from databaseSendMSG import handle_error
from config.configSetup import symbol, timeframe
from config.configExchange import exchange

local_timezone = pytz.timezone("Europe/Rome")


def get_entry_time():
    """
    Returns the current time and date as a formatted string in the 'HH:MM  dd-mm-YYYY' format.
    If an exception occurs during the process, it calls the 'handle_error' function and returns None.
    """
    try:
        entry_time = datetime.now().strftime("%d-%m-%Y  %H:%M")
        return entry_time
    except Exception as e:
        handle_error(f"get_entry_time: Error calculating entry time: {str(e)}")
        return None


def get_balance(retry=False):
    """
    Fetches the account balance and returns the free BTC amount.
    If `retry` is True, it will attempt to fetch the balance again in case of an error.
    """
    try:
        balance = exchange.fetch_balance()
        return balance["free"]["BTC"]
    except ccxt.NetworkError as e:
        if retry:
            print(f"get_balance: Error fetching balance: {str(e)}. Retrying once...")
            time.sleep(1)
            return get_balance(retry=False)
        else:
            handle_error(f"get_balance: Error fetching balance: {str(e)}")

# Calcolo guadagno per ogni giorno


def get_realised_pnl(retry=False):
    """
    Fetches the account balance and returns the current Realised PNL.
    If `retry` is True, it will attempt to fetch the balance again in case of an error.
    """
    try:
        balance = exchange.fetch_balance()
        realisedPnl_in_satoshi = int(balance["info"][0]["realisedPnl"])  # convert to integer
        # convert from satoshi to BTC
        realisedPnl_in_btc = realisedPnl_in_satoshi / 1e8
        return realisedPnl_in_btc
    except ccxt.NetworkError as e:
        if retry:
            handle_error(f"get_realised_pnl: Error fetching balance: {str(e)}. Retrying once...")
            time.sleep(1)
            return get_realised_pnl(retry=False)
        else:
            handle_error(f"get_realised_pnl: Error fetching balance: {str(e)}")

# Calcolo guadagno per ogni operazione chiusa


def get_last_realised_pnl(retry=False):
    """
    Fetches the account balance and returns the previous Realised PNL.
    If `retry` is True, it will attempt to fetch the balance again in case of an error.
    """
    try:
        balance = exchange.fetch_balance()
        prevRealisedPnl_in_satoshi = int(balance["info"][0]["prevRealisedPnl"])  # convert to integer
        # convert from satoshi to BTC
        prevRealisedPnl_in_btc = prevRealisedPnl_in_satoshi / 1e8
        return prevRealisedPnl_in_btc
    except ccxt.NetworkError as e:
        if retry:
            print(f"get_last_realised_pnl: Error fetching balance: {str(e)}. Retrying once...")
            time.sleep(1)
            return get_last_realised_pnl(retry=False)
        else:
            handle_error(f"get_last_realised_pnl: Error fetching balance: {str(e)}")

# Percentuale di guadagno o perdita duerante una pooizione , in tempo reale


def get_pnl_percentage():
    """
    Calculate and return the profit and loss (PnL) percentage of a position
    in the Symbol trading pair on the exchange.

    Returns:
        float: The PnL percentage of the Symbol position, if it exists.
        None: If there is no position or an error occurs.
    """
    try:
        if position := exchange.private_get_position({"filter": '{"symbol": "XBTUSD"}'}):
            return float(position[0]["unrealisedPnlPcnt"]) * 100
        else:
            return None
    except ccxt.NetworkError as e:
        handle_error(f"get_pnl_percentage: Error calculating the profit/loss percentage: {str(e)}")

    except Exception as e:
        handle_error(f"get_pnl_percentage: Error calculating the profit/loss percentage:{str(e)}")
    return None


def get_data(max_retries=10, retry_delay=1):
    """
    Retrieve OHLCV (Open, High, Low, Close, Volume) data for the given symbol
    and timeframe using the exchange's API, and return it as a DataFrame.

    Args:
        max_retries (int, optional): Maximum number of retries before raising an exception. Defaults to 3.
        retry_delay (int, optional): Time delay in seconds between retries. Defaults to 5.

    Returns:
        pd.DataFrame: A DataFrame containing OHLCV data with columns
            ["timestamp", "open", "high", "low", "close", "volume"].

    Raises:
        Exception: If there is an error retrieving the OHLCV data.
    """
    for _ in range(max_retries):
        try:
            ohlcv = fetch_with_retry(exchange, "fetch_ohlcv", symbol, timeframe, limit=1000)
            df = pd.DataFrame( ohlcv, columns=["timestamp", "open","high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["timestamp"] = df["timestamp"].dt.tz_localize('UTC').dt.tz_convert('Europe/Rome')  # convert to UTC+2
            return df
        except Exception as e:
            handle_error(f"get_data: Error retrieving OHLCV data: {str(e)}")
            time.sleep(retry_delay)
    raise Exception(
        "get_data: Max retries reached (10). Unable to retrieve OHLCV data.")


def get_open_position_entry_price():
    """
    Fetches the entry price of the currently open position for the specified symbol.

    Returns:
        float: The average entry price of the open position, or None if there's no open position or an error occurs.
    """
    try:
        # Fetch all positions from the exchange
        positions = exchange.private_get_position()

        # Iterate through the positions
        for position in positions:
            # Check if the position matches the specified symbol and is open
            if position["symbol"] == symbol and position["isOpen"]:
                # Return the average entry price of the open position
                return float(position["avgEntryPrice"])

    except ccxt.NetworkError as e:
        # Handle network errors
        handle_error(
            f"get_open_position_entry_price: Network error while fetching the entry price of the open position: {str(e)}")

    except Exception as e:
        # Handle any other errors
        handle_error(
            f"get_open_position_entry_price: General error while fetching the entry price of the open position: {str(e)}")

    # Return None if no open position is found or an error occurs
    return None


def get_position_from_exchange():
    """Retrieves position from the exchange and returns it. If no position is found, returns None."""
    try:
        # Get all open positions from the exchange
        positions = exchange.private_get_position()

        # Filter positions to find the one corresponding to the specified symbol
        current_position = next(
            (
                position
                for position in positions
                if position["symbol"] == exchange.market_id(symbol)
            ),
            None,
        )

        # Return the current position or None if not found
        return current_position

    except ccxt.NetworkError as e:
        time.sleep(1)
        try:
            # Get all open positions from the exchange
            positions = exchange.private_get_position()

            # Filter positions to find the one corresponding to the specified symbol
            current_position = next(
                (
                    position
                    for position in positions
                    if position["symbol"] == exchange.market_id(symbol)
                ),
                None,
            )

            # Return the current position or None if not found
            return current_position

        except ccxt.NetworkError as e:
            handle_error(f'get_position_from_exchange: Network error occurred. {str(e)}')
    except ccxt.ExchangeError as e:
        handle_error(f'get_position_from_exchange: Exchange error occurred. {str(e)}')
    except Exception as e:
        handle_error(f'get_position_from_exchange: An error occurred. {str(e)}')


def get_current_position():
    """
    Retrieve the current position for the given symbol using the exchange's API.

    Returns:
        dict: A dictionary containing the current position's data, if it exists.
        None: If there is no position or an error occurs.

    Raises:
        ccxt.NetworkError: If there is a network error while fetching the current position.
        Exception: If there is a general error while fetching the current position.
    """
    try:
        return get_position_from_exchange()
    except ccxt.NetworkError as e:
        try:
            return get_position_from_exchange()
        except ccxt.NetworkError as e:
            handle_error(f"get_current_position: Network error while fetching the current position: {str(e)}")
            raise
    except Exception as e:
        try:
            return get_position_from_exchange()
        except Exception as e:
            try:
                return get_position_from_exchange()
            except Exception as e:
                handle_error(f"get_current_position: General error while fetching the current position: {str(e)}")
                raise


def get_stop_loss_price():
    try:
        stop_loss_order = None
        orders = exchange.fetch_open_orders(symbol=symbol)
        for order in orders:
            if order["type"] == "stop" and (
                order["side"] == "sell" or order["side"] == "buy"
            ):
                stop_loss_order = order
                break
        if stop_loss_order is not None:
            return stop_loss_order.get("stopPrice", None)
        else:
            positions = exchange.fetch_positions()
            for position in positions:
                if position["symbol"] == symbol:
                    if position["currentQty"] > 0:
                        return position.get("buyStopPrice", None)
                    elif position["currentQty"] < 0:
                        return position.get("sellStopPrice", None)
    except ccxt.NetworkError as e:
        handle_error(
            f"get_stop_loss_price: Errore di rete durante il recupero degli stop loss price: {str(e)}")
    except Exception as e:
        handle_error(
            f"get_stop_loss_price: Errore generico durante il recupero degli stop loss price: {str(e)}")
    return None


def get_stop_loss_ID():
    try:
        stop_loss_order_id = None
        orders = exchange.fetch_open_orders(symbol=symbol)
        for order in orders:
            if order["type"] == "stop" and (
                order["side"] == "sell" or order["side"] == "buy"
            ):
                stop_loss_order_id = order["id"]
                break
        if stop_loss_order_id is not None:
            return stop_loss_order_id
        else:
            positions = exchange.fetch_positions()
            for position in positions:
                if position["symbol"] == symbol:
                    if position["currentQty"] > 0:
                        return position.get("buyStopId", None)
                    elif position["currentQty"] < 0:
                        return position.get("sellStopId", None)
    except ccxt.NetworkError as e:
        handle_error(
            f"get_stop_loss_ID: Errore di rete durante il recupero degli stop loss ID: {str(e)}")
    except Exception as e:
        handle_error(
            f"get_stop_loss_ID: Errore generico durante il recupero degli stop loss ID: {str(e)}")
    return None


def get_take_profit_ID():
    try:
        take_profit_order_id = None
        orders = exchange.fetch_open_orders(symbol=symbol)
        for order in orders:
            if order["type"] == "limit" and (
                order["side"] == "sell" or order["side"] == "buy"
            ):
                take_profit_order_id = order["id"]
                break
        if take_profit_order_id is not None:
            return take_profit_order_id
        else:
            positions = exchange.fetch_positions()
            for position in positions:
                if position["symbol"] == symbol:
                    return position.get("takeProfit", {}).get("orderId", None)
    except ccxt.NetworkError as e:
        handle_error(
            f"get_take_profit_ID: Errore di rete durante il recupero dei take profit ID: {str(e)}")
    except Exception as e:
        handle_error(
            f"get_take_profit_ID: Errore generico durante il recupero dei take profit ID: {str(e)}")
    return None


def get_take_profit_price():
    try:
        take_profit_order = None
        orders = exchange.fetch_open_orders(symbol=symbol)
        for order in orders:
            if (
                order["type"] == "limit"
                and order["side"] == "sell"
                or order["side"] == "buy"
            ):
                take_profit_order = order
                break
        if take_profit_order is not None:
            return take_profit_order["price"]
        else:
            positions = exchange.fetch_positions()
            for position in positions:
                if position["symbol"] == symbol:
                    return position.get("takeProfitPrice", None)
    except ccxt.NetworkError as e:
        handle_error(
            f"get_take_profit_price:Errore di rete durante il recupero dei take profit price: {str(e)}")
    except Exception as e:
        handle_error(
            f"get_take_profit_price: Errore generico durante il recupero dei take profit price: {str(e)}")
    return None


def get_open_position_size():
    """
    Retrieve the size (quantity) of the open position for the given symbol using the exchange's API.

    Returns:
        int: The size (quantity) of the open position if it exists, or 0 if there is no open position or an error occurs.
    Note:
        In case of errors, the error messages will be handled by the handle_error function.
    """
    try:
        # Get all open positions from the exchange
        positions = exchange.private_get_position()

        # Iterate through the positions
        for position in positions:
            # Check if the position matches the specified symbol and is open
            if position["symbol"] == symbol and position["isOpen"]:
                # Return the size (quantity) of the open position
                return position["currentQty"]

    except ccxt.NetworkError as e:
        # Handle network errors
        handle_error(
            f"get_open_position_size: Network error while fetching position size: {str(e)}")

    except Exception as e:
        # Handle any other errors
        handle_error(
            f"get_open_position_size: General error while fetching position size: {str(e)}")

    # Return 0 if no open position is found or an error occurs
    handle_error("get_open_position_size: Return posizion size 0")
    return 0


def get_entry_timestamp():
    """
    Retrieve the entry timestamp of the open position for the given symbol using the exchange's API,
    and convert it to a localized, formatted string.

    Returns:
        str: The formatted timestamp of the open position if it exists, or None if there is no open position or an error occurs.

    Note:
        In case of errors, the error messages will be handled by the handle_error function.
    """
    try:
        positions = exchange.private_get_position()
        for position in positions:
            if position["symbol"] == symbol and position["isOpen"]:
                # Esempio di stringa

                timestamp_string = position["timestamp"]

                # Converto la stringa in un oggetto datetime
                timestamp_datetime = datetime.fromisoformat(
                    timestamp_string.replace("Z", "+00:00")
                ).replace(tzinfo=pytz.utc)

                # Converto il timestamp in un oggetto timezone-aware nel fuso orario locale
                local_timestamp = timestamp_datetime.astimezone(local_timezone)

                # Applico la formattazione richiesta
                formatted_timestamp = local_timestamp.strftime(
                    "%H:%M h %d-%m-%Y")
                return formatted_timestamp
    except ccxt.NetworkError as e:
        handle_error(
            f"get_entry_timestamp:Errore di rete durante il recupero position['timestamp']: {str(e)}")
    except Exception as e:
        handle_error(
            f"get_entry_timestamp: Errore generico durante il recupero position['timestamp']: {str(e)}")
    return None


# Retrieve the entry timestamp (in milliseconds) of the current open position
def get_current_position_entry_time():
    try:
        # Get all open positions from the exchange
        positions = exchange.private_get_position()

        # Iterate through the positions
        for position in positions:
            # Check if the position matches the specified symbol and is open
            if position["symbol"] == symbol and position["isOpen"]:
                # Return the opening timestamp of the current open position
                return position["openingTimestamp"]

    except ccxt.NetworkError as e:
        # Handle network errors
        handle_error(
            f"get_current_position_entry_time: Network error while fetching current position entry time: {str(e)}")

    except Exception as e:
        # Handle any other errors
        handle_error(
            f"get_current_position_entry_time: General error while fetching current position entry time: {str(e)}")

    # Return None if no open position is found or an error occurs
    return None


def get_tick_size():
    """
    Retrieve the tick size for the given symbol using the exchange's API.

    Returns:
        float: The tick size as a float if it can be retrieved, or None if there is an error.

    Note:
        In case of errors, the error messages will be handled by the handle_error function.
    """
    try:
        # Get market information for the specified symbol
        market = exchange.market(symbol)

        # Retrieve and return the tick size as a float
        return float(market["info"]["tickSize"])

    except ccxt.BaseError as e:
        # Handle ccxt-specific errors
        handle_error(
            f"get_tick_size: Error while fetching tick size from ccxt: {str(e)}")
        return None

    except KeyError as e:
        # Handle missing keys in the market information
        handle_error(
            f"get_tick_size: Key error while fetching tick size: {str(e)}")
        return None

    except Exception as e:
        # Handle any other errors
        handle_error(
            f"get_tick_size: General error while fetching tick size: {str(e)}")
        return None


@contextlib.contextmanager
def rate_limit_sleep(rate_limit):
    """
    A context manager for rate-limiting API requests. It enforces a specified rate limit by sleeping for a calculated duration after the execution of the block of code inside the context.
    Args:
        rate_limit (int): The maximum number of requests allowed per minute.
    Usage:
        with rate_limit_sleep(rate_limit):
        120 requests per minute on all routes (reduced to 30 when unauthenticated)
        10 requests per second on certain routes (see below)
    Note:
        This context manager helps prevent exceeding API rate limits, which could lead to temporary or permanent bans.
    """

    sleep_time = 60 / rate_limit
    yield
    time.sleep(sleep_time)


def fetch_with_retry(exchange, method, *args, **kwargs):
    """
    Perform an API request using the given method, automatically retrying the request in case of temporary errors.

    Args:
        exchange (ccxt.Exchange): The ccxt exchange instance to use for the API request.
        method (str): The name of the method to call on the exchange instance.
        *args: Positional arguments to pass to the method.
        **kwargs: Keyword arguments to pass to the method.

    Returns:
        Any: The result of the API request.

    Raises:
        Exception: If the maximum number of retries is reached.

    Note:
        This function helps prevent request failures due to temporary errors or expired requests.
    """
    retry_delay = 1
    retry_count = 0
    max_retries = 10
    while True:
        try:
            if method == "request":
                return exchange.request(*args, **kwargs)
            else:
                return getattr(exchange, method)(*args, **kwargs)
        except BAD_REQUEST as e:
            if "This request has expired" not in str(e):
                raise e
            # Add a time margin to avoid discrepancies
            time.sleep(retry_delay)
            retry_delay += 1
            retry_count += 1
            if retry_count >= max_retries:
                raise Exception(
                    "fetch_with_retry: Retrieval attempts exhausted")
        except (ConnectionError, TimeoutError) as e:
            handle_error(
                f"fetch_with_retry: Retrieval attempts exhausted: {str(e)}")
            retry_delay += 10
            time.sleep(retry_delay)
            retry_count += 1
            if retry_count >= max_retries:
                raise Exception(
                    "fetch_with_retry: Retrieval attempts exhausted")


def fetch_data_with_retry(fetch_function, *args, retry_delay=1, rate_limit=120, **kwargs):
    """
    Perform an API request using the given fetch_function, automatically retrying the request in case of errors while also rate-limiting the requests.

    Args:
        fetch_function (callable): The function to use for fetching the data.
        *args: Positional arguments to pass to the fetch_function.
        retry_delay (int, optional): The time to wait between retries in case of errors. Defaults to 1.
        rate_limit (int, optional): The maximum number of requests allowed per minute. Defaults to 120.
        **kwargs: Keyword arguments to pass to the fetch_function.

    Returns:
        Any: The result of the API request.

    Note:
        This function helps prevent request failures due to temporary errors and enforces the specified rate limit.
    """

    while True:
        try:
            with rate_limit_sleep(rate_limit):
                result = fetch_function(*args, **kwargs)
            return result
        except ccxt.NetworkError as e:
            error_message = f"fetch_data_with_retry: NetworkError: {str(e)}"
            handle_error(error_message)
            time.sleep(retry_delay)
        except ccxt.ExchangeError as e:
            error_message = f"fetch_data_with_retry: ExchangeError: {str(e)}"
            handle_error(error_message)
            time.sleep(retry_delay)
        except Exception as e:
            error_message = f"fetch_data_with_retry: GeneralError: {str(e)}"
            handle_error(error_message)
            time.sleep(retry_delay)

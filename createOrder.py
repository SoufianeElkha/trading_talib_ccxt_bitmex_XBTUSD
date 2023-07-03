import ccxt
from cancelOrder import cancel_stop_loss_order, cancel_take_profit_order, cancel_trailing_stop_order
from config.configSetup import *
from config.configExchange import exchange
from databaseSendMSG import handle_error, handle_info, save_info_info, save_to_file
from getter import *
import varGlobal as glo


def set_leverage():
    """
    Set the leverage for the specified trading symbol.

    Note:
        This function sets the leverage for the symbol specified in the global variable 'symbol'. In case of errors, it calls the 'handle_error' function to handle them.
    """

    global symbol
    try:
        exchange.private_post_position_leverage(
            {"symbol": exchange.market_id(symbol), "leverage": leverage})
    except ccxt.NetworkError as e:
        handle_error(
            f"set_leverage: Network error while setting leverage: {str(e)}")
    except Exception as e:
        handle_error(
            f"set_leverage: General error while setting leverage: {str(e)}")


def set_margin_type():
    """
    Set the margin type for the specified trading symbol.

    Note:
        This function sets the margin type for the symbol specified in the global variable 'symbol'. In case of errors, it calls the 'handle_error' function to handle them.
    """

    global symbol
    try:
        exchange.private_post_position_isolate(
            {
                "symbol": exchange.market_id(symbol),
                "enabled": marginType.lower() == "isolated",
            }
        )
    except ccxt.NetworkError as e:
        handle_error(
            f"set_margin_type: Network error while setting margin type: {str(e)}")
    except Exception as e:
        handle_error(
            f"set_margin_type: General error while setting margin type: {str(e)}")


def create_trailing_stop_loss(side, entry_price, amount, percentage):
    stop_price = None
    tick_size = get_tick_size()
    if side not in ["buy", "sell"]:
        raise ValueError(
            "create_trailing_stop_loss: Invalid side. It must be 'buy' or 'sell'.")

    if side == "sell":  # LONG POSITION
        stop_price = entry_price * (1 - (percentage / 100))
        peg_offset_value = entry_price * (percentage / tick_size / 100)
        offset = -(round(peg_offset_value * tick_size))
        handle_error(f"create_trailing_stop_loss: Offset price long: {offset}")

    else:  # SHORT POSITION
        stop_price = entry_price * (1 + (percentage / 100))
        peg_offset_value = entry_price * (percentage / tick_size / 100)
        offset = round(peg_offset_value * tick_size)
        handle_error(
            f"create_trailing_stop_loss: Offset price short: {offset}")

    params = {
        "execInst": "LastPrice",
        "pegOffsetValue": offset,
        "pegPriceType": "TrailingStopPeg",
        "stopPx": stop_price,
    }

    handle_error(
        f"\ntick = {tick_size}\npercentage : {percentage}\n peg_offset_value: {offset}\n entry_price: {entry_price}\n stop_price {stop_price}")
    return exchange.create_order(symbol, "stop", side, amount, None, params)


def create_stop_loss_order(side, amount, entry_price, stop_loss_percentage):
    """
    Create a stop-loss order for the specified trading symbol.

    Args:
        symbol (str): The trading symbol to create the stop-loss order for.
        side (str): The side of the trade, either "long" or "short".
        amount (float): The amount of the order in the base currency.
        entry_price (float): The entry price of the trade.
        stop_loss_percentage (float): The stop-loss percentage to apply, as a decimal (e.g., 0.03 for a 3% stop-loss).

    Returns:
        dict: The stop-loss order object returned by the exchange.

    Note:
        This function creates a stop-loss order at a price calculated based on the entry price and the specified stop-loss percentage.
    """
    if side == "long":
        stop_loss_price = entry_price * (1 - stop_loss_percentage)
        stop_side = "sell"
    else:
        stop_loss_price = entry_price * (1 + stop_loss_percentage)
        stop_side = "buy"

    stop_loss_order = exchange.create_order(
        symbol,
        "stop",
        stop_side,
        amount,
        price=stop_loss_price,
        params={"stopPx": stop_loss_price},
    )

    return stop_loss_order


def create_take_profit_order(position, contracts, entry_price, take_profit_percentage):
    """
    Create a take-profit order for the specified trading symbol.

    Args:
        symbol (str): The trading symbol to create the take-profit order for.
        position (str): The position of the trade, either "long" or "short".
        contracts (float): The number of contracts to take profit on.
        entry_price (float): The entry price of the trade.
        take_profit_percentage (float): The take-profit percentage to apply, as a decimal (e.g., 0.03 for a 3% take-profit).

    Returns:
        dict: The take-profit order object returned by the exchange.
    """

    price = (
        entry_price * (1 + take_profit_percentage)
        if position == "long"
        else entry_price * (1 - take_profit_percentage)
    )
    side = "sell" if position == "long" else "buy"
    take_profit_order = exchange.create_order(
        symbol, "limit", side, contracts, price)
    return take_profit_order


def open_long_position():
    set_leverage()
    set_margin_type()

    available_contracts_no_leverage = None
    wallet_balance = get_balance(retry=True)
    glo.tmp_wallet_balance = wallet_balance
    available_balance_btc = wallet_balance * (balance_percentual/100)
    symbol_usd_price = exchange.fetch_ticker(symbol)["last"]
    available_contracts_no_leverage = int(available_balance_btc * symbol_usd_price // 100) * 100
    available_contracts = available_contracts_no_leverage * leverage
    save_info_info(
        f"open_long_position: Contratti calcolati: {available_contracts}")

    if available_contracts is not None:
        order_buy = execute_order("buy", available_contracts)

    if order_buy:
        glo.position = "long"
        glo.entry_price = get_open_position_entry_price()
        entry_time = get_entry_time()

        # manage_thread_price_BTC("open", glo.entry_price, glo.position, alerted_tp_sl=False, glo.check_btc_thread)

        if Active_stop_loss:
            try:
                stop_loss_order = create_stop_loss_order(
                    glo.position,
                    available_contracts,
                    glo.entry_price,
                    (stop_loss_LONG_percentage / 100),
                )
                glo.stop_loss_order_id = stop_loss_order["id"]
            except Exception as e:
                handle_error(
                    f"open_long_position: Errore durante la creazione dell'ordine stop loss Long: {str(e)}")

        if Active_take_profit:
            try:
                take_profit_order = create_take_profit_order(
                    glo.position,
                    available_contracts,
                    glo.entry_price,
                    (take_profit_LONG_percentage / 100),
                )
                glo.take_profit_order_id = take_profit_order["id"]
            except Exception as e:
                handle_error(
                    f"open_long_position: Errore durante la creazione dell'ordine di take profit Long: {str(e)}")

        if Active_traling_stop_loss:
            try:
                trailing_stop_order_LONG = create_trailing_stop_loss(
                    "sell",
                    glo.entry_price,
                    available_contracts,
                    trailing_stop_loss_percentage_Long,
                )
                glo.trailing_stop_order_id = trailing_stop_order_LONG["id"]
            except Exception as e:
                handle_error(
                    f"open_long_position: Errore durante la creazione del traling stop loss LONG: {str(e)}")

        # Ottieni la posizione e la dimensione correnti
        current_position = get_current_position()
        glo.current_position_size = (
            abs(int(current_position["currentQty"])) if current_position else None)

        save_to_file(
            entry_time,
            "Open Long  ",
            glo.entry_price,
            None,
            glo.current_position_size,
            leverage,
            stop_loss_LONG_percentage,
            take_profit_LONG_percentage,
            wallet_balance,
            None,
        )


def close_long_position():
    glo.close_size_contracts = None
    glo.close_size_contracts = get_open_position_size()
    temp_entry_price = glo.entry_price

    #order_exit_buy = execute_order("sell", glo.close_size_contracts)
    order_exit_buy = close_position()
    if order_exit_buy:
        # manage_thread_price_BTC("close")
        try:
            if (Active_stop_loss and glo.stop_loss_order_id is not None):
                cancel_stop_loss_order()
                glo.stop_loss_order_id = None

            if (Active_take_profit and glo.take_profit_order_id is not None):
                cancel_take_profit_order()
                glo.take_profit_order_id = None

            if (Active_traling_stop_loss and glo.trailing_stop_order_id is not None):
                cancel_trailing_stop_order()
                glo.trailing_stop_order_id = None
        except Exception as e:
            handle_error(
                f"close_long_position: Errore creazione ST or TP or TRLS: {str(e)}")

        glo.position = None
        glo.entry_price = None
        exit_time = get_entry_time()
        wallet_balance = get_balance(retry=True)
        pnl_percentage = ((wallet_balance - glo.tmp_wallet_balance) / glo.tmp_wallet_balance)*100
        save_to_file(
            exit_time,
            "Close Long",
            temp_entry_price,
            pnl_percentage,
            glo.current_position_size,
            leverage,
            stop_loss_LONG_percentage,
            take_profit_LONG_percentage,
            wallet_balance,
            get_last_realised_pnl(retry=True),
        )
        temp_entry_price = None
        pnl_percentage = None
        wallet_balance = None
        glo.tmp_wallet_balance = None
        handle_info(
            f"close_long_position: Number of closed Long contracts: {str(glo.close_size_contracts)} USD")


def open_short_position():
    set_leverage()
    set_margin_type()

    available_contracts_no_leverage = None
    wallet_balance = get_balance(retry=True)
    glo.tmp_wallet_balance = wallet_balance
    available_balance_btc = wallet_balance * (balance_percentual/100)
    symbol_usd_price = exchange.fetch_ticker(symbol)["last"]
    available_contracts_no_leverage = int(available_balance_btc * symbol_usd_price // 100) * 100
    available_contracts = available_contracts_no_leverage * leverage
    save_info_info(
        f"open_short_position: Contratti calcolati: {available_contracts}")

    if available_contracts is not None:
        order_sell = execute_order("sell", available_contracts)

    if order_sell:
        glo.position = "short"
        glo.entry_price = get_open_position_entry_price()
        entry_time = get_entry_time()

        # manage_thread_price_BTC("open", glo.entry_price,  glo.position, alerted_tp_sl=False, glo.check_btc_thread)

        if Active_stop_loss:
            try:
                stop_loss_order = create_stop_loss_order(
                    glo.position,
                    available_contracts,
                    glo.entry_price,
                    (stop_loss_SHORT_percentage / 100),
                )
                glo.stop_loss_order_id = stop_loss_order["id"]
            except Exception as e:
                handle_error(
                    f"open_short_position: Errore durante la creazione dell'ordine stop loss Short: {str(e)}")

        if Active_take_profit:
            try:
                take_profit_order = create_take_profit_order(
                    glo.position,
                    available_contracts,
                    glo.entry_price,
                    (take_profit_SHORT_percentage / 100),
                )
                glo.take_profit_order_id = take_profit_order["id"]
            except Exception as e:
                handle_error(
                    f"open_short_position: Errore durante la creazione dell'ordine di take profit Short: {str(e)}")

        if Active_traling_stop_loss:
            try:
                trailing_stop_order_SHORT = create_trailing_stop_loss(
                    "buy",
                    glo.entry_price,
                    available_contracts,
                    trailing_stop_loss_percentage_Short,
                )
                # Ottieni l'ID dell'ordine
                glo.trailing_stop_order_id = trailing_stop_order_SHORT["id"]
            except Exception as e:
                handle_error(
                    f"open_short_position: Errore durante la creazione del traling stop loss SHORT: {str(e)}")

        # Ottieni la posizione e la dimensione correnti
        current_position = get_current_position()
        glo.current_position_size = (
            abs(int(current_position["currentQty"])) if current_position else None)

        save_to_file(
            entry_time,
            "Open Short",
            glo.entry_price,
            None,
            glo.current_position_size,
            leverage,
            stop_loss_SHORT_percentage,
            take_profit_SHORT_percentage,
            wallet_balance,
            None,
        )


def close_short_position():
    glo.close_size_contracts = None
    glo.close_size_contracts = get_open_position_size()
    temp_entry_price = glo.entry_price

    #order_exit_sell = execute_order("buy", abs(int(glo.close_size_contracts)))
    order_exit_sell = close_position()
    if order_exit_sell:
        # manage_thread_price_BTC("close")
        try:
            if (Active_stop_loss and glo.stop_loss_order_id is not None):
                cancel_stop_loss_order()
                glo.stop_loss_order_id = None

            if (Active_take_profit and glo.take_profit_order_id is not None):
                cancel_take_profit_order()
                glo.take_profit_order_id = None

            if (Active_traling_stop_loss and glo.trailing_stop_order_id is not None):
                cancel_trailing_stop_order()
                glo.trailing_stop_order_id = None
        except Exception as e:
            handle_error(
                f"close_short_position: Errore creazione ST or TP or TRLS: {str(e)}")

        glo.position = None
        glo.entry_price = None
        exit_time = get_entry_time()
        wallet_balance = get_balance(retry=True)
        pnl_percentage = ((wallet_balance - glo.tmp_wallet_balance) / glo.tmp_wallet_balance)*100
        save_to_file(
            exit_time,
            "Close Short",
            temp_entry_price,
            pnl_percentage,
            glo.current_position_size,
            leverage,
            stop_loss_SHORT_percentage,
            take_profit_SHORT_percentage,
            wallet_balance,
            get_last_realised_pnl(retry=True),
        )
        temp_entry_price = None
        pnl_percentage = None
        wallet_balance = None
        glo.tmp_wallet_balance = None
        handle_info(
            f"close_short_position: Number of closed Short contracts: {str(glo.close_size_contracts)} USD")


def execute_order(order_type, contracts):
    """
    Execute a market order (buy or sell) for the specified trading symbol and contracts.

    Args:
        order_type (str): The type of order to execute, either "buy" or "sell".
        symbol (str): The trading symbol to create the order for.
        contracts (float): The number of contracts to execute the order for.

    Returns:
        dict: The executed order object returned by the exchange, or None if an error occurs.
    """

    try:
        if order_type == "buy":
            order = exchange.create_market_buy_order(symbol, contracts)
        elif order_type == "sell":
            order = exchange.create_market_sell_order(symbol, contracts)
        return order
    except ccxt.NetworkError as e:
        handle_error(
            f"execute_order: Network error while creating {order_type} order: {str(e)}")
    except ccxt.InvalidOrder as e:
        handle_error(
            f"execute_order: Invalid order while creating {order_type} order: {str(e)}")
    except ccxt.ExchangeError as e:
        handle_error(
            f"execute_order: Exchange error while creating {order_type} order: {str(e)}")
    except Exception as e:
        handle_error(
            f"execute_order: General error while creating {order_type} order: {str(e)}")
        return None

def close_position():
    try:
        order = exchange.privatePostOrderClosePosition({
            'symbol': symbol
        })
        return order
    except ccxt.NetworkError as e:
        handle_error(
            f"close_position: Network error while closing position: {str(e)}")
    except ccxt.InvalidOrder as e:
        handle_error(
            f"close_position: Invalid order while closing position: {str(e)}")
    except ccxt.ExchangeError as e:
        handle_error(
            f"close_position: Exchange error while closing position: {str(e)}")
    except Exception as e:
        handle_error(
            f"close_position: General error while closing position: {str(e)}")
        return None

import asyncio
import aiohttp
from config.configSetup import symbol, stop_loss_LONG_percentage, stop_loss_SHORT_percentage, take_profit_LONG_percentage, take_profit_SHORT_percentage
from aiohttp.client_exceptions import ClientConnectorError
from databaseSendMSG import handle_error, handle_info


async def get_btc_price(url, key=None, sub_key=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    if key:
                        if sub_key:
                            return float(data[key][sub_key]['c'][0])
                        else:
                            return float(data[key])
                    else:
                        return data
                else:
                    return None

    except ClientConnectorError:
        print("get_btc_price: Errore di connessione")
        return None
    except KeyError:
        print("get_btc_price: Chiave non trovata")
        return None
    except ValueError:
        print("get_btc_price: Errore nella conversione del valore")
        return None
    except Exception as e:
        print(f"get_btc_price: Errore sconosciuto: {str(e)}")
        return None


async def get_btc_price_bybit():
    url = "https://api.bybit.com/v2/public/tickers?symbol=BTCUSD"
    data = await get_btc_price(url)
    return float(data["result"][0]["last_price"]) if data else None


async def get_btc_price_bitmex():
    url = "https://www.bitmex.com/api/v1/instrument?symbol={symbol}"
    data = await get_btc_price(url)
    return data[0]["lastPrice"] if data else None


async def get_btc_price_binance():
    url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT"
    return await get_btc_price(url, key='price')


async def main(entry_price, position, alerted_tp_sl, check_btc_thread):
    print("Controllo percentuale BTC avviato")
    while position == 'long' or position == 'short':
        try:
            price_bitmex = await get_btc_price_bitmex()
            price_binance = await get_btc_price_binance()
            price_bybit = await get_btc_price_bybit()

            prices = [price for price in [price_bitmex,
                                          price_binance, price_bybit] if price is not None]

            if len(prices) > 0:
                medium_price = sum(prices) / len(prices)
                price_change_percentage = (
                    medium_price - entry_price) / entry_price * 100

                if not alerted_tp_sl:
                    print(f"Price entry: {entry_price}")
                    print(
                        f"Price BTC: {medium_price:.2f} --> {price_change_percentage:.2f}")
                    # Gestione alert stop loss e take profit
                    if position == 'long':
                        if price_change_percentage >= take_profit_LONG_percentage:
                            handle_info(
                                f"Take Profit LONG raggiunto: {price_change_percentage:.2f}%")
                            alerted_tp_sl = True

                        if price_change_percentage <= -stop_loss_LONG_percentage:
                            handle_info(
                                f"Stop Loss LONG raggiunto: -{price_change_percentage:.2f}%")
                            alerted_tp_sl = True

                    elif position == 'short':
                        if price_change_percentage <= -take_profit_SHORT_percentage:
                            handle_info(
                                f"Take Profit SHORT raggiunto: {price_change_percentage:.2f}%")
                            alerted_tp_sl = True

                        if price_change_percentage >= stop_loss_SHORT_percentage:
                            handle_info(
                                f"Stop Loss SHORT raggiunto: -{price_change_percentage:.2f}%")
                            alerted_tp_sl = True

            else:
                handle_info("priceBTC: Errore nel recupero del prezzo")

        except Exception as e:
            handle_error(f"Errore durante il controllo del prezzo: {str(e)}")
            await asyncio.sleep(30)

        await asyncio.sleep(1)


def run_controllo_btc(entry_price, position, alerted_tp_sl, check_btc_thread):
    asyncio.run(main(entry_price, position, alerted_tp_sl, check_btc_thread))

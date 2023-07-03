from datetime import datetime
import time
import os
import time
import psutil
import subprocess
from config.configSetup import *
from databaseSendMSG import handle_error, handle_info


def is_vcgencmd_available():
    try:
        subprocess.check_output(['vcgencmd'], stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

# Leggi la temperatura della CPU -> String


def get_cpu_temperature():
    try:
        if is_vcgencmd_available():
            temp = os.popen('vcgencmd measure_temp').readline()
            return (temp.replace("temp=", "").replace("'C\n", ""))
        return None
    except Exception as e:
        handle_error(
            f"Display.py : Errore durante la lettura della temperatura della CPU: {str(e)}")
        return None

# Leggi utilizzo RAM -> Float


def get_ram_usage():
    try:
        memory_info = psutil.virtual_memory()
        return memory_info.percent
    except Exception as e:
        handle_error(
            f"Display.py : Errore durante la lettura dell'utilizzo della RAM: {str(e)}")
        return None


def update_display(window, price, wallet_balance, current_position_side, current_position_size, signal, pnl_percentage, tmp_agg_display, entry_price, entry_timestamp):

    # Cancella la finestra
    window.clear()

    # Stampa la temperatura della CPU
    cpu_temp = get_cpu_temperature()

    # Stampa le informazioni sulla CPU
    cpu_percent = psutil.cpu_percent()

    # Utilizzo della funzione per ottenere l'utilizzo della RAM
    ram_usage_percent = get_ram_usage()

    # Get the window size
    max_y, max_x = window.getmaxyx()

    # Check if the window is large enough to display all the text
    if max_y < 10 or max_x < 10:
        window.addstr(20, 20, "Please resize the window to at least 10x10.")
        window.refresh()
        time.sleep(tmp_agg_display)
        return

    now = datetime.now()
    current_time = now.strftime("[ %H:%M ] [ %d-%m-%Y ]")

    # Aggiungi questa riga per mostrare la data e l'ora
    window.addstr(0, 0, f"Ora attuale e Data   : {current_time}")

    # Aggiorna le stringhe con le informazioni sulla posizione in tempo reale
    window.addstr(
        2, 0, f"Posizione corrente   : {'Long' if current_position_side else 'Short' if current_position_side is not None else 'N/D'}")

    try:
        window.addstr(4, 0, f"Mark Price           : {price:.2f} USD")
    except Exception as e:
        handle_error(f"Display.py : Errore Mark Price : {str(e)}")

    try:
        window.addstr(
            3, 0, f"Execution time       : {entry_timestamp}"if entry_timestamp is not None and current_position_side is not None else "Execution time       : N/D")
    except Exception as e:
        handle_error(
            f"Display.py : Errore nel recupero del timestamp: {str(e)}")

    try:
        window.addstr(
            5, 0, f"Entry Price          : {entry_price} USD" if entry_price is not None and current_position_side is not None else "Entry Price          : N/D")
    except Exception as e:
        handle_error(f"Display.py : Errore Enty Price : {str(e)}")

    if pnl_percentage is not None:
        window.addstr(
            6, 0, f"Guadagno/Perdita     : {float(pnl_percentage)* float(leverage):.2f}%")
    else:
        window.addstr(6, 0, "Guadagno/Perdita     : N/D")

    window.addstr(
        7, 0, f"Dimensione Posizione : {current_position_size if current_position_size is not None else 0} USD")
    window.addstr(
        8, 0, f"Patrimonio attuale   : {wallet_balance * price:.2f} USD")

    window.addstr(9, 0, f"Bilancio BTC         : {wallet_balance:.8f} BTC")
    window.addstr(10, 0, f"Long Condition       : {signal['long_condition']}")
    window.addstr(11, 0, f"Short Condition      : {signal['short_condition']}")
    window.addstr(12, 0, f"Exit Long            : {signal['exit_long']}")
    window.addstr(13, 0, f"Exit Short           : {signal['exit_short']}")
    window.addstr(14, 0, f"Leva set             : {leverage}")
    if current_position_side is not None:
        window.addstr(
            15, 0, f"Stop Loss            : {(stop_loss_LONG_percentage*100) if current_position_side else (stop_loss_SHORT_percentage*100) if current_position_side is not None else 'N/D'}%")
        window.addstr(
            16, 0, f"Take Profit          : {(take_profit_LONG_percentage*100) if current_position_side else (take_profit_LONG_percentage*100) if current_position_side is not None else 'N/D'}%")

    # Uso CPU e funziona solo su Raspberry pi
    if is_vcgencmd_available():
        window.addstr(17, 0, f"Temperatura CPU      : {str(cpu_temp)} °C")
    window.addstr(18, 0, f"Utilizzo della CPU:  : {str(cpu_percent)} %")
    window.addstr(19, 0, f"Utilizzo della RAM:  : {str(ram_usage_percent)} %")

    if is_vcgencmd_available():
        if len(cpu_temp) > 0 and float(cpu_temp) > 65:
            handle_info("Display.py: Temperatura CPU alta, sopra i 65°C")

    if float(ram_usage_percent) > 85:
        handle_info("Display.py: Utilizzo della RAM elevato, superiore al 85%")

    try:
        window.refresh()
    except Exception as e:
        handle_error(f"Display.py: Errore aggiornamento display")

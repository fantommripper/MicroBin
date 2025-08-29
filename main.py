import os
import json
import winshell
import pystray
import threading
import time
from PIL import Image

# путь к папке с конфигом
APPDATA = os.getenv("APPDATA")
CONFIG_DIR = os.path.join(APPDATA, "MicroBin")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# иконки для тем
ICONS = {
    "light": {
        "empty": "bin_empty_light.ico",
        "full": "bin_full_light.ico"
    },
    "dark": {
        "empty": "bin_empty_dark.ico",
        "full": "bin_full_dark.ico"
    }
}

# загружаем настройки
def load_config():
    default_config = {
        "theme": "light",
        "check_interval": 1  # интервал проверки в секундах по умолчанию
    }
    
    if not os.path.exists(CONFIG_FILE):
        return default_config
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Убедимся, что все необходимые поля есть в конфиге
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
    except Exception:
        return default_config

# сохраняем настройки
def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

# глобальные настройки
config = load_config()
theme = config.get("theme", "light")
check_interval = config.get("check_interval", 1)

def get_icon_path():
    """Выбираем иконку по теме и состоянию корзины"""
    try:
        rb = winshell.recycle_bin()
        items = list(rb.items())
        has_items = len(items) > 0
        return ICONS[theme]["full"] if has_items else ICONS[theme]["empty"]
    except Exception:
        return ICONS[theme]["empty"]

def update_icon(icon):
    """Обновляем иконку"""
    path = get_icon_path()
    if os.path.exists(path):
        icon.icon = Image.open(path)

def monitor_recycle_bin(icon):
    """Мониторинг состояния корзины в отдельном потоке"""
    prev_state = None
    while getattr(icon, 'monitor_running', True):
        try:
            rb = winshell.recycle_bin()
            current_state = len(list(rb.items())) > 0
            
            if current_state != prev_state:
                update_icon(icon)
                prev_state = current_state
        except Exception as e:
            print(f"Ошибка при проверке корзины: {e}")
        
        # Используем текущий интервал из конфига
        current_interval = getattr(icon, 'check_interval', check_interval)
        time.sleep(current_interval)

def open_recyclebin(icon, item):
    os.startfile("shell:RecycleBinFolder")
    update_icon(icon)

def empty_recyclebin(icon, item):
    rb = winshell.recycle_bin()
    if any(True for _ in rb.items()):
        rb.empty(confirm=False, show_progress=False, sound=True)
    update_icon(icon)

def set_theme(icon, item, value):
    global theme, config
    theme = value
    config["theme"] = value
    save_config(config)
    update_icon(icon)

def set_check_interval(icon, item, value):
    global config, check_interval
    check_interval = value
    config["check_interval"] = value
    save_config(config)
    # Обновляем интервал в мониторинге
    icon.check_interval = value

# меню
menu = pystray.Menu(
    pystray.MenuItem("Открыть", open_recyclebin),
    pystray.MenuItem("Очистить", empty_recyclebin),
    pystray.MenuItem(
        "Персонализация",
        pystray.Menu(
            pystray.MenuItem(
                "Светлая тема",
                lambda icon, item: set_theme(icon, item, "light"),
                checked=lambda item: theme == "light",
                radio=True
            ),
            pystray.MenuItem(
                "Тёмная тема",
                lambda icon, item: set_theme(icon, item, "dark"),
                checked=lambda item: theme == "dark",
                radio=True
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Интервал проверки",
                pystray.Menu(
                    pystray.MenuItem(
                        "0.5 секунды",
                        lambda icon, item: set_check_interval(icon, item, 0.5),
                        checked=lambda item: check_interval == 0.5,
                        radio=True
                    ),
                    pystray.MenuItem(
                        "1 секунда",
                        lambda icon, item: set_check_interval(icon, item, 1),
                        checked=lambda item: check_interval == 1,
                        radio=True
                    ),
                    pystray.MenuItem(
                        "2 секунды",
                        lambda icon, item: set_check_interval(icon, item, 2),
                        checked=lambda item: check_interval == 2,
                        radio=True
                    ),
                    pystray.MenuItem(
                        "5 секунд",
                        lambda icon, item: set_check_interval(icon, item, 5),
                        checked=lambda item: check_interval == 5,
                        radio=True
                    ),
                )
            ),
        )
    ),
    pystray.MenuItem("Выход", lambda icon, item: icon.stop())
)

icon = pystray.Icon(
    "MicroBin",
    icon=Image.open(get_icon_path()),
    title="Micro Bin",
    menu=menu,
)

# Сохраняем текущий интервал в объекте иконки
icon.check_interval = check_interval

# Запускаем мониторинг корзины в отдельном потоке
icon.monitor_running = True
monitor_thread = threading.Thread(target=monitor_recycle_bin, args=(icon,))
monitor_thread.daemon = True
monitor_thread.start()

# Останавливаем мониторинг при выходе
original_stop = icon.stop
def stop_with_monitor():
    icon.monitor_running = False
    original_stop()
icon.stop = stop_with_monitor

icon.run()
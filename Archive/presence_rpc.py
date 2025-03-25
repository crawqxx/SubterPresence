import os
import psutil
import time
import webbrowser
from pypresence import Presence
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
import threading
import tkinter as tk
import sys
import ctypes
import traceback
from datetime import datetime

if sys.platform == 'win32':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

client_id = "1353747282234707988"
RPC = Presence(client_id)
RPC.connect()

game_name = "SubterPlayerBeta.exe"
user_status = None
game_id = None
start_time = None
last_game_state = False
log_file = "crash_log.txt"

def setup_crash_logging():
    if os.path.exists(log_file):
        os.remove(log_file)
    sys.excepthook = handle_exception

def handle_exception(exc_type, exc_value, exc_traceback):
    error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_msg = f"[{error_time}] CRASH:\n"
    error_msg += "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    with open(log_file, "a") as f:
        f.write(error_msg + "\n\n")
    os._exit(1)

def find_game_version():
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        if proc.info['name'] == game_name:
            exe_path = proc.info['exe']
            parent_dir = os.path.dirname(exe_path)
            folder_name = os.path.basename(parent_dir)
            if folder_name.startswith("Client"):
                return folder_name[6:]
    return None

def check_game_running():
    try:
        return any(p.info['name'] == game_name for p in psutil.process_iter(['name']))
    except:
        return False

def update_presence():
    global start_time, user_status, last_game_state, game_id
    while True:
        try:
            year = find_game_version()
            game_open = year is not None
            
            if game_open != last_game_state:
                if game_open:
                    start_time = int(time.time())
                    root.after(0, root.deiconify)
                else:
                    root.after(0, root.withdraw)
                last_game_state = game_open
            
            if game_open:
                status_text = f"Playing {year}"
                details = user_status if user_status else "Subter Player"
                buttons = []
                if game_id and game_id.strip():
                    buttons.append({"label": "Play Together", "url": f"https://subter.org/games/{game_id.strip()}"})
                RPC.update(state=status_text, details=details, start=start_time, buttons=buttons if buttons else None)
            else:
                RPC.clear()
            
            time.sleep(2)
        except Exception as e:
            handle_exception(type(e), e, e.__traceback__)

def create_image():
    image = Image.new('RGB', (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Subter", fill=(255, 255, 255))
    return image

def on_quit():
    RPC.close()
    os._exit(0)

def setup_tray():
    icon_image = create_image()
    menu = Menu(
        MenuItem('Show', lambda: root.deiconify()),
        MenuItem('Quit', on_quit)
    )
    icon = Icon("Subter", icon_image, "Subter Presence", menu)
    icon.run()

def update_presence_data():
    global user_status, game_id
    user_status = status_entry.get()
    game_id = game_id_entry.get()
    root.withdraw()

if __name__ == "__main__":
    setup_crash_logging()
    
    root = tk.Tk()
    root.title("Subter Presence")
    root.configure(bg='#2e2e2e')
    root.geometry('300x200')
    root.resizable(False, False)

    tk.Label(root, text="Custom Status", fg='white', bg='#2e2e2e').pack(pady=5)
    status_entry = tk.Entry(root, width=25)
    status_entry.pack(pady=5)

    tk.Label(root, text="Game ID", fg='white', bg='#2e2e2e').pack(pady=5)
    game_id_entry = tk.Entry(root, width=25)
    game_id_entry.pack(pady=5)

    tk.Button(root, text="Update Presence", command=update_presence_data).pack(pady=10)

    if check_game_running():
        root.deiconify()
    else:
        root.withdraw()

    presence_thread = threading.Thread(target=update_presence, daemon=True)
    presence_thread.start()

    root.protocol('WM_DELETE_WINDOW', root.withdraw)
    
    threading.Thread(target=setup_tray, daemon=True).start()
    
    root.mainloop()

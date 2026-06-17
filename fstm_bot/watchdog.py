import os
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

target_url = "https://e-resultat.fstm.ac.ma/index.php"
state_file = "known_announcements.json"
node_api_url = "http://localhost:3000/api/grades"

env_groups = ""
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("WATCHDOG_GROUP_IDS="):
                env_groups = line.strip().split("=", 1)[1].strip('"\'')

whatsapp_group_ids = [g.strip() for g in env_groups.split(",")] if env_groups else []

purple = '\033[35m'
green = '\033[32m'
cyan = '\033[36m'
red = '\033[31m'
reset = '\033[0m'

def get_timestamp():
    return datetime.now().strftime("%y-%m-%d %H:%M:%S")

def load_state():
    if os.path.exists(state_file):
        with open(state_file, "r", encoding='utf-8') as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()

def save_state(modules_set):
    with open(state_file, "w", encoding='utf-8') as f:
        json.dump(list(modules_set), f, ensure_ascii=False, indent=4)

def fetch_current_modules():
    headers = {
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        fonts = soup.find_all('font', color='black')
        
        extracted_modules = set()
        for font in fonts:
            text = font.text.strip()
            if text.startswith('-'):
                clean_name = text[1:].strip().lower()
                extracted_modules.add(clean_name)
                
        return extracted_modules

    except requests.RequestException as e:
        print(f"{red}[-] [{get_timestamp()}] network error: {e}{reset}")
        return None

def trigger_alert(new_modules):
    print(f"{purple}[*] alert: new modules detected!{reset}")
    
    message_body = "[*] *fstm alert : new results* [*]\n\nthe following modules have just been added to the portal:\n\n"
    for mod in new_modules:
        print(f"{green}[+] {mod}{reset}")
        message_body += f"[*] *{mod}*\n"
    
    message_body += "\n[*] https://e-resultat.fstm.ac.ma/deust/modules.php"
    
    for group_id in whatsapp_group_ids:
        payload = {
            "chatId": group_id,
            "message": message_body.lower()
        }
        
        try:
            response = requests.post(node_api_url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"{green}[+] payload successfully routed to: {group_id}{reset}")
            else:
                print(f"{red}[-] api error for {group_id}: {response.text.lower()}{reset}")
        except Exception as e:
            print(f"{red}[-] connection failed for {group_id}. is the node engine running?\nerror: {e}{reset}")
        
        time.sleep(1)

def update_recent_history(new_modules):
    history_file = "recent_history.json"
    recent_log = []
    
    if os.path.exists(history_file):
        with open(history_file, "r", encoding='utf-8') as f:
            try:
                recent_log = json.load(f)
            except json.JSONDecodeError:
                pass
                
    current_time = datetime.now().strftime("%d/%m at %H:%M")
    for mod in new_modules:
        recent_log.append({"name": mod.lower(), "time": current_time})
        
    recent_log = recent_log[-10:]
    
    with open(history_file, "w", encoding='utf-8') as f:
        json.dump(recent_log, f, ensure_ascii=False, indent=4)

def run_watchdog():
    print(f"{cyan}[*] fstm watchdog initialized. monitoring every 45 seconds...{reset}")
    
    if not os.path.exists(state_file):
        print(f"{cyan}[*] no state file found. building initial baseline...{reset}")
        initial_modules = fetch_current_modules()
        if initial_modules:
            save_state(initial_modules)
            print(f"{green}[+] baseline established: {len(initial_modules)} modules tracked.{reset}\n")

    while True:
        try:
            known_modules = load_state()
            current_modules = fetch_current_modules()
            
            if current_modules is not None:
                new_modules = current_modules - known_modules
                
                if new_modules:
                    trigger_alert(new_modules)
                    update_recent_history(new_modules)
                    
                    known_modules.update(new_modules)
                    save_state(known_modules)
                else:
                    print(f"[{get_timestamp()}] [*] scan complete. no changes detected.")
            
            time.sleep(45)
            
        except KeyboardInterrupt:
            print(f"\n{red}[-] watchdog terminated by user.{reset}")
            break

if __name__ == "__main__":
    run_watchdog()

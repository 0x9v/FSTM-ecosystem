import os
import sys
import time
import random
import argparse
import requests
from bs4 import BeautifulSoup
import mysql.connector
from typing import List, Dict, Optional, Any

purple, bold, reset = '\033[35m', '\033[1m', '\033[0m'
red, green, cyan = '\033[31m', '\033[32m', '\033[36m'

url = "https://e-resultat.fstm.ac.ma/deust/modules.php"
db_config = {
    'user': 'root',
    'password': '',
    'host': '127.0.0.1',
    'database': 'fstm_grades'
}

user_agents = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def init_db() -> mysql.connector.connection.MySQLConnection:
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"{red}[-] db error: {err}{reset}")
        sys.exit(1)

def parse_grade(val_str: str) -> Optional[float]:
    if not val_str or val_str.lower() in ["-", "abs", "none", ""]:
        return None
    try:
        return float(val_str.replace(',', '.').strip())
    except ValueError:
        return None

def save_to_db(cursor, conn, data: Dict[str, Any]):
    query = """
    insert into notes (massar, full_name, parcours, module_name, tp, exam, moyenne, resultat, is_rattrapage)
    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    on duplicate key update
        parcours = values(parcours),
        tp = ifnull(values(tp), tp),
        exam = ifnull(values(exam), exam),
        moyenne = values(moyenne),
        resultat = values(resultat),
        is_rattrapage = values(is_rattrapage);
    """
    
    tp_val = parse_grade(data.get('tp', ''))
    exam_val = parse_grade(data.get('exam', ''))
    moy_val = parse_grade(data.get('moy', ''))
    full_name = f"{data.get('nom', '')} {data.get('prenom', '')}".strip()

    vals = (
        data.get('massar', 'unknown'), full_name, data.get('parcours', 'unknown'), 
        data.get('module', 'unknown'), tp_val, exam_val, moy_val, 
        data.get('res', '-'), data.get('is_rattrapage', False)
    )
    
    try:
        cursor.execute(query, vals)
        conn.commit()
    except mysql.connector.Error as err:
        print(f"\n{red}[-] db write failed: {err}{reset}")

def find_column_index(headers: List[str], keywords: List[str]) -> int:
    clean_headers = [h.lower().replace('é', 'e').strip() for h in headers]
    for kw in keywords:
        for idx, header in enumerate(clean_headers):
            if kw == 'note' and ('tp' in header or 'exam' in header):
                continue
            if kw in header:
                return idx
    return -1

def parse_html_to_data(html_content: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_data = []

    for div in soup.find_all('div', class_='table-responsive'):
        title_tag = div.find_previous('font', color='blue')
        raw_name = title_tag.text.strip() if title_tag else "unknown"
        is_rattrapage = "(résultat final)" in raw_name.lower()
        module_name = raw_name.replace("(Résultat final)", "").replace("(résultat final)", "").strip().lower()

        thead = div.find('thead')
        tbody = div.find('tbody')
        if not thead or not tbody:
            continue
            
        headers = [th.text.strip() for th in thead.find_all('th')]
        
        indices = {
            'massar': find_column_index(headers, ['code']),
            'nom': find_column_index(headers, ['nom']),
            'prenom': find_column_index(headers, ['prenom']),
            'parcours': find_column_index(headers, ['parcours', 'parc']),
            'tp': find_column_index(headers, ['tp']),
            'exam': find_column_index(headers, ['exam', 'normale']),
            'moy': find_column_index(headers, ['moyenne finale', 'note finale', 'moyenne', 'moy', 'note']),
            'res': find_column_index(headers, ['resultat', 'res'])
        }

        for row in tbody.find_all('tr'):
            cols = [col.text.strip() for col in row.find_all(['th', 'td'])]
            if len(cols) < 5:
                continue
            
            def get_val(key):
                idx = indices[key]
                return cols[idx].lower() if idx != -1 and idx < len(cols) else ("-" if key in ['tp', 'exam', 'moy', 'res'] else "unknown")

            extracted_data.append({
                "module": module_name,
                "is_rattrapage": is_rattrapage,
                "massar": get_val('massar'),
                "nom": get_val('nom'),
                "prenom": get_val('prenom'),
                "parcours": get_val('parcours'),
                "tp": get_val('tp'),
                "exam": get_val('exam'),
                "moy": get_val('moy'),
                "res": get_val('res')
            })
            
    return extracted_data

def fetch_student_data(session: requests.Session, student_id: str) -> Optional[List[Dict[str, Any]]]:
    headers = {
        'user-agent': random.choice(user_agents),
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://e-resultat.fstm.ac.ma',
        'referer': url
    }
    payload = {'code': student_id, 'afficher': ''}    
    try:
        response = session.post(url, data=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return parse_html_to_data(response.text)
    except requests.RequestException:
        return None

def main():
    parser = argparse.ArgumentParser(description="fstm e-resultat extractor (cli)")
    parser.add_argument("-f", "--file", type=str, help="path to the text file containing massar ids")
    args = parser.parse_args()

    print(f"\n{purple}{bold}[*] fstm data extractor{reset}")

    target_file = args.file or input(f"{cyan}[*] enter the name of the id file (e.g., ids.txt): {reset}").strip()

    if not os.path.isfile(target_file):
        print(f"{red}[-] error: file '{target_file}' not found.{reset}")
        sys.exit(1)

    with open(target_file, "r") as f:
        student_ids = [line.strip() for line in f if line.strip()]
    
    total_ids = len(student_ids)
    print(f"{green}[+] loaded {total_ids} ids from {target_file}{reset}\n")

    db_conn = init_db()
    cursor = db_conn.cursor()
    print(f"{green}[+] connected to mariadb.{reset}\n")

    failed_ids = []
    start_time = time.time()
    
    with requests.Session() as session:
        try:
            for index, student_id in enumerate(student_ids, 1):
                elapsed = time.time() - start_time
                avg_time = elapsed / index
                eta_seconds = int(avg_time * (total_ids - index))
                m, s = divmod(eta_seconds, 60)
                
                print(f"\r{purple}[*] [{index}/{total_ids}]{reset} fetching {bold}{student_id}{reset} (eta: {m:02d}:{s:02d}) ... ", end="", flush=True)
                
                data_list = fetch_student_data(session, student_id)
                
                if data_list is None:
                    print(f"{red}[-] network err{reset}")
                    failed_ids.append(student_id)
                    continue
                
                if not data_list:
                    print(f"{cyan}[*] no data{reset}")
                    continue

                for data in data_list:
                    save_to_db(cursor, db_conn, data)

                print(f"{green}[+] done{reset}")
                time.sleep(random.uniform(0.2, 0.6))
                
        except KeyboardInterrupt:
            print(f"\n\n{red}[-] execution interrupted by user.{reset}")
        
        finally:
            cursor.close()
            db_conn.close()
            
            print(f"\n{purple}{bold}[*] summary{reset}")
            print(f"[*] processed: {total_ids}")
            if failed_ids:
                print(f"{red}[-] failed ids: {len(failed_ids)}{reset}")
                with open("failed_extraction.txt", "w") as f:
                    f.write("\n".join(failed_ids))
                print("[+] failed ids saved to 'failed_extraction.txt'")

if __name__ == "__main__":
    main()

import os
import sys
import time
import random
import requests
from bs4 import BeautifulSoup

purple, bold, reset = "\033[35m", "\033[1m", "\033[0m"
cyan, green, red = "\033[36m", "\033[32m", "\033[31m"

url = "https://e-resultat.fstm.ac.ma/deust/modules.php"
user_agents = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
]


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def scan_for_modules(file_path):
    try:
        with open(file_path, "r") as f:
            student_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"{red}[-] error: file '{file_path}' not found.{reset}")
        sys.exit(1)

    unique_modules = set()
    total_ids = len(student_ids)
    print(f"{purple}{bold}[*] === FSTM MODULE RECONNAISSANCE ENGINE ==={reset}\n")
    print(f"{cyan}[*] scanning {total_ids} students for raw module names...{reset}")

    with requests.Session() as session:
        for i, massar in enumerate(student_ids, 1):
            headers = {"user-agent": random.choice(user_agents)}
            payload = {"code": massar, "afficher": ""}

            print(
                f"\r{purple}[*] [{i}/{total_ids}]{reset} probing {bold}{massar}{reset} ... ",
                end="",
                flush=True,
            )

            try:
                res = session.post(url, data=payload, headers=headers, timeout=10)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")

                for div in soup.find_all("div", class_="table-responsive"):
                    title_tag = div.find_previous("font", color="blue")
                    if title_tag:
                        raw_name = title_tag.text.strip()

                        # Strip the rattrapage tags to merge sessions, lower it, and crush weird spaces
                        clean_name = (
                            raw_name.replace("(Résultat final)", "")
                            .replace("(résultat final)", "")
                            .strip()
                            .lower()
                        )
                        clean_name = " ".join(clean_name.split())

                        unique_modules.add(clean_name)

            except Exception:
                # Silent fail for speed on broken network requests
                pass

    print(
        f"\n\n{green}[+] scan complete. successfully isolated {len(unique_modules)} unique module strings.{reset}"
    )

    # Dump the sorted set to a text file
    output_file = "fstm_raw_modules.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for mod in sorted(unique_modules):
            f.write(f"{mod}\n")

    print(
        f"{green}[+] data locked. open '{output_file}' in neovim to see the administration's chaos.{reset}\n"
    )


if __name__ == "__main__":
    clear_screen()
    target_file = input(
        f"{cyan}[*] enter your massar list file (e.g., ids.txt): {reset}"
    ).strip()
    scan_for_modules(target_file)

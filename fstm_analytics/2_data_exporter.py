import os
import sys
import mysql.connector
from tabulate import tabulate
from fpdf import FPDF

purple = '\033[35m'
bold = '\033[1m'
reset = '\033[0m'
cyan = '\033[36m'
red = '\033[31m'
green = '\033[32m'
bg_black = '\033[40m'

ui_primary = f"{bg_black}{purple}{bold}"
ui_text = f"{bg_black}{purple}"

db_config = {
    'user': 'root',
    'password': '',
    'host': '127.0.0.1',
    'database': 'fstm_grades'
}

valid_columns = ['massar', 'full_name', 'parcours', 'module_name', 'tp', 'exam', 'moyenne', 'resultat', 'is_rattrapage']

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def init_db():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"{red}[-] db error: {err}{reset}")
        sys.exit(1)

def ask_menu(title, options, allow_multiple=False, default_idx=None):
    print(f"\n{ui_primary}[*] === {title} ==={reset}")
    for i, opt in enumerate(options, 1):
        if default_idx is not None and i - 1 == default_idx:
            print(f"{ui_text}[{i}]{reset} {opt} {cyan}(default){reset}")
        else:
            print(f"{ui_text}[{i}]{reset} {opt}")
    
    while True:
        try:
            if allow_multiple:
                choice = input(f"\n{cyan}[*] select numbers (comma-separated) or press enter for all: {reset}").strip()
                if choice == '' or choice.lower() == 'all':
                    return options
                indices = [int(x.strip()) - 1 for x in choice.split(',')]
                return [options[i] for i in indices]
            else:
                prompt_str = f"select an option (1-{len(options)})"
                if default_idx is not None:
                    prompt_str += " or press enter for default"
                
                choice = input(f"\n{cyan}[*] {prompt_str}: {reset}").strip()
                
                if choice == '' and default_idx is not None:
                    return options[default_idx]
                
                choice = int(choice)
                if 1 <= choice <= len(options):
                    return options[choice - 1]
                print(f"{red}[-] invalid selection. try again.{reset}")
        except (ValueError, IndexError):
            print(f"{red}[-] please enter valid numbers.{reset}")

def generate_pdf(headers, data, filename="export.pdf", title="fstm grades report"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, title, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    ratt_idx = -1
    for i, h in enumerate(headers):
        if str(h).lower() == 'is_rattrapage':
            ratt_idx = i
            break

    cleaned_data = []
    for row in data:
        cleaned_row = []
        for i, item in enumerate(row):
            if i == ratt_idx:
                val = "rattrapage" if str(item).strip() in ['1', 'True'] else "normale"
            else:
                val = f"{item:.2f}" if isinstance(item, float) else str(item)
                if val == "None": val = "-"
            cleaned_row.append(val)
        cleaned_data.append(cleaned_row)

    page_w = pdf.epw
    
    base_widths = {
        '#': 10, 
        'massar': 25, 
        'parcours': 22, 
        'tp': 15, 
        'exam': 15, 
        'moyenne': 18, 
        'resultat': 18, 
        'is_rattrapage': 25
    }
    
    actual_widths = []
    flexible_cols = []
    
    for i, h in enumerate(headers):
        h_lower = str(h).lower()
        if h_lower in base_widths:
            actual_widths.append(base_widths[h_lower])
        else:
            actual_widths.append(0)
            flexible_cols.append(i)
    
    used_w = sum(actual_widths)
    remaining_w = page_w - used_w
    
    if flexible_cols:
        flex_w = remaining_w / len(flexible_cols)
        for i in flexible_cols:
            actual_widths[i] = flex_w

    def truncate(text, max_w):
        max_chars = int(max_w / 1.6)
        if len(text) > max_chars:
            return text[:max_chars-2] + ".."
        return text

    line_height = 6
    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(200, 200, 200)
    for i, header in enumerate(headers):
        safe_header = truncate(str(header).lower(), actual_widths[i])
        pdf.cell(actual_widths[i], line_height, safe_header, border=1, fill=True, align="C")
    pdf.ln(line_height)

    pdf.set_font("helvetica", "", 8)
    for row in cleaned_data:
        for i, item in enumerate(row):
            safe_item = truncate(item.lower(), actual_widths[i])
            pdf.cell(actual_widths[i], line_height, safe_item, border=1, align="C")
        pdf.ln(line_height)

    pdf.output(filename)

def main():
    clear_screen()
    print(f"{ui_primary}[*] === fstm data export wizard ==={reset}\n")
    
    db_conn = init_db()
    cursor = db_conn.cursor()

    try:
        cursor.execute("select distinct module_name from notes order by module_name")
        modules = [row[0] for row in cursor.fetchall()]
        
        if not modules:
            print(f"{red}[-] no data found in the database. run the scraper first.{reset}")
            return
            
        selected_module = ask_menu("select module", modules)

        selected_cols = ask_menu("select columns to export", valid_columns, allow_multiple=True)
        cols_string = ", ".join(selected_cols)

        sort_options = [
            "moyenne (highest first) -> moyenne desc",
            "moyenne (lowest first) -> moyenne asc",
            "exam (highest first) -> exam desc",
            "tp (highest first) -> tp desc",
            "alphabetical (a-z) -> full_name asc"
        ]
        selected_sort = ask_menu("sorting order", sort_options, default_idx=0)
        order_clause = selected_sort.split("->")[1].strip()

        limit_options = ["top 10", "top 50", "top 100", "all rows"]
        selected_limit_str = ask_menu("number of rows", limit_options, default_idx=3)
        limit_val = 10000 if selected_limit_str == "all rows" else int(selected_limit_str.split()[1])

        format_options = ["cli (view in terminal)", "txt (markdown table)", "pdf (formal report)"]
        selected_format = ask_menu("output format", format_options, default_idx=0).split(" ")[0].lower()

        clear_screen()
        print(f"{ui_text}[*] fetching data...{reset}\n")
        
        query = f"select {cols_string} from notes where module_name = %s order by {order_clause} limit {limit_val}"
        cursor.execute(query, (selected_module,))
        raw_results = cursor.fetchall()

        if not raw_results:
            print(f"{cyan}[-] no records match this criteria.{reset}")
            return

        headers_with_index = ["#"] + selected_cols
        indexed_results = []
        for index, row in enumerate(raw_results, 1):
            indexed_results.append((index,) + row)

        if selected_format == 'cli':
            print(f"{ui_primary}[+] === results: {selected_module.lower()} ==={reset}")
            print(tabulate(indexed_results, headers=headers_with_index, tablefmt="fancy_grid", floatfmt=".2f", missingval="-").lower())
            print(f"\n{ui_text}[*] total rows extracted: {len(indexed_results)}{reset}\n")

        elif selected_format == 'txt':
            filename = input(f"{cyan}[*] enter output filename (without .txt): {reset}").strip() + ".txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"module: {selected_module.lower()}\n")
                f.write("=" * 70 + "\n")
                f.write(tabulate(indexed_results, headers=headers_with_index, tablefmt="github", floatfmt=".2f", missingval="-").lower())
            print(f"{green}[+] saved to {filename}{reset}")

        elif selected_format == 'pdf':
            filename = input(f"{cyan}[*] enter output filename (without .pdf): {reset}").strip() + ".pdf"
            generate_pdf(headers_with_index, indexed_results, filename=filename, title=f"fstm: {selected_module[:40].lower()}")
            print(f"{green}[+] generated {filename}{reset}")

    finally:
        cursor.close()
        db_conn.close()

if __name__ == "__main__":
    main()

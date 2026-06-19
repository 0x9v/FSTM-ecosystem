import os
import io
import sys
import base64
import mysql.connector
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from tabulate import tabulate
from fpdf import FPDF
from weasyprint import HTML

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

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def init_db():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"{red}[-] db error: {err}{reset}")
        sys.exit(1)

def ask_menu(title, options, default_idx=None):
    print(f"\n{ui_primary}[*] === {title} ==={reset}")
    for i, opt in enumerate(options, 1):
        if default_idx is not None and i - 1 == default_idx:
            print(f"{ui_text}[{i}]{reset} {opt} {cyan}(default){reset}")
        else:
            print(f"{ui_text}[{i}]{reset} {opt}")
    
    while True:
        try:
            prompt_str = f"select an option (1-{len(options)})"
            if default_idx is not None:
                prompt_str += " or press enter for default"
            
            choice = input(f"\n{cyan}[*] {prompt_str}: {reset}").strip()
            
            if choice == '' and default_idx is not None:
                return options[default_idx], default_idx
            
            choice = int(choice)
            if 1 <= choice <= len(options):
                return options[choice - 1], choice - 1
            print(f"{red}[-] invalid selection.{reset}")
        except ValueError:
            print(f"{red}[-] please enter a valid number.{reset}")

def calculate_stats(grades):
    arr = np.array(grades)
    count = len(arr)
    if count == 0: return None

    stats = {
        'count': count,
        'mean': np.mean(arr),
        'median': np.median(arr),
        'std': np.std(arr),
        'var': np.var(arr),
        'max': np.max(arr),
        'min': np.min(arr),
        'p95': np.percentile(arr, 95),
        'p90': np.percentile(arr, 90),
        'q25': np.percentile(arr, 25),
        'q50': np.median(arr),
        'q75': np.percentile(arr, 75),
        'fail_rate': len(arr[arr < 10]) / count * 100 if count > 0 else 0,
        'total_fail': len(arr[arr < 10]),
        'eliminated': len(arr[arr < 5]),
        'rattrapage': len(arr[(arr >= 5) & (arr < 10)]),
        'frustration': len(arr[(arr >= 9) & (arr < 10)]),
        'pass_ok': len(arr[(arr >= 10) & (arr < 12)]),
        'pass_good': len(arr[(arr >= 12) & (arr < 14)]),
        'pass_exc': len(arr[arr >= 14]),
        'g_elim': len(arr[arr < 5]),
        'g_rat': len(arr[(arr >= 5) & (arr < 10)]),
        'g_pass': len(arr[(arr >= 10) & (arr < 12)]),
        'g_good': len(arr[(arr >= 12) & (arr < 14)]),
        'g_exc': len(arr[arr >= 14]),
        'false_hope': len(arr[(arr >= 8) & (arr < 10)]),
        'slaughter': len(arr[arr < 5])
    }
    return stats

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=200, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def safe_bar(val, total):
    if total == 0: return ""
    return "█" * int((val / total) * 35)

def generate_pdf_report(module, metric, session_label, stats, grades, parcours_data, filename="beautiful_stats.pdf"):
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['text.color'] = '#2c3e50'
    colors = ['#e74c3c', '#f39c12', '#2ecc71', '#3498db']

    labels = ['eliminated (<5)', 'rattrapage (5-10)', 'validated (10-14)', 'elite (14-20)']
    sizes = [stats['eliminated'], stats['rattrapage'], stats['pass_ok'] + stats['pass_good'], stats['pass_exc']]
    f_labels = [l for s, l in zip(sizes, labels) if s > 0]
    f_sizes = [s for s in sizes if s > 0]
    f_colors = [c for s, c in zip(sizes, colors) if s > 0]

    fig1, ax1 = plt.subplots(figsize=(5, 5))
    if f_sizes:
        wedges, _, _ = ax1.pie(
            f_sizes, labels=None, colors=f_colors, 
            autopct='%1.1f%%', startangle=140, pctdistance=0.75,
            wedgeprops=dict(width=0.4, edgecolor='none'),
            textprops={'color': 'white', 'fontsize': 10, 'weight': 'bold'}
        )
        ax1.legend(wedges, f_labels, title="categories", loc="center left", bbox_to_anchor=(0.9, 0, 0.5, 1), frameon=False)
        ax1.text(0, 0, f"pass rate\n{100 - stats['fail_rate']:.1f}%", ha='center', va='center', fontsize=12, weight='bold', color='#2c3e50')
    donut_b64 = fig_to_base64(fig1)

    fig2, ax2 = plt.subplots(figsize=(5, 5))
    p_names = [p[0] for p in parcours_data][::-1]
    p_avgs = [p[1] for p in parcours_data][::-1]
    bars = ax2.barh(p_names, p_avgs, color='#3498db', height=0.6, edgecolor='none')
    ax2.axvline(stats['mean'], color='#e74c3c', linestyle='dashed', linewidth=1.5, zorder=0)

    for spine in ['top', 'right', 'bottom', 'left']: ax2.spines[spine].set_visible(False)
    ax2.xaxis.set_visible(False)
    ax2.tick_params(left=False)

    for bar in bars:
        width = bar.get_width()
        ax2.text(width + 0.3, bar.get_y() + bar.get_height()/2, f'{width:.1f}', 
                 va='center', ha='left', color='#2c3e50', weight='bold', fontsize=10)
    ax2.text(stats['mean'] + 0.2, len(p_names)-0.5, f"avg ({stats['mean']:.1f})", color='#e74c3c', weight='bold', fontsize=9)
    bar_b64 = fig_to_base64(fig2)

    fig3, ax3 = plt.subplots(figsize=(10, 4.5))
    ax3.grid(axis='y', color='#ecf0f1', linestyle='-', linewidth=1)
    ax3.set_axisbelow(True)
    ax3.hist(grades, bins=20, range=(0, 20), color='#34495e', edgecolor='white', linewidth=1.2, alpha=0.9)

    ax3.axvline(10, color='#e74c3c', linestyle='dashed', linewidth=2, label="pass threshold (10.0)")
    ax3.axvline(stats['mean'], color='#3498db', linestyle='dashed', linewidth=2, label=f"mean ({stats['mean']:.2f})")
    ax3.axvline(stats['p95'], color='#2ecc71', linestyle='dashed', linewidth=2, label=f"top 5% ({stats['p95']:.2f})")

    for spine in ['top', 'right', 'left']: ax3.spines[spine].set_visible(False)
    ax3.spines['bottom'].set_color('#bdc3c7')
    ax3.tick_params(bottom=False, left=False)
    ax3.set_xlim(0, 20)
    ax3.legend(loc='upper left', frameon=False, labelcolor='#2c3e50', prop={'weight':'bold'})
    ax3.set_xlabel('score / 20', color='#7f8c8d', weight='bold')
    dist_b64 = fig_to_base64(fig3)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 20mm; background-color: #f4f7f6; }}
            body {{ margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #2c3e50; font-size: 11pt; line-height: 1.5; text-transform: lowercase; }}
            *, *::before, *::after {{ box-sizing: border-box; }}
            
            .header {{ margin: -20mm -20mm 15mm -20mm; padding: 25mm 20mm 15mm 20mm; background-color: #1e293b; color: white; border-bottom: 6px solid #3b82f6; }}
            .header h1 {{ margin: 0 0 5px 0; font-size: 22pt; font-weight: 600; letter-spacing: -0.5px; text-transform: lowercase; }}
            .header p {{ margin: 0; color: #94a3b8; font-size: 11pt; letter-spacing: 1.5px; font-weight: 600; }}
            
            .section-title {{ font-size: 13pt; color: #0f172a; border-left: 4px solid #3b82f6; padding-left: 10px; margin-top: 25px; margin-bottom: 15px; font-weight: bold; letter-spacing: 1px; page-break-after: avoid; }}
            
            .chart-row {{ display: table; width: 100%; margin-bottom: 25px; table-layout: fixed; background: white; border-radius: 8px; border: 1px solid #e2e8f0; padding: 15px 0; }}
            .chart-col {{ display: table-cell; width: 50%; vertical-align: top; text-align: center; }}
            .chart-title {{ font-size: 11pt; font-weight: bold; color: #64748b; margin-bottom: 5px; }}
            .chart-col img {{ max-width: 95%; height: auto; }}

            .stats-block {{ display: table; width: calc(100% + 30px); margin-bottom: 25px; table-layout: fixed; border-spacing: 15px 0; margin-left: -15px; margin-right: -15px; }}
            .stats-cell {{ display: table-cell; width: 50%; background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; vertical-align: top; }}
            .stat-item {{ margin-bottom: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }}
            .stat-item:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
            .stat-label {{ color: #64748b; font-size: 10pt; }}
            .stat-value {{ font-size: 12pt; font-weight: bold; color: #0f172a; float: right; }}
            
            .val-red {{ color: #ef4444; }} .val-orange {{ color: #f59e0b; }}
            
            .gaussian-box {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; font-family: 'Courier New', monospace; font-size: 10pt; color: #334155; line-height: 1.6; margin-bottom: 25px; }}
            .g-bar {{ color: #3b82f6; }} .g-label {{ display: inline-block; width: 140px; }} .g-count {{ display: inline-block; width: 40px; font-weight: bold; }}

            .full-width-chart {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; text-align: center; }}
            .full-width-chart img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>

        <div class="header">
            <h1>{module}</h1>
            <p>{metric} | session: {session_label}</p>
        </div>

        <div class="section-title">macro distribution & leaderboard</div>
        <div class="chart-row">
            <div class="chart-col">
                <div class="chart-title">status distribution</div>
                <img src="data:image/png;base64,{donut_b64}" alt="donut chart" />
            </div>
            <div class="chart-col">
                <div class="chart-title">major leaderboard</div>
                <img src="data:image/png;base64,{bar_b64}" alt="bar chart" />
            </div>
        </div>

        <div class="section-title">core performance metrics</div>
        <div class="stats-block">
            <div class="stats-cell">
                <div class="stat-item"><span class="stat-label">global failure rate</span><span class="stat-value val-red">{stats['fail_rate']:.1f}% ({stats['total_fail']}/{stats['count']})</span></div>
                <div class="stat-item"><span class="stat-label">elimination (&lt;5)</span><span class="stat-value">{stats['eliminated']} students</span></div>
                <div class="stat-item"><span class="stat-label">rattrapage (5-10)</span><span class="stat-value val-orange">{stats['rattrapage']} students</span></div>
                <div class="stat-item"><span class="stat-label">frustration (9-9.9)</span><span class="stat-value">{stats['frustration']} students</span></div>
            </div>
            <div class="stats-cell">
                <div class="stat-item"><span class="stat-label">class average</span><span class="stat-value">{stats['mean']:.2f} / 20</span></div>
                <div class="stat-item"><span class="stat-label">median (middle)</span><span class="stat-value">{stats['median']:.2f} / 20</span></div>
                <div class="stat-item"><span class="stat-label">standard deviation</span><span class="stat-value">{stats['std']:.2f}</span></div>
                <div class="stat-item"><span class="stat-label">extremes (min - max)</span><span class="stat-value">{stats['min']:.1f} - {stats['max']:.1f}</span></div>
            </div>
        </div>

        <div class="section-title">simplified gaussian curve</div>
        <div class="gaussian-box">
            <div><span class="g-label">[00 - 05[ (elim.)</span> <span class="g-count">{stats['g_elim']}</span> <span class="g-bar">{safe_bar(stats['g_elim'], stats['count'])}</span></div>
            <div><span class="g-label">[05 - 10[ (rat.)</span> <span class="g-count">{stats['g_rat']}</span> <span class="g-bar">{safe_bar(stats['g_rat'], stats['count'])}</span></div>
            <div><span class="g-label">[10 - 12[ (pass)</span> <span class="g-count">{stats['g_pass']}</span> <span class="g-bar">{safe_bar(stats['g_pass'], stats['count'])}</span></div>
            <div><span class="g-label">[12 - 14[ (good)</span> <span class="g-count">{stats['g_good']}</span> <span class="g-bar">{safe_bar(stats['g_good'], stats['count'])}</span></div>
            <div><span class="g-label">[14 - 20] (elite)</span> <span class="g-count">{stats['g_exc']}</span> <span class="g-bar">{safe_bar(stats['g_exc'], stats['count'])}</span></div>
        </div>

        <div class="section-title" style="page-break-before: always; padding-top: 10px;">grade dispersion ridge</div>
        <div class="full-width-chart">
            <img src="data:image/png;base64,{dist_b64}" alt="distribution ridge" />
        </div>

    </body>
    </html>
    """

    HTML(string=html_content).write_pdf(filename)
    print(f"[+] successfully generated: {filename}")


def main():
    clear_screen()
    print(f"{ui_primary}[*] === fstm statistical forensics ==={reset}\n")
    
    db_conn = init_db()
    cursor = db_conn.cursor()

    try:
        cursor.execute("select distinct module_name from notes order by module_name")
        modules = [row[0] for row in cursor.fetchall()]
        if not modules:
            print(f"{red}[-] no data found.{reset}")
            return
        selected_module, _ = ask_menu("select module to analyze", modules)

        session_options = ["normale", "rattrapage", "combined"]
        selected_session, s_idx = ask_menu("select session", session_options, default_idx=0)

        metrics = ["exam", "moyenne", "tp"]
        selected_metric, m_idx = ask_menu("select target metric", metrics, default_idx=0)
        actual_metric = metrics[m_idx]

        clear_screen()
        print(f"{ui_text}[*] crunching {actual_metric} data for {selected_module.lower()} ({selected_session})...{reset}\n")

        query_base = f"select {actual_metric}, parcours from notes where module_name = %s and {actual_metric} is not null"
        params = [selected_module]

        if s_idx == 0:
            query_base += " and is_rattrapage = 0"
        elif s_idx == 1:
            query_base += " and is_rattrapage = 1"

        cursor.execute(query_base, tuple(params))
        results = cursor.fetchall()

        if not results:
            print(f"{red}[-] no valid {actual_metric} data found for this session/module.{reset}")
            return

        grades = [float(row[0]) for row in results]
        stats = calculate_stats(grades)

        parcours_dict = {}
        for row in results:
            p = row[1]
            if p not in parcours_dict:
                parcours_dict[p] = []
            parcours_dict[p].append(float(row[0]))
        
        parcours_leaderboard = []
        for p, p_grades in parcours_dict.items():
            parcours_leaderboard.append((p, np.mean(p_grades), len(p_grades)))
        parcours_leaderboard.sort(key=lambda x: x[1], reverse=True)

        clean_module_name = "".join([c if c.isalnum() else "_" for c in selected_module])[:30].lower()
        default_pdf_name = f"{clean_module_name}_{actual_metric}_{selected_session}.pdf"
        
        user_filename = input(f"{cyan}[*] enter filename (press enter for '{default_pdf_name}'): {reset}").strip()
        final_filename = user_filename + ".pdf" if user_filename else default_pdf_name
        
        generate_pdf_report(
            module=selected_module.lower(), 
            metric=actual_metric,
            session_label=selected_session,
            stats=stats, 
            grades=grades, 
            parcours_data=parcours_leaderboard, 
            filename=final_filename
        )

    finally:
        cursor.close()
        db_conn.close()

if __name__ == "__main__":
    main()

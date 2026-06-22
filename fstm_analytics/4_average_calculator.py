import os
import sys
import mysql.connector
from tabulate import tabulate

# --- UI Styling ---
purple = "\033[35m"
bold = "\033[1m"
reset = "\033[0m"
cyan = "\033[36m"
red = "\033[31m"
green = "\033[32m"

db_config = {
    "user": "root",
    "password": "",
    "host": "127.0.0.1",
    "database": "fstm_grades",
}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def normalize_string(s):
    """Crushes double spaces, strips accents, and standardizes strings."""
    if not s:
        return ""
    # Convert common accented characters to plain text
    import unicodedata

    s = str(s).lower()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return " ".join(s.split())


# --- La Matrice Globale FSTM Validée et Normalisée (Clés sans accents) ---
MODULE_MAP = {
    # ==================== FILIÈRE : GI (Génie Informatique) ====================
    "analyse3 m231gi": "S3",
    "microcontroleur et capteurs e233gi": "S3",
    "art et culture s231gi": "S3",
    "langues etrangeres s3 - anglais- l231gi": "S3",
    "algorithmique et programmation 2 i231gigese": "S3",
    "structure de donnees i232gigese": "S3",
    "systeme d'information et bases donnees i233gi": "S3",
    "statistiques et probabilites m242gigese": "S4",
    "analyse numerique m241gesegi": "S4",
    "analyse numerique m241gigese": "S4",
    "dev personnel s241gi": "S4",
    "dev personnel s241gigese": "S4",
    "langues s4 l241gigese": "S4",
    "developpement web i242gi": "S4",
    "architecture des ordinateurs i241gi": "S4",
    "recherche operationnelle m243gi": "S4",
    # ==================== FILIÈRE : GE (Génie Électrique) ====================
    "electronique analogique e231gese": "S3",
    "electromagnetisme p131gese": "S3",
    "capteurs et instrumentation e232gese": "S3",
    "langues etrangeres s3 - anglais- l231gese": "S3",
    "langues etrangeres s3 - anglais- l231gesegi": "S3",
    "art et culture s231gese": "S3",
    # Partagé GI/GE
    "structure de donnees i232gigese": "S3",
    "algorithmique et programmation 2 i231gigese": "S3",
    "electronique numerique e241gese": "S4",
    "electrotechnique e242gese": "S4",
    "automatique e243gese": "S4",
    "dev personnel s241gese": "S4",
    "analyse numerique m241gesegi": "S4",
    "analyse numerique m241gigese": "S4",
    "langues s4 l241gigese": "S4",
    # ==================== FILIÈRE : GP (Génie Procédés) ====================
    "mecanique du solide p132gp": "S3",
    "electromagnetisme p131gp": "S3",
    "art et culture s131gp": "S3",
    "langues etrangeres s3 - anglais- l131gp": "S3",
    "algorithmique & programmation 2 i131gpmsd": "S3",
    "analyse numerique m131gpmsd": "S3",
    "statistiques et probabilites m132gpmsd": "S3",
    "structures de donnees i141gp": "S4",
    "optique physique p141gp": "S4",
    "mecanique des fluides et transfert ther p142gp": "S4",
    "dev personnel s141gp": "S4",
    "analyse 3 m141gpmsd": "S4",
    "analyse 4 m142gpmsd": "S4",
    "langues etrangeres s4 l141gpmsd": "S4",
    # ==================== FILIÈRE : MSD (Mathématiques & Sciences de Données) ====================
    "algebre 3 m133msd": "S3",
    "art et culture s131msd": "S3",
    "langues etrangeres s3 - anglais- l131msd": "S3",
    "langues etrangeres s3 - anglais- l131gpmsd": "S3",
    "systeme d'information et bases donnees i233msd": "S3",
    # Partagé GP/MSD
    "algorithmique & programmation 2 i131gpmsd": "S3",
    "analyse numerique m131gpmsd": "S3",
    "statistiques et probabilites m132gpmsd": "S3",
    "enquetes et techniques de sondage m143msd": "S4",
    "inference statistique et applications m145msd": "S4",
    "analyse de donnees / modeles de regress m144msd": "S4",
    "dev personnel s141msd": "S4",
    "analyse 3 m141gpmsd": "S4",
    "analyse 4 m142gpmsd": "S4",
    "langues etrangeres s4 l141gpmsd": "S4",
}


def load_whitelists():
    whitelist = {}
    files = {
        "GI": "listeGIS4.list",
        "GE": "listeGES4.list",
        "GP": "listeGPS4.list",
        "MSD": "listeMSDS4.list",
    }
    for filiere, filename in files.items():
        try:
            with open(filename, "r") as f:
                for line in f:
                    massar = line.strip().upper()
                    if massar:
                        whitelist[massar] = filiere
        except FileNotFoundError:
            print(f"{red}[-] warning: {filename} not found.{reset}")
    return whitelist


def fetch_and_group_grades(whitelist):
    print(
        f"{cyan}[*] connecting to database and fetching raw temporal grades...{reset}"
    )
    try:
        db_conn = mysql.connector.connect(**db_config)
        cursor = db_conn.cursor(dictionary=True)
        query = """
            SELECT massar, full_name, module_name, moyenne, is_rattrapage
            FROM notes
            WHERE moyenne IS NOT NULL
            ORDER BY massar, module_name, is_rattrapage DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"{red}[-] db error: {err}{reset}")
        sys.exit(1)
    finally:
        if "db_conn" in locals() and db_conn.is_connected():
            cursor.close()
            db_conn.close()

    student_data = {}
    for row in results:
        if row["moyenne"] is None:
            continue
        massar = row["massar"].strip().upper()
        if massar not in whitelist:
            continue

        student_filiere = whitelist[massar]
        raw_module = normalize_string(row["module_name"])
        grade = float(row["moyenne"])

        if raw_module not in MODULE_MAP:
            continue
        semester = MODULE_MAP[raw_module]

        if massar not in student_data:
            student_data[massar] = {
                "full_name": str(row.get("full_name", "N/A")).strip().title(),
                "filiere": student_filiere,
                "S3": {},
                "S4": {},
            }

        if raw_module not in student_data[massar][semester]:
            student_data[massar][semester][raw_module] = grade
    return student_data


def calculate_and_save(student_data):
    print(f"{cyan}[*] crunching final averages (strict division by 7)...{reset}")
    final_results = []
    for massar, data in student_data.items():
        s3_avg = sum(data["S3"].values()) / 7.0
        s4_avg = sum(data["S4"].values()) / 7.0
        global_avg = (s3_avg + s4_avg) / 2.0

        final_results.append(
            {
                "massar": massar,
                "full_name": data["full_name"],
                "filiere": data["filiere"],
                "s3_avg": round(s3_avg, 3),
                "s4_avg": round(s4_avg, 3),
                "global_avg": round(global_avg, 3),
            }
        )

    print(f"{cyan}[*] forging '2y_avg' table in MariaDB...{reset}")
    try:
        db_conn = mysql.connector.connect(**db_config)
        cursor = db_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `2y_avg` (
                massar VARCHAR(20) PRIMARY KEY,
                full_name VARCHAR(100),
                filiere VARCHAR(10),
                s3_avg FLOAT,
                s4_avg FLOAT,
                global_avg FLOAT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        insert_query = """
            INSERT INTO `2y_avg` (massar, full_name, filiere, s3_avg, s4_avg, global_avg)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            full_name = VALUES(full_name), filiere = VALUES(filiere), 
            s3_avg = VALUES(s3_avg), s4_avg = VALUES(s4_avg), global_avg = VALUES(global_avg)
        """
        db_data = [
            (
                r["massar"],
                r["full_name"],
                r["filiere"],
                r["s3_avg"],
                r["s4_avg"],
                r["global_avg"],
            )
            for r in final_results
        ]
        cursor.executemany(insert_query, db_data)
        db_conn.commit()
        print(
            f"{green}[+] successfully locked {len(final_results)} student records into `2y_avg`.{reset}"
        )
    except mysql.connector.Error as err:
        print(f"{red}[-] db error during injection: {err}{reset}")
    finally:
        if "db_conn" in locals() and db_conn.is_connected():
            cursor.close()
            db_conn.close()
    return final_results


def print_leaderboards(results):
    if not results:
        return
    results.sort(key=lambda x: x["global_avg"], reverse=True)
    print(f"\n{purple}{bold}[*] === FSTM YEAR 2 GLOBAL TOP 10 ==={reset}")
    top_10 = [
        [
            r["massar"],
            r["full_name"],
            r["filiere"],
            r["s3_avg"],
            r["s4_avg"],
            r["global_avg"],
        ]
        for r in results[:10]
    ]
    print(
        tabulate(
            top_10,
            headers=[
                "Massar",
                "Nom Complet",
                "Filière",
                "S3 Avg",
                "S4 Avg",
                "Global Avg",
            ],
            tablefmt="fancy_grid",
        )
    )

    for f in ["GI", "GE", "GP", "MSD"]:
        f_students = [r for r in results if r["filiere"] == f]
        if f_students:
            print(f"\n{cyan}[*] --- TOP 10: {f} ---{reset}")
            top_3 = [
                [r["massar"], r["full_name"], r["s3_avg"], r["s4_avg"], r["global_avg"]]
                for r in f_students[:10]
            ]
            print(
                tabulate(
                    top_3,
                    headers=["Massar", "Nom Complet", "S3 Avg", "S4 Avg", "Global Avg"],
                    tablefmt="simple",
                )
            )


def main():
    clear_screen()
    print(f"{purple}{bold}[*] === FSTM AVERAGE CALCULATOR ENGINE ==={reset}\n")
    whitelist = load_whitelists()
    if not whitelist:
        sys.exit(1)
    student_data = fetch_and_group_grades(whitelist)
    if not student_data:
        sys.exit(1)
    final_results = calculate_and_save(student_data)
    print_leaderboards(final_results)


if __name__ == "__main__":
    main()

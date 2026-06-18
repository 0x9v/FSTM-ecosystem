import argparse
import json
import os

db_file = "custom_commands.json"

def load_db():
    if not os.path.exists(db_file): 
        return {}
    with open(db_file, "r", encoding="utf-8") as f: 
        return json.load(f)

def save_db(data):
    with open(db_file, "w", encoding="utf-8") as f: 
        json.dump(data, f, indent=4, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="oracle cli - explicit flag edition")
    subparsers = parser.add_subparsers(dest="action", required=True)

    add_parser = subparsers.add_parser("add", help="add a new command or append to a pool")
    add_parser.add_argument("trigger", type=str, help="the trigger word (e.g., !ratt)")
    add_parser.add_argument("payload", type=str, help="the text reply or the filename")
    add_parser.add_argument("--tag", type=str, help="whatsapp tag (e.g., sticker, audio, video, file)", default=None)
    add_parser.add_argument("--folder", type=str, help="storage folder (e.g., img, audio, video, pdf)", default=None)

    rm_parser = subparsers.add_parser("rm", help="remove a command completely")
    rm_parser.add_argument("trigger", type=str, help="the trigger word to remove")

    subparsers.add_parser("list", help="list all commands")

    args = parser.parse_args()
    db = load_db()

    if args.action == "add":
        triggers = [t.strip().lower() for t in args.trigger.split(",")]
        
        # note: i fixed a logic bug here from your original script where providing both caused an error
        if args.tag and args.folder:
            new_payload = f"[{args.tag.upper()}]{args.folder.upper()}/{args.payload}"
        elif args.tag or args.folder:
            print("[-] error: if using media, you must provide both --tag and --folder.")
            return
        else:
            new_payload = args.payload.lower()

        for cmd in triggers:
            if cmd in db:
                if isinstance(db[cmd], list):
                    if new_payload not in db[cmd]:
                        db[cmd].append(new_payload)
                        print(f"[+] added to existing pool! '{cmd}' now has {len(db[cmd])} variations.")
                    else:
                        print(f"[*] this exact payload is already in the '{cmd}' pool.")
                elif db[cmd] != new_payload:
                    db[cmd] = [db[cmd], new_payload]
                    print(f"[+] converted '{cmd}' into a roulette pool! it now has 2 variations.")
                else:
                    print(f"[*] this exact payload is already locked to '{cmd}'.")
            else:
                db[cmd] = new_payload
                print(f"[+] alias '{cmd}' locked in.")
        
        save_db(db)

    elif args.action == "rm":
        cmd = args.trigger.lower().strip()
        if cmd in db:
            del db[cmd]
            save_db(db)
            print(f"[+] command '{cmd}' and all its variations wiped.")
        else:
            print("[-] command not found.")

    elif args.action == "list":
        print("\n[*] custom commands:")
        for c, r in db.items():
            if isinstance(r, list):
                print(f" [*] {c} : [pool of {len(r)} items]")
            else:
                print(f" [*] {c} : {r}")
        print()

if __name__ == "__main__":
    main()

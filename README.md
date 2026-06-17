# FSTM academic automation ecosystem

a monorepo combining a whatsapp notification bot and a student data analytics pipeline built for the faculte des sciences et techniques (FSTM).

## system architecture
this repository is divided into two independant components:
```text
FSTM-ecosystem/
│
├── fstm_bot/                 # [Notification Bot] Node.js & Python
│   ├── src/                  # Core routing and event handlers
│   ├── watchdog.py           # Web scraper for real-time exam results
│   ├── server.js             # WhatsApp Web client implementation
│   ├── cli.py                # CLI tool for managing NoSQL database records
│   ├── boot.sh               # PM2 startup script
│   └── ram.sh                # RAM usage monitor
│
└── fstm_analytics/           # [Data Analytics] Python & MariaDB
    ├── 1_student_scraper.py  # Portal scraper and MariaDB database updater
    ├── 2_data_exporter.py    # Extracts and formats filtered student datasets
    └── 3_stat_analyzer.py    # Generates statistical charts and PDF reports
```
## engine 1: FSTM notification bot (`fstm_bot/`)
a whatsapp bot built with `whatsapp-web.js` and managed via pm2, serving as an automated dispatcher and command interface.

* **realtime scraper:** a python scrirpt (`watchdog.py`) checks the university portal every 45 seconds. when a new exam result is detected, it triggers aa local node.js API to broadcast an alert to the whatsapp groups.
* **dynamic command management:** a local python CLI (`cli.py`) manages a JSON file containing bot commands, allowing triggers and media to be updated without restarting the node server.
* **memory optimization:** the headless chromium instance is configured with srict performance flags (e.g., `--disable-gpu`) and a 512MB V8 memory limit to run efficiently on low resource linux environments.

## engine 2: data analytics (`fstm_analytics/`)
a python pipeline designed to extract student data from the university portal and generate academic statistics.
* **data extraction & database sync:** `1_student_scraper.py` parses the portal HTML, formats the grading data, and syncs the records with a local mariadb instance.
* **statistical analytics:** `3_stat_analyzer.py` utilizes numpy aand matplotlib to calculaate class medians, standard deviations and failure rates, exporting the results as terminal tables, images, or PDF reports.

## technology stack
* **runtime:** node.js, python 3.10+
* **database:** mariadb (analytics), local JSON (bot state)
* **web scraping:** beautifulsoup4, requests
* **automation bridge:** puppeteer / whatsapp-web.js
* **analytics & reporting:** numpy, matplotlib, weasyprint, tabulate
* **process management:** pm2 daemon

#!/bin/bash

echo -e "\n========================================"
echo -e "[*] fstm oracle - automated bootloader"
echo -e "========================================\n"

echo "[*] 1. suspending pm2 daemon..."
pm2 stop fstm-oracle

echo "[*] 2. purging zombie chromium/puppeteer processes..."
pkill -f chromium
pkill -f puppeteer

echo "[*] 3. wiping corrupted session locks..."
find . -type f -name "SingletonLock" -delete
find . -type f -name "SingletonCookie" -delete

echo "[+] system sanitized. re-igniting engine..."
pm2 start fstm-oracle

echo "[+] boot sequence complete. tapping into live logs..."
sleep 2
pm2 logs fstm-oracle

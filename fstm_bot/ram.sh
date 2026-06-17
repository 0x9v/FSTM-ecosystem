#!/bin/bash

echo -e "\n========================================"
echo -e "[*] oracle memory scanner"
echo -e "========================================\n"

chromium_ram=$(ps aux | grep "[c]hromium" | awk '{sum+=$6} END {if(sum) print int(sum/1024); else print 0}')
echo "[*] chromium (whatsapp) : ${chromium_ram} mb"

node_ram=$(ps aux | grep "[n]ode" | awk '{sum+=$6} END {if(sum) print int(sum/1024); else print 0}')
echo "[*] node.js (bot engine) : ${node_ram} mb"

echo "--------------------------------------"

free -h | awk 'NR==2{print "[*] total system ram: " $3 " used out of " $2}'

echo "========================================"
echo ""

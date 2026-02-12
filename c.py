#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PROXY CHECKER - SCAN FILE proxy.txt
# WindyGPT - HTTPBIN 1x + DSTATBOT 2x = 3x Validasi
# Input: proxy.txt | Output: proxy_live.txt

import requests
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import signal
import sys
import os

# ============== KONFIGURASI ==============
THREADS = 100
TIMEOUT = 5
INPUT_FILE = "proxy.txt"
OUTPUT_TXT = "proxy_live.txt"
OUTPUT_JSON = "proxy_live.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ============== ENDPOINT ==============
ENDPOINTS = {
    "httpbin": {
        "url": "http://httpbin.org/ip",
        "name": "HTTPBIN",
        "timeout": 5,
        "retry": 1
    },
    "dstatbot": {
        "url": "https://c3.dstatbot.win",
        "name": "DSTATBOT",
        "timeout": 5,
        "retry": 2
    }
}

# ============== GLOBAL ==============
valid_proxies = []
valid_lock = threading.Lock()
save_lock = threading.Lock()
stop_flag = False
checked_count = 0
total_proxies = 0

# ============== CTRL+C HANDLER ==============
def signal_handler(sig, frame):
    global stop_flag
    print("\n\n[!] CTRL+C DETECTED! MENYIMPAN DATA...")
    stop_flag = True
    save_results()
    print(f"[✓] {len(valid_proxies)} PROXY TERSIMPAN DI {OUTPUT_TXT}")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ============== SAVE RESULTS ==============
def save_results():
    with save_lock:
        with open(OUTPUT_TXT, 'w') as f:
            for p in valid_proxies:
                f.write(f"{p['proxy']}\n")
        
        with open(OUTPUT_JSON, 'w') as f:
            json.dump(valid_proxies, f, indent=2)

# ============== VALIDASI 3 LANGKAH ==============
def validate_proxy(proxy):
    """VALIDASI DARI FILE:
       1. HTTPBIN 1x
       2. DSTATBOT 2x berturut-turut
    """
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }
    
    # ===== 1. HTTPBIN 1x =====
    try:
        start = time.time()
        r1 = requests.get(
            ENDPOINTS["httpbin"]["url"],
            proxies=proxies,
            timeout=ENDPOINTS["httpbin"]["timeout"],
            headers=HEADERS
        )
        if r1.status_code != 200:
            return None
        httpbin_ms = int((time.time() - start) * 1000)
    except:
        return None
    
    # ===== 2. DSTATBOT - Percobaan 1 =====
    try:
        start = time.time()
        r2 = requests.get(
            ENDPOINTS["dstatbot"]["url"],
            proxies=proxies,
            timeout=ENDPOINTS["dstatbot"]["timeout"],
            headers=HEADERS,
            allow_redirects=False
        )
        if r2.status_code != 200:
            return None
        dstatbot1_ms = int((time.time() - start) * 1000)
    except:
        return None
    
    # Delay kecil antar percobaan
    time.sleep(0.2)
    
    # ===== 3. DSTATBOT - Percobaan 2 =====
    try:
        start = time.time()
        r3 = requests.get(
            ENDPOINTS["dstatbot"]["url"],
            proxies=proxies,
            timeout=ENDPOINTS["dstatbot"]["timeout"],
            headers=HEADERS,
            allow_redirects=False
        )
        if r3.status_code != 200:
            return None
        dstatbot2_ms = int((time.time() - start) * 1000)
    except:
        return None
    
    # LOLOS SEMUA!
    return {
        "proxy": proxy,
        "httpbin_ms": httpbin_ms,
        "dstatbot1_ms": dstatbot1_ms,
        "dstatbot2_ms": dstatbot2_ms,
        "avg_dstatbot": (dstatbot1_ms + dstatbot2_ms) // 2,
        "avg_total": (httpbin_ms + dstatbot1_ms + dstatbot2_ms) // 3,
        "timestamp": datetime.now().isoformat()
    }

# ============== WORKER ==============
def worker(proxy):
    global checked_count, valid_proxies, stop_flag, total_proxies
    
    if stop_flag:
        return
    
    result = validate_proxy(proxy)
    
    with valid_lock:
        checked_count += 1
        
        if result:
            valid_proxies.append(result)
            
            print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  ✅ PROXY LOLOS 3X VALIDASI!                                    ║
║     Proxy      : {result['proxy']:<35} ║
║     HTTPBIN    : {result['httpbin_ms']:>4}ms (1/1)             ║
║     DSTATBOT   : {result['dstatbot1_ms']:>4}ms + {result['dstatbot2_ms']:>4}ms (2/2) ║
║     Rata Total : {result['avg_total']:>4}ms                    ║
║     Progress   : {checked_count}/{total_proxies} | {len(valid_proxies)} lolos ║
╚══════════════════════════════════════════════════════════════════╝""")
            
            # SAVE REAL TIME - SETIAP 5 PROXY LOLOS
            if len(valid_proxies) % 5 == 0:
                save_results()
        else:
            if checked_count % 100 == 0:
                print(f"  ⏳ [{checked_count}/{total_proxies}] | {len(valid_proxies)} lolos")

# ============== MAIN ==============
def main():
    global total_proxies
    
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║     PROXY CHECKER - SCAN FILE proxy.txt                             ║
║     📂 INPUT: proxy.txt (IP:PORT per baris)                        ║
║     📡 HTTPBIN 1x + DSTATBOT 2x = 3x VALIDASI                      ║
║     💾 OUTPUT: proxy_live.txt (hanya yang lolos)                   ║
║     ⚡ REAL TIME SAVE - SETIAP 5 PROXY LOLOS                       ║
║     Powered by WindyGPT & Dstatbot                                 ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Cek file proxy.txt
    if not os.path.exists(INPUT_FILE):
        print(f"\n❌ ERROR: File {INPUT_FILE} tidak ditemukan!")
        print(f"📌 Buat file {INPUT_FILE} berisi daftar proxy (IP:PORT per baris)")
        print(f"📌 Contoh:")
        print(f"   192.168.1.1:8080")
        print(f"   10.0.0.1:3128")
        print(f"   172.16.0.1:80")
        return
    
    # Baca proxy dari file
    try:
        with open(INPUT_FILE, 'r') as f:
            proxies = [line.strip() for line in f if line.strip() and ':' in line]
    except Exception as e:
        print(f"\n❌ ERROR: Gagal membaca {INPUT_FILE} - {e}")
        return
    
    total_proxies = len(proxies)
    
    if total_proxies == 0:
        print(f"\n❌ ERROR: File {INPUT_FILE} kosong atau tidak ada format IP:PORT")
        return
    
    print(f"\n📂 File: {INPUT_FILE}")
    print(f"📊 Total proxy: {total_proxies:,}")
    print(f"\n[*] Testing endpoints...")
    
    # Test Endpoints
    endpoints_ok = 0
    for name, ep in ENDPOINTS.items():
        try:
            r = requests.get(ep["url"], timeout=3)
            if r.status_code == 200:
                print(f"  ✅ {ep['name']} ONLINE")
                endpoints_ok += 1
            else:
                print(f"  ⚠️  {ep['name']} response {r.status_code}")
        except:
            print(f"  ❌ {ep['name']} OFFLINE")
    
    if endpoints_ok < 2:
        print(f"\n⚠️  PERINGATAN: Hanya {endpoints_ok}/2 endpoint yang online")
        print(f"   Hasil validasi mungkin tidak akurat\n")
    else:
        print(f"\n✅ SEMUA ENDPOINT ONLINE - Siap validasi\n")
    
    print(f"[*] SKEMA VALIDASI: HTTPBIN 1x + DSTATBOT 2x = 3x CEK")
    print(f"[*] HANYA PROXY YANG LOLOS 3x AKAN DISIMPAN\n")
    print(f"[*] MEMULAI VALIDASI {total_proxies:,} PROXY...\n")
    
    # Reset file output
    open(OUTPUT_TXT, 'w').close()
    open(OUTPUT_JSON, 'w').close()
    
    start_time = time.time()
    
    # Validasi dengan multithreading
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(worker, proxies)
    
    # SAVE FINAL
    save_results()
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"📊 HASIL VALIDASI 3X (HTTPBIN 1x + DSTATBOT 2x)")
    print(f"{'='*80}")
    print(f"""
    File input           : {INPUT_FILE}
    Total proxy di file  : {total_proxies:,}
    Total divalidasi     : {checked_count:,}
    TOTAL PROXY LOLOS 3X : {len(valid_proxies):,}
    
    Persentase kelolosan : {(len(valid_proxies)/checked_count*100):.2f}%
    Rata-rata HTTPBIN    : {sum(p['httpbin_ms'] for p in valid_proxies)/len(valid_proxies):.0f}ms
    Rata-rata DSTATBOT   : {sum(p['avg_dstatbot'] for p in valid_proxies)/len(valid_proxies):.0f}ms
    Rata-rata total      : {sum(p['avg_total'] for p in valid_proxies)/len(valid_proxies):.0f}ms
    Waktu validasi       : {elapsed:.1f} detik
    Kecepatan            : {checked_count/elapsed:.1f} proxy/detik
    
    Top 5 Proxy Tercepat:
    """)
    
    if valid_proxies:
        sorted_proxies = sorted(valid_proxies, key=lambda x: x['avg_total'])[:5]
        for i, p in enumerate(sorted_proxies, 1):
            print(f"      {i}. {p['proxy']} - HTTPBIN:{p['httpbin_ms']}ms | DSTATBOT:{p['avg_dstatbot']}ms")
    
    print(f"""
    File output:
      📁 {OUTPUT_TXT} - {len(valid_proxies):,} proxy (IP:PORT)
      📁 {OUTPUT_JSON} - {len(valid_proxies):,} proxy (detail)
    """)
    print(f"{'='*80}")
    print(f"\n[✓] SELESAI! {len(valid_proxies)} PROXY LOLOS 3X VALIDASI")
    print(f"[✓] Hasil tersimpan di {OUTPUT_TXT}")

if __name__ == "__main__":
    main()

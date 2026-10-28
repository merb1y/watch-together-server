import os
import sys
import time
import subprocess
import threading
import re

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_uvicorn():
    os.system(f'"{sys.executable}" -m uvicorn main:app --host 0.0.0.0 --port 8000')

# Uvicorn'u arka planda başlat
t = threading.Thread(target=run_uvicorn, daemon=True)
t.start()
time.sleep(1.5)

print("\n" + "=" * 55)
print("🚀 WatchTogether Güvenli İnternet Tüneli Açılıyor...")
print("=" * 55)

# SSH localhost.run ile güvenli SSL tüneli aç
ssh_cmd = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=NUL",
    "-T",
    "-R", "80:127.0.0.1:8000",
    "nokey@localhost.run"
]

try:
    proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    tunnel_url = None
    for line in proc.stdout:
        match = re.search(r'(https://[a-zA-Z0-9-]+\.lhr\.life)', line)
        if match:
            tunnel_url = match.group(1).replace("https://", "")
            print("\n" + "🌟" * 28)
            print("🎉 SUNUCUNUZ HEM SİZİN HEM ARKADAŞLARINIZ İÇİN HAZIR!")
            print("=" * 55)
            print(f"👉 EKLENTİDEKİ 'Sunucu Adresi' KISMINA ŞUNU YAZIN:\n")
            print(f"   {tunnel_url}")
            print("\n" + "=" * 55)
            print("(Arkadaşlarınız da evlerinden bu adresi yazarak bağlanabilir!)")
            print("🌟" * 28 + "\n")
            break
    proc.wait()
except KeyboardInterrupt:
    print("\nSunucu kapatılıyor...")
except Exception as e:
    print("Tünel hatası:", e)
    print("Yerel modda devam ediliyor: 127.0.0.1:8000")
    while True:
        time.sleep(1)

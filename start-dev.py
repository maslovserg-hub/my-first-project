import subprocess
import threading
import sys
import os
import re
import time
import webbrowser
import tempfile
import io

# Принудительно UTF-8 для stdout (Windows CP1252 не тянет кириллицу)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8000

# ── 1. Убить старый процесс на PORT, если есть ──
def kill_port(port):
    try:
        result = subprocess.run(
            f'netstat -ano | findstr ":{port} "',
            shell=True, capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts:
                pid = parts[-1]
                subprocess.run(f'taskkill /PID {pid} /F', shell=True,
                               capture_output=True)
    except Exception:
        pass

kill_port(PORT)
time.sleep(1)

# ── 2. Запустить Python HTTP-сервер ──
server = subprocess.Popen(
    [sys.executable, '-m', 'http.server', str(PORT)],
    cwd=BASE_DIR,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
print(f'[OK] HTTP-сервер запущен на порту {PORT}')
time.sleep(1)

# ── 3. Запустить SSH-туннель, поймать URL ──
print('[..] Подключаемся к туннелю, подождите...')

tunnel_url = None
tunnel_proc = subprocess.Popen(
    [
        'ssh', '-o', 'StrictHostKeyChecking=no',
        '-o', 'ServerAliveInterval=30',
        '-R', f'80:localhost:{PORT}',
        'nokey@localhost.run'
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

def read_tunnel(proc, result):
    for line in proc.stdout:
        line = line.strip()
        m = re.search(r'https://[a-z0-9]+\.lhr\.life', line)
        if m:
            result['url'] = m.group(0)
            print(f'[OK] Туннель: {result["url"]}')

result = {}
t = threading.Thread(target=read_tunnel, args=(tunnel_proc, result), daemon=True)
t.start()
t.join(timeout=20)

if not result.get('url'):
    print('[ERR] Не удалось получить URL туннеля.')
    server.terminate()
    sys.exit(1)

tunnel_url = result['url']
index_url  = tunnel_url + '/index.html'

# ── 4. Создать HTML со страницей с QR-кодом и открыть в браузере ──
qr_api = (
    'https://api.qrserver.com/v1/create-qr-code/'
    f'?size=400x400&ecc=M&margin=1&data={index_url}'
)

html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Сканируй и открывай</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0a0a14;
    color: #e2e8f0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
  }}
  .card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(124,58,237,0.35);
    border-radius: 24px;
    padding: 40px 36px;
    text-align: center;
    max-width: 400px;
    width: 100%;
    box-shadow: 0 0 60px rgba(124,58,237,0.15);
  }}
  h1 {{ font-size: 1.4rem; font-weight: 700; margin-bottom: 8px; }}
  .sub {{ font-size: 14px; color: #64748b; margin-bottom: 28px; line-height: 1.6; }}
  .sub strong {{ color: #a78bfa; }}
  .qr-wrap {{
    background: #fff;
    border-radius: 14px;
    padding: 12px;
    display: inline-flex;
    margin-bottom: 24px;
    box-shadow: 0 0 40px rgba(124,58,237,0.2);
  }}
  .qr-wrap img {{ display: block; width: 280px; height: 280px; border-radius: 6px; }}
  .url-box {{
    font-size: 12px;
    color: #475569;
    word-break: break-all;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 10px 14px;
  }}
</style>
</head>
<body>
<div class="card">
  <h1>Наведите камеру</h1>
  <p class="sub">Откроется страница со всеми QR-кодами проекта.<br>
  Туннель активен: <strong>{tunnel_url}</strong></p>
  <div class="qr-wrap">
    <img src="{qr_api}" alt="QR">
  </div>
  <div class="url-box">{index_url}</div>
</div>
</body>
</html>"""

tmp = tempfile.NamedTemporaryFile(
    mode='w', suffix='.html', delete=False, encoding='utf-8'
)
tmp.write(html)
tmp.close()

webbrowser.open(f'file:///{tmp.name.replace(os.sep, "/")}')
print('[OK] QR-код открыт в браузере.')
print('     Закройте это окно, чтобы остановить сервер и туннель.')

# ── 5. Ждём, пока туннель живёт ──
try:
    tunnel_proc.wait()
except KeyboardInterrupt:
    pass
finally:
    print('\n[..] Останавливаем...')
    tunnel_proc.terminate()
    server.terminate()
    try:
        os.unlink(tmp.name)
    except Exception:
        pass
    print('[OK] Готово.')

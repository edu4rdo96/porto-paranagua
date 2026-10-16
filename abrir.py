"""Sobe o painel (se ainda não estiver no ar) e abre no Brave.

Chamado pelo atalho "Porto de Paranaguá" da área de trabalho.
"""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PASTA = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:4180/'
BRAVE = r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe'


def no_ar() -> bool:
    try:
        with urllib.request.urlopen(URL, timeout=2):
            return True
    except OSError:
        return False


if not no_ar():
    # O servidor continua rodando depois que este script termina.
    subprocess.Popen([sys.executable, str(PASTA / 'server.py')], cwd=PASTA,
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if no_ar():
            break
        time.sleep(0.5)

subprocess.Popen([BRAVE, URL])

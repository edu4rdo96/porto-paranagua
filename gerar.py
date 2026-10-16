"""Gera a versão estática do painel para publicar no GitHub Pages.

Lê a APPA e o clima, compara com o data.json já publicado (para "O que mudou")
e escreve site/index.html + site/data.json. Roda no GitHub Actions a cada ~20 min.

    python gerar.py [URL_DO_DATA_JSON_PUBLICADO]
"""
from __future__ import annotations

import json
import shutil
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import appa
import clima

PASTA = Path(__file__).resolve().parent
SAIDA = PASTA / 'site'


def publicado(url: str | None) -> dict | None:
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=30) as resposta:
            return json.load(resposta)
    except Exception:
        return None


def main() -> int:
    anterior = publicado(sys.argv[1] if len(sys.argv) > 1 else None)
    situacoes = appa.interpretar(appa.baixar_html(timeout=90))
    if not situacoes:
        print('a página da APPA veio sem tabelas', file=sys.stderr)
        return 1
    try:
        tempo = clima.chuva_paranagua()
    except Exception:
        tempo = None
    # "O que mudou" compara com a última publicação que trouxe dados diferentes.
    if anterior and anterior.get('situacoes') == situacoes:
        base, desde = anterior.get('base'), anterior.get('desde')
    elif anterior:
        base, desde = anterior.get('situacoes'), anterior.get('atualizado')
    else:
        base, desde = None, None
    dados = {
        'atualizado': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'situacoes': situacoes,
        'mudancas': appa.mudancas(base, situacoes),
        'desde': desde,
        'base': base,
        'erro': None,
        'clima': tempo,
        'fonte': appa.URL_LINEUP,
    }
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / 'data.json').write_text(json.dumps(dados, ensure_ascii=False), encoding='utf-8')
    shutil.copy(PASTA / 'web' / 'index.html', SAIDA / 'index.html')
    print(f"ok: {sum(len(v) for v in situacoes.values())} navios, {len(dados['mudancas'])} mudanças")
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Painel local do line-up do Porto de Paranaguá.

Serve a página em http://127.0.0.1:4180 e o JSON em /api/lineup. Lê a APPA no
máximo a cada 15 minutos; a leitura anterior fica guardada para mostrar o que mudou.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import appa
import clima

PASTA = Path(__file__).resolve().parent
DADOS = PASTA / 'dados'
PORTA = 4180
INTERVALO = 15 * 60  # segundos entre leituras da APPA

_trava = threading.Lock()
_estado: dict = {'lido_em': 0.0}


def _ler_json(caminho: Path):
    try:
        return json.loads(caminho.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def lineup(forcar: bool = False) -> dict:
    with _trava:
        if not forcar and time.time() - _estado['lido_em'] < INTERVALO and 'situacoes' in _estado:
            return _estado
        DADOS.mkdir(exist_ok=True)
        try:
            _estado['clima'] = clima.chuva_paranagua()
        except Exception:  # sem clima o painel continua funcionando
            _estado['clima'] = None
        ultimo = _ler_json(DADOS / 'ultimo.json')
        try:
            situacoes = appa.interpretar(appa.baixar_html())
            if not situacoes:
                raise ValueError('a página da APPA veio sem tabelas')
        except Exception as erro:  # rede fora ou layout mudou: mantém o último dado bom
            _estado.update(erro=f'{type(erro).__name__}: {erro}', lido_em=time.time())
            if 'situacoes' not in _estado and ultimo:
                _estado.update(situacoes=ultimo['situacoes'], atualizado=ultimo['atualizado'], mudancas=[])
            return _estado
        agora = datetime.now().strftime('%d/%m/%Y %H:%M')
        if ultimo and ultimo['situacoes'] != situacoes:
            (DADOS / 'anterior.json').write_text(json.dumps(ultimo, ensure_ascii=False), encoding='utf-8')
        anterior = _ler_json(DADOS / 'anterior.json')
        (DADOS / 'ultimo.json').write_text(json.dumps({'atualizado': agora, 'situacoes': situacoes}, ensure_ascii=False), encoding='utf-8')
        _estado.update(situacoes=situacoes, atualizado=agora, erro=None, lido_em=time.time(),
                       mudancas=appa.mudancas(anterior['situacoes'] if anterior else None, situacoes),
                       desde=anterior['atualizado'] if anterior else None)
        return _estado


class Pedido(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PASTA / 'web'), **kwargs)

    def do_GET(self):
        if self.path.startswith('/api/lineup'):
            estado = lineup(forcar='forcar=1' in self.path)
            corpo = json.dumps({k: estado.get(k) for k in ('atualizado', 'situacoes', 'mudancas', 'desde', 'erro', 'clima')}
                               | {'fonte': appa.URL_LINEUP}, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(corpo)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    servidor = ThreadingHTTPServer(('127.0.0.1', PORTA), Pedido)
    print(f'Painel do Porto de Paranaguá em http://127.0.0.1:{PORTA}', file=sys.stderr)
    servidor.serve_forever()

"""Leitura e interpretação do line-up público da APPA (Portos do Paraná).

A página da APPA traz uma tabela por situação (ATRACADOS, PROGRAMADOS, AO LARGO,
ESPERADOS, DESPACHADOS...). Cada tabela tem uma linha de título, uma linha de
cabeçalho e as linhas de navios. Navio com mais de uma mercadoria aparece em
linhas extras, mais curtas, que repetem só as colunas finais.
"""
from __future__ import annotations

import re
import unicodedata
import urllib.request
from html.parser import HTMLParser

URL_LINEUP = 'https://www.appaweb.appa.pr.gov.br/appaweb/pesquisa.aspx?WCI=relLineUpRetroativo'

# Códigos de bordo da legenda da APPA (BB bombordo, BE boreste, QB qualquer bordo).
BORDOS = {'BB', 'BE', 'QB'}

# Grupos de produto para o filtro. O primeiro grupo cuja palavra-chave casar vence,
# por isso "óleo de milho" e "farelo de soja" vêm antes de milho e soja.
GRUPOS = [
    ('Óleos e álcool', ['OLEO', 'ALCOOL', 'ETANOL', 'METANOL', 'BIODIESEL']),
    ('Farelo', ['FARELO']),
    ('Soja', ['SOJA']),
    ('Milho', ['MILHO']),
    ('Trigo / outros grãos', ['TRIGO', 'CEVADA', 'MALTE', 'SORGO', 'ARROZ']),
    ('Açúcar', ['ACUCAR']),
    ('Fertilizantes', ['UREIA', 'FERTILIZ', 'POTASSIO', 'KCL', 'NITRATO', 'SULFATO', 'FOSFAT', 'NPK', 'ENXOFRE', 'AMONIA', r'\bMAP\b', r'\bDAP\b']),
    ('Contêineres', ['CONTEINER', 'CONTENTOR']),
    ('Veículos', ['VEICULO', 'AUTOMOVE']),
    ('Celulose / madeira', ['CELULOSE', 'MADEIRA', 'PAPEL']),
    ('Combustíveis', ['DIESEL', 'GASOLINA', 'GLP', 'COMBUST', 'NAFTA', 'BUNKER', 'PETROLEO']),
    ('Carnes / congelados', ['CARNE', 'FRANGO', 'CONGELAD', 'FRIGORIF']),
    ('Passageiros', ['PASSAGEIRO']),
]


def sem_acento(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()


def grupo_do_produto(mercadoria: str) -> str:
    alvo = sem_acento(mercadoria or '')
    for nome, chaves in GRUPOS:
        if any(re.search(chave, alvo) for chave in chaves):
            return nome
    return 'Outros' if mercadoria else 'Sem carga'


def numero_br(texto: str) -> float | None:
    """'45.000,000 Tons.' -> 45000.0 ; '600 Movs.' -> 600.0"""
    achado = re.search(r'-?\d[\d.]*(?:,\d+)?', texto or '')
    if not achado:
        return None
    return float(achado.group().replace('.', '').replace(',', '.'))


class _Tabelas(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tabelas: list[list[list[str]]] = []
        self._linha: list[str] | None = None
        self._celula: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.tabelas.append([])
        elif tag == 'tr' and self.tabelas:
            self._linha = []
        elif tag in ('td', 'th') and self._linha is not None:
            self._celula = ''

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._celula is not None:
            self._linha.append(re.sub(r'\s+', ' ', self._celula).strip())
            self._celula = None
        elif tag == 'tr' and self._linha is not None:
            if any(self._linha):
                self.tabelas[-1].append(self._linha)
            self._linha = None

    def handle_data(self, data):
        if self._celula is not None:
            self._celula += data


def baixar_html(timeout: int = 30) -> str:
    pedido = urllib.request.Request(URL_LINEUP, headers={'User-Agent': 'Mozilla/5.0 (painel-porto-paranagua)'})
    with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
        return resposta.read().decode('utf-8', errors='replace')


def _carga(campos: dict[str, str]) -> dict:
    mercadoria = campos.get('Mercadoria', '')
    previsto = campos.get('Previsto', '')
    return {
        'mercadoria': mercadoria,
        'grupo': grupo_do_produto(mercadoria),
        'sentido': campos.get('Sentido', ''),
        'operador': campos.get('Operador', ''),
        'previsto': numero_br(previsto),
        'realizado': numero_br(campos.get('Realizado', '')),
        'saldo': numero_br(campos.get('Saldo Operador', '')),
        # Só nos atracados: ritmo planejado (t/dia) e o que foi operado nas últimas 24h.
        'prancha': numero_br(campos.get('Prancha (t/dia)', '')),
        'tons_dia': numero_br(campos.get('Tons/Dia', '')),
        'unidade': 'movs' if 'Movs' in previsto else 't',
    }


def interpretar(html: str) -> dict[str, list[dict]]:
    """Devolve {situação: [navio, ...]}, cada navio com uma ou mais cargas."""
    leitor = _Tabelas()
    leitor.feed(html)
    resultado: dict[str, list[dict]] = {}
    for tabela in leitor.tabelas:
        if len(tabela) < 3 or not tabela[0] or tabela[0][0] in ('', 'LEGENDA'):
            continue
        titulo = tabela[0][0].strip()
        cabecalho = tabela[1]
        navios: list[dict] = []
        for linha in tabela[2:]:
            if linha[0].strip().isdigit() and len(linha) >= len(cabecalho) - 2:
                campos = dict(zip(cabecalho, linha))
                navios.append({
                    'programacao': campos.get('Programação', ''),
                    'duv': campos.get('DUV', ''),
                    'berco': campos.get('Berço', ''),
                    'navio': campos.get('Embarcação', ''),
                    'imo': campos.get('IMO', ''),
                    'loa': numero_br(campos.get('LOA', '')),
                    'dwt': numero_br(campos.get('DWT', '')),
                    'agencia': campos.get('Agência', ''),
                    'eta': campos.get('ETA', ''),
                    'chegada': campos.get('Chegada', ''),
                    'atracacao': campos.get('Atracação', '') or campos.get('ETB', ''),
                    'desatracacao': campos.get('Desatracacao', ''),
                    'janela': campos.get('Janela Operacional', ''),
                    'cargas': [_carga(campos)],
                })
            elif navios:
                # Mercadoria extra do navio anterior: a linha começa na coluna "Bordo"
                # (ou "Sentido", nas tabelas sem bordo) e segue a ordem do cabeçalho.
                inicio = cabecalho.index('Bordo') if linha[0] in BORDOS and 'Bordo' in cabecalho else cabecalho.index('Sentido')
                campos = dict(zip(cabecalho[inicio:], linha))
                navios[-1]['cargas'].append(_carga(campos))
        resultado[titulo] = navios
    return resultado


def mudancas(antes: dict[str, list[dict]] | None, agora: dict[str, list[dict]]) -> list[dict]:
    """Navios que entraram no line-up ou mudaram de situação desde a leitura anterior."""
    if not antes:
        return []
    onde_antes = {n['programacao']: s for s, ns in antes.items() for n in ns}
    lista = []
    for situacao, navios in agora.items():
        for navio in navios:
            anterior = onde_antes.get(navio['programacao'])
            if anterior != situacao:
                lista.append({'navio': navio['navio'], 'programacao': navio['programacao'],
                              'de': anterior or 'novo no line-up', 'para': situacao,
                              'mercadoria': ', '.join(c['mercadoria'] for c in navio['cargas'])})
    return lista

"""Chuva em Paranaguá pela Open-Meteo (gratuita, sem chave).

Embarque de granéis para quando chove, então o painel mostra se está chovendo,
quantas horas choveu nas últimas 24h e as horas de chuva previstas nas próximas 24h.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime

URL = ('https://api.open-meteo.com/v1/forecast?latitude=-25.52&longitude=-48.51'
       '&current=precipitation&hourly=precipitation,precipitation_probability'
       '&past_days=1&forecast_days=2&timezone=America%2FSao_Paulo')
LIMIAR_MM = 0.2  # abaixo disso é garoa que não aparece como chuva na prática


def chuva_paranagua(timeout: int = 20) -> dict:
    with urllib.request.urlopen(URL, timeout=timeout) as resposta:
        dados = json.load(resposta)
    horas = dados['hourly']
    agora = datetime.now().replace(minute=0, second=0, microsecond=0)
    passadas, futuras = [], []
    for texto, mm, prob in zip(horas['time'], horas['precipitation'], horas['precipitation_probability']):
        hora = datetime.fromisoformat(texto)
        diferenca = (hora - agora).total_seconds() / 3600
        if -24 <= diferenca < 0:
            passadas.append(mm or 0)
        elif 0 <= diferenca < 24:
            futuras.append({'hora': hora.strftime('%d/%m %Hh'), 'mm': mm or 0, 'prob': prob or 0})
    mm_agora = dados['current'].get('precipitation') or 0
    return {
        'chovendo': mm_agora >= LIMIAR_MM,
        'mm_agora': mm_agora,
        'horas_chuva_24h': sum(1 for mm in passadas if mm >= LIMIAR_MM),
        'mm_24h': round(sum(passadas), 1),
        # Só horas com chuva de fato prevista; probabilidade alta com 0 mm é garoa.
        'previsao': [h for h in futuras if h['mm'] >= LIMIAR_MM],
    }

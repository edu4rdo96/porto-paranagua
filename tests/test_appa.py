import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import appa  # noqa: E402

FIXTURE = Path(__file__).with_name('lineup_2026-10-16.html')


class InterpretarLineup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = appa.interpretar(FIXTURE.read_text(encoding='utf-8', errors='replace'))

    def navio(self, situacao, nome):
        return next(n for n in self.d[situacao] if n['navio'] == nome)

    def test_situacoes(self):
        for s in ['ATRACADOS', 'PROGRAMADOS', 'AO LARGO', 'ESPERADOS', 'DESPACHADOS']:
            self.assertIn(s, self.d)
        self.assertEqual(len(self.d['ATRACADOS']), 15)
        self.assertEqual(len(self.d['AO LARGO']), 44)

    def test_linha_extra_alinha_pelo_bordo(self):
        cargas = self.navio('ATRACADOS', 'GLBS MAGIC')['cargas']
        self.assertEqual([c['mercadoria'] for c in cargas], ['UREIA', 'UREIA'])
        self.assertEqual(cargas[1]['operador'], 'HARBOR')
        self.assertEqual(cargas[1]['previsto'], 5000.0)
        self.assertEqual(cargas[1]['sentido'], 'Imp')

    def test_ritmo_dos_atracados(self):
        c = self.navio('ATRACADOS', 'GLBS MAGIC')['cargas'][0]
        self.assertEqual((c['prancha'], c['tons_dia']), (6292.909, 81.0))

    def test_varias_mercadorias(self):
        cargas = self.navio('PROGRAMADOS', 'SANTIAGO I')['cargas']
        self.assertEqual([c['grupo'] for c in cargas], ['Óleos e álcool', 'Óleos e álcool'])

    def test_campos_do_navio(self):
        n = self.navio('AO LARGO', 'ARISTOS II')
        self.assertEqual(n['imo'], '1066673')
        self.assertEqual(n['cargas'][0]['grupo'], 'Soja')
        self.assertEqual(n['cargas'][0]['previsto'], 72000.0)
        self.assertEqual(n['cargas'][0]['sentido'], 'Exp')

    def test_conteiner_em_movimentos(self):
        c = self.navio('ATRACADOS', 'MAERSK LABREA')['cargas'][0]
        self.assertEqual((c['grupo'], c['unidade'], c['previsto']), ('Contêineres', 'movs', 600.0))


class Grupos(unittest.TestCase):
    def test_grupos(self):
        casos = {'FARELO DE SOJA': 'Farelo', 'SOJA EM GRAOS': 'Soja', 'OLEO DE MILHO': 'Óleos e álcool',
                 'MAP': 'Fertilizantes', 'SORGO DE GRAO, EXCETO PARA SEM': 'Trigo / outros grãos',
                 'AÇÚCAR VHP': 'Açúcar', 'MAPA': 'Outros', '': 'Sem carga'}
        for mercadoria, grupo in casos.items():
            self.assertEqual(appa.grupo_do_produto(mercadoria), grupo, mercadoria)

    def test_numero_br(self):
        self.assertEqual(appa.numero_br('45.000,000 Tons.'), 45000.0)
        self.assertEqual(appa.numero_br('600 Movs.'), 600.0)
        self.assertIsNone(appa.numero_br(''))


class Mudancas(unittest.TestCase):
    def test_detecta_entrada_e_troca_de_situacao(self):
        antes = {'AO LARGO': [{'programacao': '1', 'navio': 'A', 'cargas': []}]}
        agora = {'ATRACADOS': [{'programacao': '1', 'navio': 'A', 'cargas': []}],
                 'ESPERADOS': [{'programacao': '2', 'navio': 'B', 'cargas': []}]}
        m = appa.mudancas(antes, agora)
        self.assertEqual({(x['navio'], x['de'], x['para']) for x in m},
                         {('A', 'AO LARGO', 'ATRACADOS'), ('B', 'novo no line-up', 'ESPERADOS')})
        self.assertEqual(appa.mudancas(None, agora), [])


if __name__ == '__main__':
    unittest.main()

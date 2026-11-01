"""Source-compared, reproducible presentation corrections for the initial booklet.

The read-only native-v1 snapshot is the input. This never reinterprets answers,
changes their order, or rasterizes prose. See the dated review in docs/.
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'data/derived/baselines/enem-2024-dia2-azul-native-v1.json'
TARGET = ROOT / 'data/enem-2024-dia2-azul.json'
VERSION = 'native-v2-2026-10-31'
REASONS = {
    91: 'Título e crédito da figura associados ao diagrama; crédito do texto separado.',
    92: 'Semirreações em LaTeX no rodapé da figura, crédito separado e alternativas químicas em LaTeX; fase líquida l conferida no original.',
    94: 'Carga do próton em LaTeX; legenda Nimesulida e crédito associados à estrutura química.',
    97: 'Massas molares, concentração e unidades em LaTeX; parênteses e ordem do texto preservados.',
    99: 'Índices das frequências e comparações das alternativas em LaTeX.',
    100: 'Índices dos espelhos em LaTeX; título do texto e crédito do esquema separados.',
    114: 'Espécies químicas em LaTeX e crédito associado ao gráfico.',
    116: 'Equação química separada do comando e renderizada em LaTeX, com cargas e estados físicos.',
    118: 'Hidroxiapatita, cargas e equilíbrio em LaTeX químico, preservando os rótulos dos dois sentidos.',
    123: 'Crédito bibliográfico associado às fórmulas estruturais preservadas como figura.',
    128: 'Cargas genéricas m+ e n− e elétron em LaTeX; crédito associado à figura.',
    132: 'Índices das lâmpadas e da tensão V_QR em LaTeX.',
    133: 'Continuidade do parágrafo, grandezas e unidades em LaTeX.',
    135: 'Título separado; alumina, unidades, porcentagem e notação científica em LaTeX.',
    170: 'Índices de magnitudes e energias e valor M_1 em LaTeX no texto, de acordo com a equação.',
}


def paragraph(text, role='body'):
    return {'type': 'paragraph', 'text': text, 'role': role}


def reaction(text):
    # Separate species at actual operators, so narrow screens can wrap without
    # splitting a molecular formula or mistaking an ionic charge for addition.
    left, right = text.split(' -> ')
    return r' \longrightarrow '.join(' + '.join(r'\ce{' + species + '}' for species in side.split(' + ')) for side in [left, right])


def move_figure_credit(content, prefixes, caption='', equations=None):
    selected = [b for b in content['blocks'] if b['type'] == 'paragraph' and any(b['text'].startswith(prefix) for prefix in prefixes)]
    assert len(selected) == len(prefixes), (content['number'], prefixes)
    figure = [b for b in content['blocks'] if b['type'] == 'image'][-1]
    figure.update(caption=caption, credit='\n'.join(b['text'] for b in selected), equations=equations or [])
    content['blocks'] = [b for b in content['blocks'] if b not in selected]
    return figure


def replace_text(content, changes, alternatives=False):
    for block in content['blocks']:
        if block['type'] == 'paragraph':
            for old, new in changes.items(): block['text'] = block['text'].replace(old, new)
    if alternatives:
        for option in content['alternatives']:
            for old, new in changes.items(): option['text'] = option['text'].replace(old, new)


def apply_review(data):
    for question in data['questions']:
        c = question['content']
        n = c['number']
        if n not in REASONS: continue
        # Called on a native-v1 input; prevent accidentally applying a patch twice.
        if c['layout'].get('presentation_version') == VERSION: continue
        before = copy.deepcopy(c)
        for block in c['blocks']:
            if block['type'] == 'paragraph': block['role'] = 'body'
        if n == 91:
            figure = move_figure_credit(c, ['Momentum and Car safety.', 'Disponível em: www.shalom', 'Acesso em: 5 jul.'])
            figure['caption'], figure['credit'] = figure['credit'].split('\n', 1)
            for b in c['blocks']:
                if b['type'] == 'paragraph' and (b['text'].startswith('DAY,') or b['text'].startswith('Acesso em: 2 jul.')): b['role'] = 'credit'
        if n == 92:
            mixed = next(b for b in c['blocks'] if b['type'] == 'paragraph' and b['text'].startswith('CH₃COO'))
            citation = mixed['text'][mixed['text'].index('QUINTO,'):]
            mixed['text'] = citation
            figure = move_figure_credit(c, ['QUINTO,', 'https://jornal.usp.br.'], caption='Célula a combustível microbiana (CCM).', equations=[
                reaction('CH3COO- (aq) + 2 H2O (l) -> 2 CO2 (g) + 7 H+ (aq) + 8 e-'),
                reaction('4 H+ (aq) + O2 (g) + 4 e- -> 2 H2O (l)'),
            ])
            formulas = [
                'CH3COO- (aq) + O2 (g) -> 2 CO2 (g) + 3 H+ (aq)',
                'CO2 (g) + O2 (g) + H+ (aq) -> H2O (l) + CH3COO- (aq)',
                'CH3COO- (aq) + H+ (aq) + 2 O2 (g) -> 2 CO2 (g) + 2 H2O (l)',
                'CH3COO- (aq) + 6 H2O (l) -> 2 CO2 (g) + 2 O2 (g) + 15 H+ (aq)',
                '2 CO2 (g) + 11 H+ (aq) + O2 (g) -> CH3COO- (aq) + 4 H2O (l)',
            ]
            for option, formula in zip(c['alternatives'], formulas): option['text'] = '$' + reaction(formula) + '$'
        if n == 94:
            replace_text(c, {'H⁺': r'$\ce{H+}$'})
            figure = move_figure_credit(c, ['Nimesulida GONÇALVES,', 'Química Nova,'], caption='Nimesulida')
            figure['credit'] = figure['credit'].removeprefix('Nimesulida ')
        if n == 97:
            replace_text(c, {'2 L': r'$2\,\mathrm{L}$', '1,4 mg/mL': r'$1{,}4\,\mathrm{mg/mL}$'})
            c['blocks'][1:3] = [paragraph(r'Considere as massas molares: $\ce{NaCl} = 58{,}5\,\mathrm{g/mol}$; $\ce{Na} = 23\,\mathrm{g/mol}$.')]
            for option in c['alternatives']: option['text'] = '$' + option['text'].replace(',', '{,}').replace(' g', r'\,\mathrm{g}') + '$'
        if n == 99:
            replace_text(c, {'f₀': '$f_0$', 'fᵣ': '$f_r$'})
            for option in c['alternatives']:
                text, expression = option['text'].rsplit(' e ', 1)
                option['text'] = text + ' e $' + expression.rstrip('.').replace('fᵣ', 'f_r').replace('f₀', 'f_0') + '$.'
        if n == 100:
            title = 'Mirascópio 3D: produtor de ilusão instantânea'
            c['blocks'][0:1] = [paragraph(title), paragraph(c['blocks'][0]['text'].removeprefix(title).strip())]
            replace_text(c, {'E₁': '$E_1$', 'E₂': '$E_2$'})
            move_figure_credit(c, ['SALZMANN,', 'Acesso em: 27 jun.'])
        if n == 114:
            replace_text(c, {'CO₂': r'$\ce{CO2}$', 'O₂': r'$\ce{O2}$', '(HC)': r'($\ce{HC}$)', '(CO)': r'($\ce{CO}$)', '(NO)': r'($\ce{NO}$)'}, alternatives=True)
            for option in c['alternatives']:
                for species in ['NO', 'HC', 'CO']:
                    option['text'] = option['text'].replace('de '+species+'.', 'de $\\ce{'+species+'}$.').replace('de '+species+' ', 'de $\\ce{'+species+'}$ ')
            move_figure_credit(c, ['RANGEL,'])
        if n == 116:
            replace_text(c, {'Mg²⁺': r'$\ce{Mg^2+}$', 'Ca(OH)₂': r'$\ce{Ca(OH)2}$', 'Ca²⁺': r'$\ce{Ca^2+}$'})
            c['blocks'][1:] = [
                {'type': 'math', 'tex': reaction('Mg^2+ (aq) + Ca(OH)2 (aq) -> Mg(OH)2 (s) + Ca^2+ (aq)')},
                paragraph(r'O método adequado para separar o $\ce{Mg(OH)2}$ dessa mistura é a'),
            ]
        if n == 118:
            replace_text(c, {'Ca₅(PO₄)₃OH': r'$\ce{Ca5(PO4)3OH}$'})
            formula = next(b for b in c['blocks'] if b['type'] == 'math')
            formula['tex'] = r'\ce{Ca5(PO4)3OH (s)} + \ce{H+ (aq)}\ \underset{\text{Mineralização}}{\overset{\text{Desmineralização}}{\rightleftharpoons}}\ \ce{5 Ca^2+ (aq)} + \ce{3 PO4^3- (aq)} + \ce{H2O (l)}'
            for b in c['blocks']:
                if b['type'] == 'paragraph' and b['text'].startswith(('STORGATTO,', 'A química na odontologia.')): b['role'] = 'credit'
        if n == 123:
            move_figure_credit(c, ['PINTO-ZEVALLOS,', 'perspectivas para', 'Química Nova,'])
        if n == 128:
            replace_text(c, {'Am+': '$A^{m+}$', 'Bn−': '$B^{n-}$', 'e⁻': r'$\ce{e-}$'})
            move_figure_credit(c, ['TANG,', 'Angewandte Chemie'])
        if n == 132:
            replace_text(c, {'L₁': '$L_1$', 'L₂': '$L_2$', 'V_QR': '$V_{QR}$'})
        if n == 133:
            c['blocks'][0:2] = [paragraph(c['blocks'][0]['text'] + ' ' + c['blocks'][1]['text'])]
            replace_text(c, {'70%': r'$70\%$', '16 g/mol': r'$16\,\mathrm{g/mol}$', '22 L/mol': r'$22\,\mathrm{L/mol}$', '46 g/mol': r'$46\,\mathrm{g/mol}$', '1 m³': r'$1\,\mathrm{m^3}$', '0,59 L': r'$0{,}59\,\mathrm{L}$', '0,78 g/mL': r'$0{,}78\,\mathrm{g/mL}$', '10 mol': r'$10\,\mathrm{mol}$'})
            for option in c['alternatives']: option['text'] = '$' + option['text'].rstrip('.').replace(' g', r'\,\mathrm{g}') + '$.'
        if n == 135:
            title = 'Brasil fecha 2020 entre os maiores recicladores de latas de alumínio'
            c['blocks'][0:1] = [paragraph(title), paragraph(c['blocks'][0]['text'].removeprefix(title).strip())]
            replace_text(c, {'Al₂O₃': r'$\ce{Al2O3}$', '(Al)': r'($\ce{Al}$)', '50 kg': r'$50\,\mathrm{kg}$', '10 kg': r'$10\,\mathrm{kg}$', '97,4%': r'$97{,}4\%$', '4,0 × 10⁵': r'$4{,}0\times10^5$'})
            for option, tex in zip(c['alternatives'], [r'1{,}0\times10^4', r'3{,}9\times10^5', r'5{,}0\times10^5', r'1{,}9\times10^6', r'2{,}0\times10^7']): option['text'] = '$' + tex + r'\,\mathrm{ton}$'
            for b in c['blocks']:
                if b['type'] == 'paragraph' and b['text'].startswith('Disponível em:'): b['role'] = 'credit'
        if n == 170:
            replace_text(c, {'M1 = 6,9': '$M_1 = 6{,}9$', 'M1': '$M_1$', 'M2': '$M_2$', 'E₁': '$E_1$', 'E₂': '$E_2$'})
        c['statement'] = '\n\n'.join(b['text'] for b in c['blocks'] if b['type'] == 'paragraph')
        c['layout'].update(presentation_version=VERSION, review_status='source_compared_presentation', presentation_review={
            'date': '2026-10-31', 'reason': REASONS[n], 'source_page': c['page'],
            'previous_content_sha256': hashlib.sha256(json.dumps(before, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        })
        assert all(c[field] == before[field] for field in ['number', 'area', 'correct_answer', 'annulled', 'labels', 'page'])
        assert [a['letter'] for a in c['alternatives']] == [a['letter'] for a in before['alternatives']]
    return data


def main():
    data = apply_review(json.loads(BASELINE.read_text()))
    TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('Questões revisadas:', ', '.join(map(str, sorted(REASONS))))


if __name__ == '__main__': main()

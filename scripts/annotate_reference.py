"""Materializa decisões editoriais explícitas; não classifica por palavras-chave."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.presentation import content_fingerprint

# Tema (0–7), habilidade candidata e evidência da operação exigida no item.
# Habilidades ficam propostas: uma conferência técnica não é revisão independente.
MATH={
2023:{
136:(3,12,'Combinar volumes de tronco de cone e cilindro com a densidade da madeira.'),
137:(5,27,'Calcular média salarial ponderada pelas quantidades de funcionários.'),
138:(6,28,'Relacionar probabilidades de duas urnas e determinar a quantidade de bolas brancas.'),
139:(1,24,'Extrapolar progressões das vendas e comparar os meses de ultrapassagem.'),
140:(5,27,'Comparar média, mediana e moda da distribuição de viagens no gráfico.'),
141:(6,28,'Contar cartões por ano de curso e calcular a probabilidade ponderada.'),
142:(3,12,'Calcular o volume cilíndrico restante e o consumo diário por pessoa.'),
143:(0,3,'Aplicar aumentos e reduções percentuais à lista de espera da creche.'),
144:(7,16,'Relacionar altura, área da base e tempo para obter vazão constante.'),
145:(2,8,'Relacionar ângulos inscritos que enxergam o mesmo segmento AB.'),
146:(0,2,'Investigar somas no triângulo usando os números de 1 a 6 e uma progressão aritmética.'),
147:(0,16,'Converter tempo de caminhada em carboidratos, fatias e pacotes para duas pessoas.'),
148:(2,8,'Comparar comprimentos de cabos com razões trigonométricas dos três ângulos.'),
149:(7,11,'Relacionar centímetro da malha e altitude real para determinar a escala.'),
150:(1,19,'Traduzir noventa por cento da quantidade ingerida em expressão algébrica.'),
151:(4,24,'Comparar coordenadas dos nove pontos do gráfico de criptomoedas.'),
152:(1,21,'Usar expressão logarítmica da intensidade sonora e enquadrar o resultado em intervalos.'),
153:(0,3,'Combinar número de pessoas e duração de atendimento para comparar tempos de espera.'),
154:(2,7,'Reconhecer a região circular escondida pelo telhado triangular.'),
155:(2,12,'Calcular a diferença das áreas dos quadrados da piscina e da borda externa.'),
156:(4,24,'Somar intervalos de tempo em que o gráfico de sinal permanece nulo.'),
157:(5,27,'Contar pontos abaixo da massa média e acima da altura média na dispersão.'),
158:(1,21,'Modelar receita, custos fixos, diárias e comissão para satisfazer lucro mínimo.'),
159:(1,21,'Relacionar crescimento exponencial da população e capacidade total do produto.'),
160:(6,2,'Comparar contagens de senhas com restrições e sem repetição de caracteres.'),
161:(1,21,'Modelar equivalência financeira das três parcelas com juros compostos.'),
162:(1,19,'Representar preço como função afim com parcela fixa e coeficiente do volume.'),
163:(4,20,'Relacionar gráfico distância-tempo a possíveis trajetórias a velocidade constante.'),
164:(5,26,'Comparar percentuais de imunização por categoria. Item anulado, fora dos experimentos.'),
165:(2,12,'Somar áreas de pisos, espelhos e laterais dos três degraus.'),
166:(5,25,'Combinar tabelas de horas e gasto por atividade para comparar totais diários.'),
167:(0,16,'Ajustar consumo proporcional de papel e obter desconto relativo ao orçamento.'),
168:(6,28,'Calcular probabilidades em sorteios sucessivos com composição condicional da segunda urna.'),
169:(1,21,'Aplicar uma razão geométrica constante à intensidade luminosa por profundidade.'),
170:(1,21,'Obter mínimo da função quadrática no intervalo e comparar com categorias.'),
171:(7,10,'Converter ciclos Haab em dias e depois em anos Tzolkim.'),
172:(2,22,'Argumentar sobre áreas de círculos a partir do ângulo entre diâmetros.'),
173:(7,10,'Compor a unidade da razão entre consumo por tempo e massa corporal.'),
174:(4,6,'Localizar fileira e posição da poltrona seguindo orientação norte e direita.'),
175:(1,21,'Resolver sistema de relações entre os preços dos tíquetes e das cartelas.'),
176:(0,2,'Identificar o padrão de crescimento dos números figurados pentagonais.'),
177:(1,20,'Relacionar movimento circular uniforme e gráfico periódico suave de altura.'),
178:(4,20,'Representar volume acumulado com trechos crescentes e intervalo de vazão nula.'),
179:(0,1,'Interpretar representação aditiva de números em outro sistema de contagem.'),
180:(5,27,'Comparar médias de precipitação de pares de meses consecutivos.'),
},
2024:{
136:(7,10,'Relacionar micrômetros, milímetros e fatores de ampliação do microscópio.'),
137:(5,27,'Relacionar soma de notas e médias com denominadores quatro e cinco.'),
138:(6,2,'Contar escolhas ordenadas de algarismos e letras distintos em senha.'),
139:(0,3,'Comparar custo de duas unidades de X e uma de Y nas duas lojas.'),
140:(0,3,'Aplicar porcentagem sobre a quantidade de acertos e interpretar intervalos de conceito.'),
141:(4,20,'Compor relações entre grandezas em dois gráficos para determinar máximo.'),
142:(1,2,'Reconhecer crescimento por duplicação em etapas sucessivas de uma mensagem.'),
143:(0,5,'Avaliar receita de ingressos e lucro necessário de bebidas para atingir equilíbrio.'),
144:(3,7,'Identificar o sólido de revolução gerado pela rotação de trapézio.'),
145:(2,12,'Comparar áreas de dois retângulos com dimensões do campo.'),
146:(1,21,'Maximizar área retangular sob restrição linear de custo de telas.'),
147:(0,1,'Identificar representações equivalentes de números racionais no visor.'),
148:(1,21,'Determinar parâmetros da função exponencial a partir do gráfico de temperatura.'),
149:(3,12,'Converter fração de volume de cilindro em volume de cubo.'),
150:(2,12,'Combinar diâmetros, vãos e comprimento disponível para comparar orçamentos.'),
151:(7,11,'Aplicar o quadrado da escala linear à área da maquete e converter unidades.'),
152:(4,24,'Calcular saldos entre exportações e importações e ordená-los.'),
153:(0,1,'Converter uma taxa percentual em representação decimal.'),
154:(5,27,'Calcular a média dos tempos de leitura apresentados em tabela.'),
155:(2,12,'Comparar áreas de setores circulares sob restrição de cobertura mínima.'),
156:(1,19,'Construir expressão com tarifa fixa, tempo e distância.'),
157:(1,21,'Manter o preço total ao alterar a taxa fixa de entrega.'),
158:(0,5,'Comparar despesas com defensivos por área e máscara obrigatória.'),
159:(7,10,'Compor unidade do fluxo como vazão por área da membrana.'),
160:(0,16,'Relacionar volume, vazão e tempo com aumento percentual do tempo.'),
161:(4,20,'Relacionar enchimento de compartimentos e gráfico da maior coluna de água.'),
162:(1,21,'Comparar parcelas em progressão geométrica e meses de isenção.'),
163:(2,8,'Relacionar tangência e arcos das polias ao comprimento de correia.'),
164:(2,8,'Relacionar centro de triângulo equilátero à distância dos vértices.'),
165:(6,28,'Combinar probabilidades independentes de encontrar dois semáforos vermelhos.'),
166:(0,16,'Relacionar razões de população e área às densidades demográficas.'),
167:(0,3,'Subtrair medidas dadas por números mistos em polegadas.'),
168:(1,20,'Interpretar amplitudes de gráficos senoidais em dois intervalos de superfície.'),
169:(6,28,'Calcular probabilidade de sucesso na terceira tentativa sem reposição.'),
170:(1,21,'Aplicar a relação logarítmica entre energia liberada e magnitude Richter.'),
171:(2,9,'Comparar áreas de polígonos regulares de mesmo perímetro.'),
172:(0,16,'Combinar velocidades e frações do percurso para localizar o encontro dos ônibus.'),
173:(6,28,'Somar funcionários por faixa etária para comparar probabilidades de sorteio.'),
174:(3,6,'Identificar projeção ortogonal de trajetória espacial sobre o plano da base.'),
175:(3,12,'Comparar volumes de cilindros formados pelas duas orientações de uma folha.'),
176:(1,24,'Extrapolar a reta de tendência de receitas para o ano pedido.'),
177:(1,21,'Determinar custo fixo e variável em uma relação linear dada por tabela.'),
178:(5,27,'Ordenar seis percentuais de umidade e calcular a mediana.'),
179:(0,16,'Repartir pagamento proporcionalmente às horas trabalhadas dos engenheiros.'),
180:(6,2,'Contar equipes com restrição de quantidade mínima de cardiologistas.'),
}}

NATURE={
91:('Física','Mecânica'),92:('Química','Eletroquímica'),93:('Química','Química orgânica'),94:('Química','Equilíbrios químicos'),95:('Biologia','Biotecnologia'),96:('Física','Mecânica'),97:('Química','Soluções'),98:('Biologia','Evolução e diversidade'),99:('Física','Ondas e acústica'),100:('Física','Óptica'),101:('Física','Ondas e acústica'),102:('Biologia','Citologia e metabolismo'),103:('Física','Termologia e termodinâmica'),104:('Biologia','Saúde e imunologia'),105:('Química','Química ambiental'),106:('Física','Radiações e matéria'),107:('Química','Química orgânica'),108:('Biologia','Ecologia'),109:('Biologia','Fisiologia'),110:('Biologia','Evolução e diversidade'),111:('Biologia','Evolução e diversidade'),112:('Biologia','Genética'),113:('Biologia','Ecologia'),114:('Química','Química ambiental'),115:('Biologia','Citologia e metabolismo'),116:('Química','Reações e estequiometria'),117:('Biologia','Ecologia'),118:('Química','Equilíbrios químicos'),119:('Física','Óptica'),120:('Biologia','Saúde e imunologia'),121:('Física','Mecânica'),122:('Física','Termologia e termodinâmica'),123:('Química','Química orgânica'),124:('Biologia','Citologia e metabolismo'),125:('Química','Estrutura da matéria'),126:('Biologia','Saúde e imunologia'),127:('Física','Eletricidade'),128:('Física','Eletricidade'),129:('Física','Termologia e termodinâmica'),130:('Física','Termologia e termodinâmica'),131:('Física','Eletricidade'),132:('Física','Eletricidade'),133:('Física','Termologia e termodinâmica'),134:('Biologia','Ecologia'),135:('Química','Reações e estequiometria')}


def main():
    import pymupdf as fitz
    taxonomy=json.loads((ROOT/'data/taxonomy/enem-content-v1.json').read_text())
    themes=taxonomy['disciplines'][0]['themes']
    official=json.loads((ROOT/'data/sources/referencias/manifesto.json').read_text())
    with fitz.open(ROOT/'data/sources'/official['path']) as doc:
        matrix='\n'.join(doc[i].get_text() for i in [4,5,6])
    definitions={int(n):' '.join(t.split()) for n,t in re.findall(r'H(\d+)\s*[-–]\s*(.*?)(?=\nH\d+\s*[-–]|\n\s*Competência de área|\Z)',matrix,re.S)}
    assert set(definitions)==set(range(1,31))
    skills=[dict(id=f'MT.H{n}',competency=f'MT.C{next(c for c,start,end in [(1,1,5),(2,6,9),(3,10,14),(4,15,18),(5,19,23),(6,24,26),(7,27,30)] if start<=n<=end)}',text=t,page=5 if n<=14 else 6 if n<=26 else 7) for n,t in sorted(definitions.items())]
    (ROOT/'data/taxonomy/enem-official-math.json').write_text(json.dumps(dict(version='inep-enem-matriz-2009',source=official,skills=skills),ensure_ascii=False,indent=2)+'\n')
    annotations=[]
    for file in [ROOT/'data/catalog/enem-2023-matematica-azul.json',ROOT/'data/enem-2024-dia2-azul.json']:
        exam=json.loads(file.read_text());year=exam['year']
        for q in exam['questions']:
            c=q['content'];n=c['number'];bindings=[]
            if c['area']=='Matemática':
                theme,skill,reason=MATH[year][n];discipline='Matemática';selected=[themes[theme]]
                bindings=[dict(skill=f'MT.H{skill}',status='proposed',rationale=reason,matrix_page=5 if skill<=14 else 6 if skill<=26 else 7,source_sha256=official['sha256'])]
            else:
                discipline,theme=NATURE[n];selected=[theme];reason=f'Conferência do objeto e do comando do item com a fonte; disciplina principal {discipline}, tema {theme}. Casos interdisciplinares permanecem sujeitos a segunda revisão.'
            annotations.append(dict(question_id=q['question_id'],exam_id=exam['id'],year=year,number=n,page=c['page'],
                source_sha256=exam['source']['sha256'],content_sha256=content_fingerprint(c),
                taxonomy_version=taxonomy['version'],discipline=discipline,themes=selected,
                status='curated',reviewer='Codex — curadoria técnica assistida',independent_review=False,
                evidence=c['statement'][:350],rationale=reason,skill_candidates=bindings,
                eligible_for_experiments=c['area']=='Matemática' and not c['annulled']))
    path=ROOT/'data/classification/annotations-v1.json';path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(dict(version='reference-v1',policy='Temas curados tecnicamente. Habilidades são propostas com evidência, não rótulos oficiais atribuídos pelo Inep nem segunda revisão independente.',annotations=annotations),ensure_ascii=False,indent=2)+'\n')
    print(f'{len(annotations)} anotações; {sum(a["eligible_for_experiments"] for a in annotations)} itens elegíveis; habilidades propostas, não publicadas.')


if __name__=='__main__':main()

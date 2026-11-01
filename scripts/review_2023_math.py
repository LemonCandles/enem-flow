"""Curadoria reproduzível das questões 136–180, azul, ENEM 2023.

Páginas 16–31 comparadas visualmente com o PDF. As correções deste lote não
substituem o adaptador genérico nem constituem segunda revisão independente.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.preparation import prepare_exam
from backend.app.schemas import ExamImport

BASELINE=ROOT/'data/derived/baselines/enem-2023-matematica-auto-v1.json'
PDF=ROOT/'data/sources/enem/2023/regular/impresso/dia-2/caderno-7-azul/prova.pdf'
TARGET=ROOT/'data/catalog/enem-2023-matematica-azul.json'


def paragraph(text,role='body'):return dict(type='paragraph',text=text,role=role)


def review(data,render=True):
    data=copy.deepcopy(data)
    data.update(id='enem-2023-matematica-azul',title='ENEM 2023 — Matemática',kind='section',expected_items=45,duration_minutes=150)
    qs={q['content']['number']:q['content'] for q in data['questions']}
    def body(n,*texts):qs[n]['blocks']=[paragraph(t) if isinstance(t,str) else t for t in texts]
    def options(n,texts):qs[n]['alternatives']=[dict(letter=l,text=t,image=None) for l,t in zip('ABCDE',texts)]
    def table(headers,rows,caption):return dict(type='table',headers=headers,rows=rows,caption=caption)
    def figure(n,pn,rect,alt,name='figura',credit=''):
        crop_hash=hashlib.sha256(json.dumps([data['source']['sha256'],pn,rect]).encode()).hexdigest()[:10]
        relative=Path('enem-2023-matematica-azul/native')/f'q{n}-{name}-{crop_hash}.png'
        if render:
            import pymupdf as fitz
            with fitz.open(PDF) as doc:
                target=ROOT/'data/assets'/relative;target.parent.mkdir(parents=True,exist_ok=True)
                doc[pn-1].get_pixmap(matrix=fitz.Matrix(2.5,2.5),clip=fitz.Rect(rect)).save(target)
        block=dict(type='image',asset=dict(path='/assets/'+relative.as_posix(),alt=alt),caption='',credit=credit,equations=[])
        qs[n]['layout'].setdefault('reviewed_figures',[]).append(dict(page=pn,bbox=rect,asset=block['asset']['path']))
        return block
    def old(n,i):return qs[n]['blocks'][i]['text']
    def prose(n):return [b['text'] for b in qs[n]['blocks'] if b['type']=='paragraph']

    for c in qs.values():
        c['layout'].pop('reviewed_figures',None)
        # Keep original issues as evidence, explicitly resolved by this source review.
        c['layout']['automatic_issues_before_review']=copy.deepcopy(c['layout'].get('preparation',{}).get('issues',[]))
        c['layout'].pop('preparation',None)
        c['layout']['extraction']['issues']=[]

    texts=prose(136)
    body(136,texts[0],figure(136,16,[31,193,277,385],'Cone de altura 36 cm e diâmetro 18 cm; cone superior de diâmetro 6 cm removido. Seta indica o tronco perfurado por um cilindro central de diâmetro 6 cm.'),*texts[1:])
    t=qs[137]['blocks'][1];t.update(headers=['Setor','Quantidade de funcionários','Salário (em real)'],rows=[['Produção','75','2 000,00'],['Administração','25','7 000,00']],caption='Funcionários e salários por setor')
    t=next(b for b in qs[139]['blocks'] if b['type']=='table');t.update(headers=['Produto','Vendas em abril (unidade)','Vendas em maio (unidade)','Vendas em junho (unidade)'],rows=[['I','80','90','100'],['II','190','170','150']],caption='Vendas mensais dos produtos I e II')
    texts=prose(140)
    body(140,texts[0],figure(140,17,[138,466,431,618],'Gráfico de barras: 1 viagem, 10 motoristas; 2 viagens, 10; 3 viagens, 55; 4 viagens, 25; 5 viagens, zero; 6 viagens, 50; 7 viagens, 10.'),texts[-1])
    options(141,[r'$\frac{1}{2}$',r'$\frac{1}{3}$',r'$\frac{1}{8}$',r'$\frac{2}{9}$',r'$\frac{3}{8}$'])
    for b in qs[142]['blocks']:
        if b['type']=='paragraph':b['text']=b['text'].replace('aproximação para p.','aproximação para $\\pi$.')
    texts=prose(144)
    body(144,texts[0],table(['Horário (h)','Nível da água (m)'],[['6:00','0,5'],['8:00','1,1'],['12:00','2,3'],['15:00','3,2']],'Altura da água durante o abastecimento'),figure(144,19,[31,279,278,445],'Fotografia da construção de uma cisterna cilíndrica, parcialmente enterrada.',credit='Disponível em: www.paraibamix.com. Acesso em: 3 dez. 2012.'),texts[-1])
    body(145,r'Num certo momento de um jogo digital, a tela apresenta a imagem representada na figura. O ponto $Q_1$ representa a posição de um jogador que está com a bola, os pontos $Q_2$, $Q_3$, $Q_4$, $Q_5$ e $Q_6$ também indicam posições de jogadores da mesma equipe, e os pontos $A$ e $B$ indicam os dois pés da trave mais próxima deles. No momento da partida retratado, o jogador $Q_1$ tem a posse da bola, que será passada para um dos outros jogadores das posições $Q_n$, $n\in\{2,3,4,5,6\}$, cujo ângulo $A\widehat{Q_n}B$ tenha a mesma medida do ângulo $\alpha=A\widehat{Q_1}B$.',figure(145,19,[290,72,534,200],'Vista superior de campo de futebol com trave AB à esquerda. Jogadores Q1 a Q6 e circunferências tracejadas passam por A e B. O ângulo alfa está marcado em Q1.'),'Qual é o jogador que receberá a bola?')
    texts=prose(146);body(146,texts[0],figure(146,19,[355,380,466,483],'Triângulo com seis círculos vazios: um em cada vértice e um no meio de cada lado.'),*texts[1:])
    texts=prose(147)
    body(147,texts[0],paragraph('CIRINO, C. Boa pergunta: consumir carboidratos antes dos exercícios melhora o desempenho do atleta? Revista Saúde! É Vital, n. 330, nov. 2010 (adaptado).','credit'),texts[2].split('(adaptado). ',1)[-1],texts[-1])
    body(148,prose(148)[0],figure(148,20,[31,505,277,633],'Mastro vertical com ponto P a altura h. Três cabos partem de P até o chão e cada um forma ângulo alfa com o plano horizontal.'),r'Os cabos de aço formam um ângulo $\alpha$ com o plano do chão.','Por medida de segurança, há apenas três opções de instalação:',r'• opção I: $h=11\,\mathrm{m}$ e $\alpha=30^\circ$',r'• opção II: $h=12\,\mathrm{m}$ e $\alpha=45^\circ$',r'• opção III: $h=18\,\mathrm{m}$ e $\alpha=60^\circ$','A opção a ser escolhida é aquela em que a medida dos cabos seja a menor possível.','Qual será a medida, em metro, de cada um dos cabos a serem instalados?')
    options(148,[r'$\frac{22\sqrt{3}}{3}$',r'$11\sqrt{2}$',r'$12\sqrt{2}$',r'$12\sqrt{3}$','$22$'])
    texts=prose(149);body(149,texts[0],texts[1],figure(149,20,[289,411,536,502],'Gráfico em malha quadrada de altitude em função da distância. O voo começa e termina no eixo horizontal; a altitude máxima ocupa um quadradinho.'),'Essa tela apresenta os dados de um voo cuja maior altitude alcançada foi de $5\\,\\mathrm{km}$.',texts[-1])
    options(150,[r'$C=0{,}9q$',r'$C=0{,}1q$',r'$C=1-0{,}1q$',r'$C=1-0{,}9q$',r'$C=q-10$'])
    texts=prose(151);body(151,texts[0],figure(151,21,[31,394,278,594],'Gráfico cartesiano dos valores das criptomoedas A (horizontal) e B (vertical), em milhar de real, com nove posições identificadas das 9 h às 17 h.'),'Durante horas consecutivas, esses valores foram observados em nove instantes, representados por horas exatas.',texts[-1])
    body(152,r'A exposição a alguns níveis sonoros pode causar lesões auditivas. Por isso, em uma indústria, são adotadas medidas preventivas de acordo com a máquina que o funcionário opera e o nível $N$ de intensidade do som, medido em decibel (dB), a que o operário é exposto, sendo $N=\log_{10} I^{10}-\log_{10} I_0^{10}$, $I$ a intensidade do som e $I_0=10^{-12}\,\mathrm{W/m^2}$.',paragraph('Disponível em: www.sofisica.com.br. Acesso em: 8 jul. 2015 (adaptado).','credit'),r'Quando o som é considerado baixo, ou seja, $N=48\,\mathrm{dB}$ ou menos, deve ser utilizada a medida preventiva I. No caso de o som ser moderado, quando $N$ está no intervalo $(48\,\mathrm{dB},55\,\mathrm{dB})$, deve ser utilizada a medida preventiva II. Quando o som é moderado alto, o que equivale a $N$ no intervalo $(55\,\mathrm{dB},80\,\mathrm{dB})$, a medida preventiva a ser usada é a III. Se $N$ estiver no intervalo $(80\,\mathrm{dB},115\,\mathrm{dB})$, quando o som é considerado alto, deve ser utilizada a medida preventiva IV. E se o som é considerado muito alto, com $N$ maior que $115\,\mathrm{dB}$, deve-se utilizar a medida preventiva V.',r'Uma nova máquina, com $I=8\times10^{-8}\,\mathrm{W/m^2}$, foi adquirida e será classificada de acordo com o nível de ruído que produz.',r'Considere $0{,}3$ como aproximação para $\log_{10}2$.','O funcionário que operará a nova máquina deverá adotar a medida preventiva')
    texts=prose(154);body(154,texts[0],figure(154,22,[73,481,236,633],'Quadro com três torres e uma lua circular ao fundo. O telhado da torre central é um triângulo equilátero com vértice no centro da lua.'),texts[-1])
    texts=prose(155);body(155,texts[0],figure(155,22,[289,132,535,311],'Planta de piscina quadrada cercada por uma calçada de largura constante de 5 m em cada um dos quatro lados.'),texts[-1])
    texts=prose(156);body(156,texts[0],figure(156,22,[289,489,537,641],'Intensidade do sinal ao longo de 30 min. O gráfico fica sobre o eixo horizontal nos intervalos de 10 a 12 min e de 16 a 20 min; os demais trechos têm sinal positivo.'),texts[-1])
    texts=prose(157);body(157,texts[0],figure(157,23,[31,180,278,316],'Diagrama de dispersão com dez estudantes. Eixo horizontal: massa corporal de 0 a 140 kg; eixo vertical: altura de 1,45 a 1,80 m. A grade permite comparar as posições com 80 kg e 1,65 m, valores médios fornecidos no enunciado.'),*texts[-2:])
    for b in qs[160]['blocks']:
        if b['type']=='paragraph':b['text']=b['text'].replace('!, @, #, $, , &.',r'!, @, #, \$, *, &.').replace('e p3 as','e $p_3$ as')
    for b in qs[161]['blocks']:
        if b['type']=='paragraph' and 'aproximação para' in b['text']:b['text']=r'Utilize $5{,}29$ como aproximação para $\sqrt{28}$.'
    options(161,[r'$6{,}7\%$',r'$10\%$',r'$20\%$',r'$21{,}5\%$',r'$23{,}3\%$'])
    options(162,[r'$y=250x$',r'$y=500x$',r'$y=750x$',r'$y=250x+500$',r'$y=500x+250$'])
    texts=prose(163);body(163,texts[0],figure(163,24,[290,65,536,254],'Distância à base (km) em função do tempo (min): segmentos ligam (0;0), (10;3), (20;3) e (30;0).'),'A vista superior da trajetória realizada pelo vigilante durante a patrulha registrada no gráfico é descrita pela representação')
    rects=[[307,300,413,358],[307,364,413,423],[307,427,413,478],[307,484,413,540],[307,544,413,603]]
    alts=['Setor circular: saída do vértice por um raio, percurso em arco e volta pelo outro raio.','Triângulo fechado, percorrido por três segmentos de reta.','Dois segmentos formando um V invertido, sem base.','Linha poligonal com subida oblíqua, trecho horizontal e descida oblíqua.','Semicírculo percorrido pelo arco e pelo diâmetro.']
    qs[163]['alternatives']=[dict(letter=l,text='',image=figure(163,24,r,a,'alternativa-'+l)['asset']) for l,r,a in zip('ABCDE',rects,alts)]
    texts=prose(164);body(164,texts[0],figure(164,25,[80,114,492,266],'Percentuais aproximados de imunização no gráfico: adultos de 20 a 29 anos, 42%; gestantes, 54%; doentes crônicos, 57%; indígenas, 66%; crianças de 6 meses a 2 anos, 87%; trabalhadores da saúde, 100%.',credit='Época, 26 abr. 2010 (adaptado).'),texts[-1])
    texts=prose(165);body(165,texts[0],figure(165,25,[145,421,421,617],'Escada com três degraus de largura 1,0 m. Cada piso tem profundidade 0,25 m e cada espelho altura 0,20 m. Indicadas também as paredes laterais.'),*texts[1:])
    ts=[b for b in qs[166]['blocks'] if b['type']=='table'];ts[0].update(headers=['Dias da semana','Caminhar','Correr','Andar de bicicleta','Jogar futebol'],rows=[['Segunda-feira','1,0','0,5','0,0','2,0'],['Terça-feira','0,5','1,0','0,5','1,0'],['Quarta-feira','0,0','1,5','1,0','0,5'],['Quinta-feira','0,0','2,0','0,0','0,0'],['Sexta-feira','0,0','0,5','0,0','2,5']],caption='Horas diárias de atividade física');ts[1].update(headers=['Atividade física','Caminhar','Correr','Andar de bicicleta','Jogar futebol'],rows=[['Gasto calórico (cal/h)','248','764','356','492']],caption='Gasto calórico por hora')
    texts=prose(168);body(168,*texts[:2]);options(168,[r'$\frac1{50}$ e $\frac1{60}$',r'$\frac1{50}$ e $\frac1{50}$',r'$\frac1{50}$ e $\frac1{10}$',r'$\frac1{55}$ e $\frac1{54}$',r'$\frac1{100}$ e $\frac1{100}$'])
    body(169,r'O esquema mostra como a intensidade luminosa decresce com o aumento da profundidade em um rio, sendo $L_0$ a intensidade na sua superfície.',figure(169,27,[41,512,275,690],'Profundidade e intensidade luminosa: na superfície, L0; a 1 m, dois terços de L0; a 2 m, quatro nonos; a 3 m, oito vinte e sete avos.'),'Considere que a intensidade luminosa diminui, a cada metro acrescido na profundidade, segundo o mesmo padrão do esquema.',r'A intensidade luminosa correspondente à profundidade de $6\,\mathrm{m}$ é igual a')
    options(169,[r'$\frac{1}{9}L_0$',r'$\frac{16}{27}L_0$',r'$\frac{32}{243}L_0$',r'$\frac{64}{729}L_0$',r'$\frac{128}{2187}L_0$'])
    body(170,r'Analisando as vendas de uma empresa, o gerente concluiu que o montante diário arrecadado, em milhar de real, poderia ser calculado pela expressão $V(x)=\frac{x^2}{4}-10x+105$, em que os valores de $x$ representam os dias do mês, variando de 1 a 30.',r'Um dos fatores para avaliar o desempenho mensal da empresa é verificar qual é o menor montante diário $V_0$ arrecadado ao longo do mês e classificar o desempenho conforme as categorias apresentadas a seguir, em que as quantidades estão expressas em milhar de real.',r'• Ótimo: $V_0\ge24$',r'• Bom: $20\le V_0<24$',r'• Normal: $10\le V_0<20$',r'• Ruim: $4\le V_0<10$',r'• Péssimo: $V_0<4$','No caso analisado, qual seria a classificação do desempenho da empresa?')
    body(172,r'Sejam $a$, $b$ e $c$ as medidas dos lados de um triângulo retângulo, tendo $a$ como medida da hipotenusa. Esses valores $a$, $b$ e $c$ são, respectivamente, os diâmetros dos círculos $C_1$, $C_2$ e $C_3$, como apresentados na figura.',figure(172,28,[40,390,255,583],'Triângulo retângulo de lados a, b e c. Sobre cada lado foi construído um círculo de diâmetro igual ao lado: C1 sobre a, C2 sobre b e C3 sobre c.'),r'Observe que essa construção assegura, pelo teorema de Pitágoras, que área $(C_1)$ = área $(C_2)$ + área $(C_3)$.','Um professor de matemática era conhecedor dessa construção e, confraternizando com dois amigos em uma pizzaria onde são vendidas pizzas somente em formato de círculo, lançou um desafio: mesmo sem usar um instrumento de medição, poderia afirmar com certeza se a área do círculo correspondente à pizza que ele pedisse era maior, igual ou menor do que a soma das áreas das pizzas dos dois amigos. Assim, foram pedidas três pizzas. O professor as dividiu ao meio e formou um triângulo com os diâmetros das pizzas, conforme indicado na figura.',figure(172,28,[297,67,523,198],'Triângulo formado pelos diâmetros de três meias pizzas. O ângulo alfa está entre os diâmetros das pizzas dos amigos; o lado oposto é o diâmetro da pizza do professor.','pizzas'),r'A partir da medida do ângulo $\alpha$, o professor afirmou que a área de sua pizza é maior do que a soma das áreas das outras duas pizzas.','A área da pizza do professor de matemática é maior do que a soma das áreas das outras duas pizzas, pois')
    options(172,[r'$0^\circ<\alpha<90^\circ$',r'$\alpha=90^\circ$',r'$90^\circ<\alpha<180^\circ$',r'$\alpha=180^\circ$',r'$180^\circ<\alpha<360^\circ$'])
    texts=prose(173);body(173,*texts[:4]);options(173,[r'$\frac{\mathrm{min}}{\mathrm{mL}\cdot\mathrm{kg}}$',r'$\frac{\mathrm{mL}}{\mathrm{min}\cdot\mathrm{kg}}$',r'$\frac{\mathrm{min}\cdot\mathrm{mL}}{\mathrm{kg}}$',r'$\frac{\mathrm{min}\cdot\mathrm{kg}}{\mathrm{mL}}$',r'$\frac{\mathrm{mL}\cdot\mathrm{kg}}{\mathrm{min}}$'])
    texts=prose(174);body(174,texts[0],figure(174,29,[86,147,482,367],'Mapa do cinema: fileiras A a J de baixo para cima e poltronas 1 a 12 da esquerda para a direita. Escadas entre 3/4 e 9/10. Estrela na primeira escada, na fileira E. Norte aponta para cima; tela abaixo da fileira A.'),*texts[-2:])
    texts=prose(176);body(176,texts[0],figure(176,30,[33,152,270,337],'Seis arranjos pentagonais de pontos, correspondentes aos números 1, 5, 12, 22, 35 e 51.'),texts[-1])
    texts=prose(177);body(177,texts[0],figure(177,30,[63,492,244,680],'Roda-gigante com oito cadeiras. A pessoa P está na cadeira superior. Uma seta indica giro no sentido horário; o solo está abaixo da roda.'),texts[1],'O gráfico que melhor representa a variação dessa altura, em função do tempo, contado a partir do instante em que a cadeira onde se encontra a pessoa P se encontra na posição mais alta da roda-gigante, é')
    rects=[[307,130,528,210],[307,223,528,308],[307,321,528,400],[307,418,528,499],[307,508,528,586]]
    alts=['Curva senoidal suave de altura versus tempo, iniciando no máximo e com mínimos acima de zero.','Onda triangular de altura versus tempo, iniciando em valor máximo.','Onda formada por segmentos inclinados e pequenos patamares nos extremos.','Arcos curvos unidos por pontas nos mínimos sobre o eixo horizontal.','Arcos curvos com pontas nos máximos e mínimos próximos do eixo horizontal.']
    qs[177]['alternatives']=[dict(letter=l,text='',image=figure(177,30,r,a,'alternativa-'+l)['asset']) for l,r,a in zip('ABCDE',rects,alts)]
    body(178,r'Estudantes trabalhando com robótica criaram uma “torneira inteligente” que automatiza sua abertura e seu fechamento durante a limpeza das mãos. A tecnologia funciona da seguinte forma: ao se colocarem as mãos sob a torneira, ela libera água durante 3 segundos para que a pessoa possa molhá-las. Em seguida, interrompe o fornecimento de água por 5 segundos, enquanto a pessoa ensaboa suas mãos, e finaliza o ciclo liberando água para o enxágue por mais 3 segundos. Considere o tempo $(t)$, em segundo, contado a partir do instante em que se inicia o ciclo. A vazão de água nessa torneira é constante.',r'Um esboço de gráfico que descreve o volume de água acumulado, em litro, liberado por essa torneira durante um ciclo de lavagem das mãos, em função do tempo $(t)$, em segundo, é')
    rects=[[50,257,227,349],[50,352,227,441],[50,445,227,535],[50,539,227,628],[50,630,227,724]]
    alts=['Volume cresce de 0 a 3 s, cai a zero entre 3 e 8 s e retorna a um trecho crescente de 8 a 11 s.','Volume cresce linearmente de 0 a 3 s, permanece constante de 3 a 8 s e cresce com a mesma inclinação de 8 a 11 s.','Volume permanece em um patamar positivo de 0 a 3 s, zero de 3 a 8 s e retorna ao mesmo patamar de 8 a 11 s.','Volume cresce em linha reta de 0 a 11 s, sem intervalo constante.','Volume cresce de 0 a 3 s, cai a zero de 3 a 8 s e cresce com maior inclinação de 8 a 11 s.']
    qs[178]['alternatives']=[dict(letter=l,text='',image=figure(178,31,r,a,'alternativa-'+l)['asset']) for l,r,a in zip('ABCDE',rects,alts)]
    texts=prose(179);body(179,texts[0],figure(179,31,[299,120,529,289],'Quadrinho com numerais de 1 a 6: 1 é urapum; 2, okosa; 3, okosa urapum; 4, okosa okosa; 5 aparece como interrogação; 6, okosa okosa okosa.'),texts[-1])
    for n,c in qs.items():
        for b in c['blocks']:
            if b['type']=='paragraph':b['text']=b['text'].replace('aproximação para π.',r'aproximação para $\pi$.')
        c['statement']='\n\n'.join(b['text'] for b in c['blocks'] if b['type']=='paragraph')
        c['images']=[];c['original_layout']=False
        c['layout']['source_review']=dict(version='math-2023-v1',source_sha256=data['source']['sha256'],page=c['page'],reviewer='Codex — conferência técnica com a fonte',independent_review=False,reason='Enunciado, alternativas, tabelas, fórmulas, recortes e gabarito comparados às páginas 16–31; evidência anterior preservada.')
    prepared,report=prepare_exam(data)
    if report['errors']:raise ValueError(f'Curadoria deixou {report["errors"]} erros bloqueantes.')
    return prepared.model_dump(),report


if __name__=='__main__':
    source=json.loads(BASELINE.read_text());data,report=review(source)
    TARGET.parent.mkdir(parents=True,exist_ok=True);TARGET.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (TARGET.with_suffix('.report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(data["questions"])} questões; {report["errors"]} erros; {report["warnings"]} avisos.')

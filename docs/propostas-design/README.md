# Design — Conhecimento em construção

Proposta atual: **Encaixes no layout**, refinada em 30/10/2026. As peças de leitura, raciocínio e prática compartilham superfícies, curvas e ícones com a interface. Seus contornos continuam até os cartões de ações, que recebem encaixes complementares.

## Temas

| Escuro | Claro |
| --- | --- |
| ![Encaixes no layout escuro](proposta-escura.png) | ![Encaixes no layout claro](proposta-clara.png) |

As duas artes têm **1536 × 1024**. Mantêm a barra lateral à esquerda, a tipografia grande e fina e os fundos neutros. O verde `#009485` aparece nas junções, nos indicadores e na ação principal.

## Paleta

| Uso | Escuro | Claro |
| --- | --- | --- |
| Fundo | `#131313` | `#F6F5F0` |
| Barra lateral | `#191919` | `#EEEEE8` |
| Texto principal | `#F1F0EA` | `#242424` |
| Texto de apoio | `#AAA79E` | `#706F65` |
| Bordas | `#383833` | `#D8D6CC` |
| Acento / ação | `#009485` | `#009485` |
| Texto da ação | `#131313` | `#131313` |

[Ver paletas](paletas.svg). Os códigos são a referência para implementação; os pixels das artes podem variar pela geração.

## Diretrizes de implementação

- Fonte sugerida: Manrope, peso 300 no título de entrada e 400–500 nos textos e controles.
- Construir os contornos em SVG/CSS, compartilhando cores, raios e espessuras com os componentes.
- Manter textos e controles em HTML, com áreas de clique e foco preservadas.
- Renderizar enunciados, alternativas, tabelas e fórmulas como conteúdo nativo do JSON.
- Deixar a área de leitura das questões livre de decoração.
- Adaptar a composição para celular, reduzindo os encaixes quando necessário. Os mockups atuais mostram apenas o desktop.

## Geração

As artes foram geradas com a ferramenta integrada **ImageGen**. Os prompts foram preservados para novos refinamentos:

- [Prompt escuro](prompt-escuro.txt).
- [Prompt claro](prompt-claro.txt).

## Implementação

O design foi aplicado ao site: página inicial com encaixes em SVG, navegação lateral, tipografia Manrope e temas claro/escuro. A preferência de tema é salva no navegador; a primeira visita acompanha a preferência do sistema. As demais páginas compartilham as cores e os componentes da direção escolhida.

No celular, o menu é recolhido e os cartões se organizam em uma coluna. As questões mantêm texto selecionável, tabelas HTML, fórmulas e figuras separadas. O texto de apoio claro usa `#706F65` para melhorar o contraste em relação ao estudo inicial.

O código fica em `frontend/src/components/design.tsx`, `theme-toggle.tsx`, `dashboard.tsx`, `app.tsx` e `frontend/src/app/globals.css`. Os PNGs desta pasta são referências de design; a interface implementada usa elementos nativos.

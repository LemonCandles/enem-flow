"""Patterns and messages shared by the preparation steps and the content validation."""

import re

CREDIT = re.compile(r'^(?:Dispon[ií]vel em|Acesso em|Fonte\s*:|https?://|[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ -]{2,},\s)')
CAPTION = re.compile(r'^(?:Figura|Gr[aá]fico|Esquema|Fotografia|Ilustra[çc][aã]o)\s*(?:\d+|[–—:-])', re.I)
MESSAGES = {
    'ambiguous_charge': 'Carga sem posição inequívoca: confira se o número é índice ou carga e use LaTeX explícito.',
    'ambiguous_generic_ion': 'Íon genérico ou símbolo de elemento ambíguo: confira a posição de m/n no PDF.',
    'ambiguous_liquid_state': 'Estado físico (I) ambíguo: confira no PDF se é l minúsculo.',
    'ambiguous_exponent': 'Expoente sem posição preservada: confira no PDF antes de converter.',
    'unbalanced_formula': 'Parênteses da fórmula incompletos na extração.',
    'unreadable_reaction': 'Reação não interpretada com segurança; preserve o original e transcreva em LaTeX.',
    'replacement_character': 'Há caractere não reconhecido na extração.',
    'figure_association_inferred': 'Legenda/referência associada por proximidade; confira o vínculo com a figura.',
    'original_layout': 'O conteúdo ainda contém recorte integral. Prepare o PDF para separar texto e figuras.',
    'unlocated_images': 'Imagens sem posição: informe blocos image na ordem de leitura para associar suas legendas.',
    'missing_description': 'Descrição genérica da figura: substitua por uma descrição de seu conteúdo.',
    'invalid_latex': 'Delimitadores ou agrupamentos LaTeX incompletos; corrija antes de aprovar.',
    'missing_alternative': 'Alternativa não extraída: confira e recupere seu conteúdo na fonte oficial.',
    'control_character': 'A extração contém caracteres de controle sem representação legível; confira o original.',
}

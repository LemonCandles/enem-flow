"""Answers read from the official key, by booklet color and language."""

import re


from .regions import language_key


def answer_key_rows(text, language=None, numbers=None, booklet=None):
    """Number -> answer. Language options print one column per language ("1 C D").

    "*A" marks an answer rectified by the Inep. `numbers` limits the key to the
    booklet's questions, since some keys also list the other day.
    """
    text = text.replace('\xa0', ' ')
    columns = [
        key
        for _, key in sorted((m.start(), language_key(m[0])) for m in re.finditer(r'INGL[ÊE]S|ESPANHOL', text, re.I))
    ]
    columns = list(dict.fromkeys(columns))
    chosen = language_key(language) if language else None
    colors = list(
        dict.fromkeys(
            value.casefold()
            for value in re.findall(r'Gab[_ -]+(Azul|Amarelo|Branco|Rosa|Cinza|Verde|Laranja|Roxo)\b', text, re.I)
        )
    )
    selected_color = next(
        (color for color in colors if re.search(r'\b' + color + r'\b', (booklet or '').casefold())), None
    )
    if len(colors) > 1 and selected_color is None:
        raise ValueError('O gabarito reúne várias cores: informe o caderno/cor no manifesto.')
    rows = {}
    for n, first, second in re.findall(
        r'\b(\d{1,3})\s+\*?(ANULAD[AO]|[ABCDE])\b(?:[ \t]*\n?[ \t]*\*?(ANULAD[AO]|[ABCDE])(?=[ \t]*(?:\n|$)))?',
        text,
        re.I,
    ):
        if numbers is not None and int(n) not in numbers:
            continue
        value = first
        if second:
            if len(columns) != 2:
                raise ValueError(
                    f'Gabarito com duas respostas na questão {int(n)} sem colunas de língua identificadas.'
                )
            if not chosen:
                raise ValueError(
                    f'O gabarito tem colunas por língua ({", ".join(columns)}): declare "language" no manifesto.'
                )
            if chosen not in columns:
                raise ValueError(f'Língua "{language}" ausente no gabarito ({", ".join(columns)}).')
            value = (first, second)[columns.index(chosen)]
        value = value.upper()
        rows.setdefault(int(n), []).append(None if value.startswith('ANULAD') else value)
    answers = {}
    for number, values in rows.items():
        if len(colors) > 1:
            if len(values) != len(colors):
                raise ValueError(f'Questão {number}: quantidade de respostas difere das colunas de cor.')
            answers[number] = values[colors.index(selected_color)]
        elif len(set(values)) > 1:
            raise ValueError(f'Gabaritos conflitantes na questão {number}; confira as colunas da fonte.')
        else:
            answers[number] = values[0]
    return answers

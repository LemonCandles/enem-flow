"""Conservative notation conversion. Never balance reactions or infer lost exponents."""
import re

LATEX = re.compile(r'(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|(?<![A-Z\\])\$(?!\$)(?:\\.|[^$\\\n])+\$)')
SUB = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
SUB_LETTERS = str.maketrans('ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ', 'aehijklmnoprstuvx')
SUP = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻', '0123456789+-')
ELEMENTS = set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split())
CHEM_CONTEXT = re.compile(r'\b(?:qu[ií]mic\w*|[ií]ons?|c[aá]tions?|[aâ]nions?|molar\w*|mol[eé]cul\w*|hidroxi\w*|[aá]cido\w*|rea[çc][aã]o|rea[çc][oõ]es|pr[oó]tons?|el[eé]trons?|composto\w*|gases|oxida\w*|redu[çc]\w*|f[oó]rmula\w*)\b', re.I)
SPECIES = r'(?:[A-Z][a-z]?|\([A-Za-z0-9₀-₉]+\))[A-Za-z0-9₀-₉()^⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻+−–-]*'
CANDIDATE = re.compile(r'(?<![\w\\])' + SPECIES + r'(?![\w$])')
REACTION = re.compile(r'[^\n.;:]+?(?:⟶|→|⇌|↔|->|<=>)[^\n.;:]+')


def chemical_token(value):
    value = value.translate(SUB).replace('−', '-').replace('–', '-')
    value = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+', lambda m: '^' + m[0].translate(SUP), value)
    # A generic ion such as A^{m+} has no element identity to infer.
    value = re.sub(r'\^\{([^}]+)\}', r'^\1', value)
    core = re.sub(r'\^(?:\d*[+-]|[mn][+-])$|[+-]$', '', value)
    atoms = re.findall(r'[A-Z][a-z]?', core)
    residue = re.sub(r'[A-Z][a-z]?|\d+|[()]', '', core)
    if value.startswith('e') and value in {'e-', 'e^-'}: return 'e-', None
    if residue or not atoms or any(atom not in ELEMENTS for atom in atoms): return None, None
    if core.count('(') != core.count(')'): return None, 'unbalanced_formula'
    if re.fullmatch(r'[A-Z][a-z]?\d+[+-]', value): return None, 'ambiguous_charge'
    return value, None


def species(value):
    match = re.fullmatch(r'\s*(\d+(?:[.,]\d+)?\s*)?(.+?)(?:\s*\((aq|s|l|g|I)\))?\s*', value)
    if not match: return None, 'unreadable_reaction'
    coefficient, formula, state = match.groups()
    formula, issue = chemical_token(formula.strip())
    if issue or not formula: return None, issue or 'unreadable_reaction'
    return (coefficient or '') + formula + (f' ({state})' if state else ''), 'ambiguous_liquid_state' if state == 'I' else None


def reaction_tex(text):
    sides = re.split(r'\s*(?:<=>|⇌|↔|⟶|→|->)\s*', text.strip())
    if len(sides) != 2: return None, 'unreadable_reaction'
    converted, warning = [], None
    for side in sides:
        parts = []
        for item in re.split(r'\s+\+\s+', side):
            formula, issue = species(item)
            if issue and not formula: return None, issue
            warning = warning or issue
            parts.append(r'\ce{' + formula + '}')
        converted.append(' + '.join(parts))
    arrow = r' \rightleftharpoons ' if re.search(r'<=>|⇌|↔', text) else r' \longrightarrow '
    return arrow.join(converted), warning


def tex_shape_issue(tex):
    depth = 0
    for match in re.finditer(r'(?<!\\)[{}]', tex):
        depth += 1 if match[0] == '{' else -1
        if depth < 0 or depth > 128: return True
    return depth != 0


def explicit_issues(text):
    issues = []
    for token in LATEX.split(text):
        if LATEX.fullmatch(token):
            if tex_shape_issue(token): issues.append(('invalid_latex', token))
            if r'\ce{' in token and '(I)' in token: issues.append(('ambiguous_liquid_state', token))
        elif re.search(r'(?<![A-Z\\])\$|\\[\[(]', token): issues.append(('invalid_latex', token))
    return issues


def normalize(text, chemistry=False):
    """Return selectable prose with explicit LaTeX plus unresolved issue codes."""
    issues = []
    chemistry = chemistry or bool(CHEM_CONTEXT.search(text))

    def plain(part):
        # Preserve suspicious reactions verbatim instead of repairing the chemistry.
        held = []
        def hold(value):
            held.append(value)
            return f'\x00{len(held)-1}\x00'
        def equation(match):
            tex, issue = reaction_tex(match[0])
            if issue:
                issues.append((issue, match[0]))
                if not tex: return hold(match[0])
            return hold('$' + tex + '$')
        part = REACTION.sub(equation, part)

        def molecule(match):
            original = match[0]
            token, suffix = original, ''
            while token.endswith(')') and token.count(')') > token.count('('):
                token, suffix = token[:-1], ')' + suffix
            value, issue = chemical_token(token)
            if chemistry and re.fullmatch(r'[A-Z][mn][+−⁺⁻-]', token): issue = 'ambiguous_generic_ion'
            if issue:
                issues.append((issue, original)); return original
            explicit = bool(re.search(r'[₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]|\d|\^|[+-]$', token))
            compound = len(re.findall(r'[A-Z]', token)) > 1
            if value and (explicit or (compound and chemistry)) and (chemistry or compound or re.search(r'[₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]', token)):
                return hold('$\\ce{' + value + '}$' + suffix)
            return original
        part = CANDIDATE.sub(molecule, part)
        if chemistry:
            part = re.sub(r'(?<!\w)e[⁻−-](?!\w)', lambda m: hold(r'$\ce{e-}$'), part)
        # Explicit indices/superscripts are recoverable; flattened "105" is not.
        part = re.sub(r'(?<!\w)([A-Za-z])([₀-₉]+)', lambda m: hold('$' + m[1] + '_{' + m[2].translate(SUB) + '}$'), part)
        part = re.sub(r'(?<!\w)([A-Za-z])([ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ]+)', lambda m: hold('$' + m[1] + '_{' + m[2].translate(SUB_LETTERS) + '}$'), part)
        part = re.sub(r'(?<!\w)([A-Za-z])_([A-Za-z0-9]+)', lambda m: hold('$' + m[1] + '_{' + m[2] + '}$'), part)
        part = re.sub(r'(?<!\w)(\d+(?:[,.]\d+)?)\s*[×·]\s*10(?:\^([+-]?\d+)|([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+))', lambda m: hold('$' + m[1].replace(',', '{,}') + r'\times10^{' + (m[2] or m[3].translate(SUP)) + '}$'), part)
        for match in re.finditer(r'\d+(?:[,.]\d+)?\s*×\s*10\d+', part): issues.append(('ambiguous_exponent', match[0]))
        units = r'(?:kg|mg|g|km|cm|mm|m|mL|L|mol|s|V|W|J|Hz|Pa|K)(?:[²³]|\^[23])?(?:/(?:mol|mL|L|s|cm|m)(?:[²³]|\^[23])?)?'
        def unit(match):
            value = match[1].replace(',', '{,}')
            unit = match[2].replace('²', '^2').replace('³', '^3')
            unit = re.sub(r'\^([23])', r'^{\1}', unit)
            return hold('$' + value + r'\,\mathrm{' + unit + '}$')
        part = re.sub(r'(?<![\w$])(\d+(?:[,.]\d+)?)\s+(' + units + r')(?![\w/])', unit, part)
        part = re.sub(r'(?<!\w)(\d+(?:[,.]\d+)?|[A-Za-z])([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)', lambda m: hold('$' + m[1].replace(',', '{,}') + '^{' + m[2].translate(SUP) + '}$'), part)
        part = re.sub(r'(?<!\w)(\d+(?:[,.]\d+)?)\s*%', lambda m: hold('$' + m[1].replace(',', '{,}') + r'\%$'), part)
        part = re.sub(r'\x00(\d+)\x00', lambda m: held[int(m[1])], part)
        return part

    tokens = LATEX.split(text)
    issues.extend(explicit_issues(text))
    result = ''.join(part if LATEX.fullmatch(part) else plain(part) for part in tokens)
    if '\ufffd' in result: issues.append(('replacement_character', '�'))
    return result, list(dict.fromkeys(issues))

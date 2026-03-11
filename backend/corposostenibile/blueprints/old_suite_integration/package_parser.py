"""
Package Name Parser per la vecchia suite CRM.

Formato pacchetti: "N/C+P-90gg-B", "N+C-90gg-A", "N-60gg-C", etc.
- Prima parte (prima del primo '-'): ruoli separati da '/' o '+'
  N = Nutrizione, C = Coach, P = Psicologia
- Seconda parte: durata in giorni (es. "90gg")
- Terza parte: tipologia (A, B, o C)
"""

import re


def parse_package_name(name: str) -> dict:
    """
    Parsa il nome pacchetto dalla vecchia suite.

    Returns:
        {
            'raw': str,           # nome originale
            'roles': {
                'nutrition': bool,
                'coach': bool,
                'psychology': bool
            },
            'duration_days': int, # 0 se non parsabile
            'code': str           # es. 'NC', 'NCP', 'N'
        }
    """
    result = {
        'raw': name or '',
        'roles': {'nutrition': True, 'coach': True, 'psychology': True},
        'duration_days': 0,
        'code': ''
    }

    if not name:
        return result

    parts = name.strip().split('-')

    # Parse ruoli dalla prima parte
    if parts:
        role_part = parts[0].strip().upper()
        role_letters = [r.strip() for r in re.split(r'[/+]', role_part) if r.strip()]

        if role_letters:
            has_n = 'N' in role_letters
            has_c = 'C' in role_letters
            has_p = 'P' in role_letters

            # Solo se abbiamo trovato almeno un ruolo valido
            if has_n or has_c or has_p:
                result['roles'] = {
                    'nutrition': has_n,
                    'coach': has_c,
                    'psychology': has_p,
                }
                code_parts = []
                if has_n:
                    code_parts.append('N')
                if has_c:
                    code_parts.append('C')
                if has_p:
                    code_parts.append('P')
                result['code'] = ''.join(code_parts)

    # Parse durata dalla seconda parte
    if len(parts) > 1:
        duration_part = parts[1].strip().lower()
        match = re.search(r'(\d+)', duration_part)
        if match:
            result['duration_days'] = int(match.group(1))

    return result

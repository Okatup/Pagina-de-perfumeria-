# scripts/utils.py

from unidecode import unidecode

# Normalizar perfume name y marca 
def normalize(text):
    """Normaliza un texto quitando tildes y convirtiendo a minúsculas"""
    if not isinstance(text, str):
        return ""
    return unidecode(text).lower().strip()

# Formatear texto para mostrar: reemplaza guiones y capitaliza (evitar repeticiones exactas al inicio)
def format_text(text):
    if not isinstance(text, str):
        return ""
    text = text.replace('-', ' ').title()

    # Evitar repeticiones exactas al inicio
    words = text.split()
    if len(words) > 1 and words[0] == words[1]:
        text = ' '.join(words[1:])
    return text


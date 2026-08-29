import unicodedata

def NFC(item: object) -> str:
    return unicodedata.normalize("NFC", str(item))

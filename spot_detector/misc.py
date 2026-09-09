import unicodedata
from pathlib import Path

def NFC(item: object) -> str:
    return unicodedata.normalize("NFC", str(item))

def canonical_path(path: Path | str) -> Path:
    return Path(NFC(Path(path).expanduser().resolve()))

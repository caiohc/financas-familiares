from datetime import datetime, timezone


def utcnow() -> datetime:
    """Agora em UTC, sem fuso (naive): o formato em que o SQLite grava e devolve datas."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

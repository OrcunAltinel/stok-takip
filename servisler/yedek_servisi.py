"""Veritabanı yedekleme — otomatik ve manuel."""

import shutil
from datetime import datetime
from pathlib import Path

from veritabani.baglanti import DB_YOL

_PROJE_DIZIN = Path(__file__).parent.parent
YEDEK_DIZIN = _PROJE_DIZIN / "yedekler"
MAX_YEDEK = 30


def yedek_al(etiket: str = "") -> Path:
    """Veritabanını yedekler, yol döner."""
    YEDEK_DIZIN.mkdir(exist_ok=True)
    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_adi = f"stok_takip_{zaman}{('_' + etiket) if etiket else ''}.db"
    hedef = YEDEK_DIZIN / dosya_adi
    shutil.copy2(DB_YOL, hedef)
    _eski_yedekleri_sil()
    return hedef


def otomatik_yedek_al() -> Path:
    return yedek_al()


def _eski_yedekleri_sil():
    """En yeni MAX_YEDEK yedek dışındakileri siler."""
    yedekler = sorted(YEDEK_DIZIN.glob("stok_takip_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for eski in yedekler[MAX_YEDEK:]:
        try:
            eski.unlink()
        except Exception:
            pass


def yedek_listesi() -> list[Path]:
    if not YEDEK_DIZIN.exists():
        return []
    return sorted(YEDEK_DIZIN.glob("stok_takip_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)

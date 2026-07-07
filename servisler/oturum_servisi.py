"""Oturum yönetimi — giriş hatırlama (oturum.json)."""

import json
from pathlib import Path

from veritabani.baglanti import get_session
from veritabani.modeller import Admin

_OTURUM_DOSYA = Path(__file__).parent.parent / "oturum.json"


def oturum_kaydet(admin_id: int) -> None:
    _OTURUM_DOSYA.write_text(json.dumps({"admin_id": admin_id}), encoding="utf-8")


def oturum_yukle() -> Admin | None:
    """Kayıtlı oturum varsa Admin döner, yoksa None."""
    if not _OTURUM_DOSYA.exists():
        return None
    try:
        veri = json.loads(_OTURUM_DOSYA.read_text(encoding="utf-8"))
        admin_id = veri.get("admin_id")
        if not admin_id:
            return None
        with get_session() as session:
            admin = session.query(Admin).filter_by(id=admin_id, aktif=True).first()
            if admin and not admin.ilk_giris:
                session.expunge(admin)
                return admin
    except Exception:
        pass
    oturum_temizle()
    return None


def oturum_temizle() -> None:
    if _OTURUM_DOSYA.exists():
        _OTURUM_DOSYA.unlink()

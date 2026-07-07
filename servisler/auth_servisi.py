"""Kimlik doğrulama ve parola yönetimi."""

import bcrypt

from veritabani.baglanti import get_session
from veritabani.modeller import Admin


def giris_yap(kullanici_adi: str, parola: str) -> Admin | None:
    """Doğru kimlik bilgileriyle Admin döner, yanlışsa None."""
    with get_session() as session:
        admin = session.query(Admin).filter_by(
            kullanici_adi=kullanici_adi, aktif=True
        ).first()
        if admin is None:
            return None
        if bcrypt.checkpw(parola.encode(), admin.parola_hash.encode()):
            session.expunge(admin)
            return admin
        return None


def parola_degistir(admin_id: int, yeni_parola: str) -> None:
    """Admin parolasını hash'leyerek günceller ve ilk_giris'i kapatır."""
    yeni_hash = bcrypt.hashpw(yeni_parola.encode(), bcrypt.gensalt()).decode()
    with get_session() as session:
        admin = session.query(Admin).filter_by(id=admin_id).first()
        admin.parola_hash = yeni_hash
        admin.ilk_giris = False


def mevcut_parola_dogru_mu(admin_id: int, parola: str) -> bool:
    with get_session() as session:
        admin = session.query(Admin).filter_by(id=admin_id).first()
        return bcrypt.checkpw(parola.encode(), admin.parola_hash.encode())

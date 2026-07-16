"""Şema migrasyonları — mevcut veriyi bozmadan tabloya sütun eklemek için.

Her migrasyon fonksiyonu tekrar çalıştırıldığında hata vermemeli
(sütun/indeks zaten varsa atlar).
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def urun_rapa_kdv_kolonlari_ekle(engine: Engine) -> None:
    """`urunler` tablosuna `rapa_kodu` ve `kdvli_fiyat` sütunlarını ekler."""
    with engine.begin() as conn:
        mevcut_sutunlar = {
            satir[1] for satir in conn.execute(text("PRAGMA table_info(urunler)"))
        }
        if "rapa_kodu" not in mevcut_sutunlar:
            conn.execute(text("ALTER TABLE urunler ADD COLUMN rapa_kodu TEXT"))
        if "kdvli_fiyat" not in mevcut_sutunlar:
            conn.execute(text("ALTER TABLE urunler ADD COLUMN kdvli_fiyat NUMERIC(12, 2)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_urunler_rapa_kodu ON urunler (rapa_kodu)"))


def musteri_borc_bakiye_kaldir(engine: Engine) -> None:
    """Borç/veresiye/bakiye mantığı kaldırıldı — `musteriler.borc` ve `bakiye` sütunlarını düşürür."""
    with engine.begin() as conn:
        mevcut_sutunlar = {
            satir[1] for satir in conn.execute(text("PRAGMA table_info(musteriler)"))
        }
        if "borc" in mevcut_sutunlar:
            conn.execute(text("ALTER TABLE musteriler DROP COLUMN borc"))
        if "bakiye" in mevcut_sutunlar:
            conn.execute(text("ALTER TABLE musteriler DROP COLUMN bakiye"))


def tum_migrasyonlari_calistir(engine: Engine) -> None:
    urun_rapa_kdv_kolonlari_ekle(engine)
    musteri_borc_bakiye_kaldir(engine)

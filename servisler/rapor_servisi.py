"""Rapor sorguları — tarih filtreli özet ve detay raporları."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func

from veritabani.baglanti import get_session
from veritabani.modeller import (
    Musteri, Odeme, SatisFisi, SatisKalemi, StokHareketi, Urun,
)


def satis_raporu(baslangic: datetime, bitis: datetime) -> list[dict]:
    """Fiş bazlı satış listesi."""
    with get_session() as session:
        fisler = (
            session.query(SatisFisi)
            .filter(
                SatisFisi.tarih >= baslangic,
                SatisFisi.tarih <= bitis,
                SatisFisi.durum == "TAMAMLANDI",
            )
            .order_by(SatisFisi.tarih)
            .all()
        )
        sonuc = []
        for f in fisler:
            musteri_adi = ""
            if f.musteri_id:
                m = session.query(Musteri).filter_by(id=f.musteri_id).first()
                if m:
                    musteri_adi = f"{m.ad} {m.soyad}"
            sonuc.append({
                "fis_no": f.fis_no,
                "tarih": f.tarih,
                "musteri_adi": musteri_adi,
                "ara_toplam": f.ara_toplam,
                "kdv_toplam": f.kdv_toplam,
                "genel_toplam": f.genel_toplam,
                "odeme_tipi": f.odeme_tipi,
            })
        return sonuc


def urun_bazli_satis(baslangic: datetime, bitis: datetime) -> list[dict]:
    """Ürün bazlı satış özeti (toplam adet ve ciro)."""
    with get_session() as session:
        from sqlalchemy import and_
        satirlar = (
            session.query(
                Urun.urun_kodu,
                Urun.urun_adi,
                func.sum(SatisKalemi.miktar).label("toplam_miktar"),
                func.sum(SatisKalemi.satir_toplam).label("toplam_tutar"),
            )
            .join(SatisKalemi, SatisKalemi.urun_id == Urun.id)
            .join(SatisFisi, SatisFisi.id == SatisKalemi.satis_fisi_id)
            .filter(
                SatisFisi.tarih >= baslangic,
                SatisFisi.tarih <= bitis,
                SatisFisi.durum == "TAMAMLANDI",
            )
            .group_by(Urun.id)
            .order_by(func.sum(SatisKalemi.satir_toplam).desc())
            .all()
        )
        return [
            {
                "urun_kodu": r.urun_kodu,
                "urun_adi": r.urun_adi,
                "toplam_miktar": r.toplam_miktar,
                "toplam_tutar": r.toplam_tutar,
            }
            for r in satirlar
        ]


def stok_hareket_raporu(baslangic: datetime, bitis: datetime) -> list[dict]:
    with get_session() as session:
        hareketler = (
            session.query(StokHareketi)
            .filter(
                StokHareketi.tarih >= baslangic,
                StokHareketi.tarih <= bitis,
            )
            .order_by(StokHareketi.tarih)
            .all()
        )
        sonuc = []
        for h in hareketler:
            urun = session.query(Urun).filter_by(id=h.urun_id).first()
            sonuc.append({
                "tarih": h.tarih,
                "urun_kodu": urun.urun_kodu if urun else "?",
                "urun_adi": urun.urun_adi if urun else "?",
                "hareket_tipi": h.hareket_tipi,
                "miktar": h.miktar,
                "birim_fiyat": h.birim_fiyat,
                "aciklama": h.aciklama or "",
            })
        return sonuc


def borclu_musteriler() -> list[dict]:
    with get_session() as session:
        musteriler = (
            session.query(Musteri)
            .filter(Musteri.aktif == True, Musteri.borc > 0)
            .order_by(Musteri.borc.desc())
            .all()
        )
        return [
            {
                "id": m.id,
                "musteri": f"{m.ad} {m.soyad}",
                "firma": m.firma_adi or "",
                "telefon": m.telefon or "",
                "borc": m.borc,
                "bakiye": m.bakiye,
            }
            for m in musteriler
        ]


def en_cok_satanlar(baslangic: datetime, bitis: datetime, limit: int = 20) -> list[dict]:
    return urun_bazli_satis(baslangic, bitis)[:limit]


def kar_raporu(baslangic: datetime, bitis: datetime) -> list[dict]:
    """Satış fiyatı − alış fiyatı bazlı yaklaşık kâr."""
    with get_session() as session:
        satirlar = (
            session.query(
                Urun.urun_kodu,
                Urun.urun_adi,
                func.sum(SatisKalemi.miktar).label("toplam_miktar"),
                func.sum(SatisKalemi.satir_toplam).label("ciro"),
                Urun.alis_fiyati,
            )
            .join(SatisKalemi, SatisKalemi.urun_id == Urun.id)
            .join(SatisFisi, SatisFisi.id == SatisKalemi.satis_fisi_id)
            .filter(
                SatisFisi.tarih >= baslangic,
                SatisFisi.tarih <= bitis,
                SatisFisi.durum == "TAMAMLANDI",
            )
            .group_by(Urun.id)
            .all()
        )
        sonuc = []
        for r in satirlar:
            maliyet = Decimal(str(r.toplam_miktar)) * Decimal(str(r.alis_fiyati))
            kar = Decimal(str(r.ciro)) - maliyet
            sonuc.append({
                "urun_kodu": r.urun_kodu,
                "urun_adi": r.urun_adi,
                "toplam_miktar": r.toplam_miktar,
                "ciro": r.ciro,
                "maliyet": maliyet,
                "kar": kar,
            })
        return sorted(sonuc, key=lambda x: x["kar"], reverse=True)


def dashboard_ozet() -> dict:
    """Ana panel için özet veriler."""
    with get_session() as session:
        from datetime import timedelta
        bugun_bas = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        bu_ay_bas = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        bugun_bit = datetime.now().replace(hour=23, minute=59, second=59)

        def satis_toplam(bas, bit):
            sonuc = session.query(func.sum(SatisFisi.genel_toplam)).filter(
                SatisFisi.tarih >= bas,
                SatisFisi.tarih <= bit,
                SatisFisi.durum == "TAMAMLANDI",
            ).scalar()
            return Decimal(str(sonuc)) if sonuc else Decimal("0.00")

        toplam_veresiye = session.query(func.sum(Musteri.borc)).filter(Musteri.aktif == True).scalar()
        toplam_bakiye = session.query(func.sum(Musteri.bakiye)).filter(Musteri.aktif == True).scalar()

        return {
            "bugun_satis": satis_toplam(bugun_bas, bugun_bit),
            "bu_ay_satis": satis_toplam(bu_ay_bas, bugun_bit),
            "toplam_veresiye": Decimal(str(toplam_veresiye)) if toplam_veresiye else Decimal("0.00"),
            "toplam_bakiye": Decimal(str(toplam_bakiye)) if toplam_bakiye else Decimal("0.00"),
        }

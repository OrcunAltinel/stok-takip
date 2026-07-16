"""Satış fiş oluşturma testleri."""

from decimal import Decimal
from datetime import datetime
import pytest

from veritabani.modeller import (
    Musteri, Odeme, SatisFisi, SatisKalemi, StokHareketi, Urun,
)


def _urun(session, kod="TST-01", stok=Decimal("20")) -> Urun:
    u = Urun(
        urun_kodu=kod, urun_adi=f"Ürün {kod}", birim="adet",
        alis_fiyati=Decimal("100.00"), satis_fiyati=Decimal("150.00"),
        kdv_orani=Decimal("20.00"), stok_miktari=stok,
        kritik_stok_seviyesi=Decimal("5.000"),
    )
    session.add(u)
    session.commit()
    return u


def _musteri(session) -> Musteri:
    m = Musteri(ad="Ali", soyad="Test")
    session.add(m)
    session.commit()
    return m


def test_nakit_satis_stok_dusuyor(session, admin):
    urun = _urun(session)
    miktar = Decimal("3")
    fiyat = Decimal("150.00")
    kdv = Decimal("20.00")
    toplam_kdvsiz = (miktar * fiyat).quantize(Decimal("0.01"))
    kdv_tutari = (toplam_kdvsiz * kdv / 100).quantize(Decimal("0.01"))

    fis = SatisFisi(
        fis_no="SF-2026-000001",
        tarih=datetime.now(),
        ara_toplam=toplam_kdvsiz,
        kdv_toplam=kdv_tutari,
        genel_toplam=toplam_kdvsiz + kdv_tutari,
        odeme_tipi="NAKIT",
        durum="TAMAMLANDI",
        admin_id=admin.id,
    )
    session.add(fis)
    session.flush()

    kalem = SatisKalemi(
        satis_fisi_id=fis.id, urun_id=urun.id, miktar=miktar,
        birim_fiyat=fiyat, kdv_orani=kdv,
        satir_toplam=toplam_kdvsiz + kdv_tutari,
    )
    session.add(kalem)
    urun.stok_miktari = Decimal(str(urun.stok_miktari)) - miktar
    hareket = StokHareketi(
        urun_id=urun.id, hareket_tipi="CIKIS", miktar=miktar,
        birim_fiyat=fiyat, satis_fisi_id=fis.id, admin_id=admin.id,
    )
    session.add(hareket)
    session.commit()

    guncel = session.query(Urun).filter_by(id=urun.id).first()
    assert Decimal(str(guncel.stok_miktari)) == Decimal("17.000")
    assert session.query(SatisKalemi).filter_by(satis_fisi_id=fis.id).count() == 1


def test_karma_satis_odeme_kayitlari(session, admin):
    m = _musteri(session)
    tutar = Decimal("540.00")
    fis = SatisFisi(
        fis_no="SF-2026-000002", tarih=datetime.now(),
        ara_toplam=Decimal("450.00"), kdv_toplam=Decimal("90.00"),
        genel_toplam=tutar, odeme_tipi="KARMA",
        durum="TAMAMLANDI", musteri_id=m.id, admin_id=admin.id,
    )
    session.add(fis)
    session.flush()
    session.add(Odeme(
        musteri_id=m.id, islem_tipi="SATIS_ODEME", tutar=Decimal("300.00"),
        odeme_araci="NAKIT", iliskili_fis_id=fis.id, admin_id=admin.id,
    ))
    session.add(Odeme(
        musteri_id=m.id, islem_tipi="SATIS_ODEME", tutar=Decimal("240.00"),
        odeme_araci="KART", iliskili_fis_id=fis.id, admin_id=admin.id,
    ))
    session.commit()

    odemeler = session.query(Odeme).filter_by(iliskili_fis_id=fis.id).all()
    assert sum(Decimal(str(o.tutar)) for o in odemeler) == tutar


def test_fis_no_format():
    yil = 2026
    sira = 42
    fis_no = f"SF-{yil}-{sira:06d}"
    assert fis_no == "SF-2026-000042"

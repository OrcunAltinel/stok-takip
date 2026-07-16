"""İade işlemleri testleri."""

from decimal import Decimal
from datetime import datetime
import pytest

from veritabani.modeller import (
    IadeFisi, IadeKalemi, Musteri, SatisFisi, StokHareketi, Urun,
)


def _hazirla(session, admin):
    urun = Urun(
        urun_kodu="IADE-TEST", urun_adi="İade Test Ürünü", birim="adet",
        alis_fiyati=Decimal("100.00"), satis_fiyati=Decimal("150.00"),
        kdv_orani=Decimal("20.00"), stok_miktari=Decimal("7.000"),
        kritik_stok_seviyesi=Decimal("5.000"),
    )
    m = Musteri(ad="İade", soyad="Müşteri")
    session.add_all([urun, m])
    session.flush()
    fis = SatisFisi(
        fis_no="SF-2026-000010", tarih=datetime.now(),
        ara_toplam=Decimal("250.00"), kdv_toplam=Decimal("50.00"),
        genel_toplam=Decimal("300.00"), odeme_tipi="NAKIT",
        durum="TAMAMLANDI", musteri_id=m.id, admin_id=admin.id,
    )
    session.add(fis)
    session.commit()
    return urun, m, fis


def test_iade_stok_artar(session, admin):
    urun, m, fis = _hazirla(session, admin)
    iade_miktar = Decimal("2")

    iade_fis = IadeFisi(
        iade_no="IF-2026-000001", orijinal_fis_id=fis.id, musteri_id=m.id,
        tarih=datetime.now(), toplam_tutar=Decimal("300.00"),
        iade_yontemi="NAKIT_ODE", admin_id=admin.id,
    )
    session.add(iade_fis)
    session.flush()
    session.add(IadeKalemi(
        iade_fisi_id=iade_fis.id, urun_id=urun.id, miktar=iade_miktar,
        birim_fiyat=Decimal("150.00"), satir_toplam=Decimal("300.00"),
    ))
    hareket = StokHareketi(
        urun_id=urun.id, hareket_tipi="IADE_GIRIS", miktar=iade_miktar,
        birim_fiyat=Decimal("150.00"), satis_fisi_id=fis.id, admin_id=admin.id,
    )
    session.add(hareket)
    urun.stok_miktari = Decimal(str(urun.stok_miktari)) + iade_miktar
    session.commit()

    guncel = session.query(Urun).filter_by(id=urun.id).first()
    assert Decimal(str(guncel.stok_miktari)) == Decimal("9.000")


@pytest.mark.parametrize("iade_yontemi", ["NAKIT_ODE", "KART_ODE", "CEK_ODE"])
def test_iade_yontemi_kaydediliyor(session, admin, iade_yontemi):
    urun, m, fis = _hazirla(session, admin)
    iade_fis = IadeFisi(
        iade_no=f"IF-2026-{iade_yontemi}", orijinal_fis_id=fis.id, musteri_id=m.id,
        tarih=datetime.now(), toplam_tutar=Decimal("150.00"),
        iade_yontemi=iade_yontemi, admin_id=admin.id,
    )
    session.add(iade_fis)
    session.commit()
    guncel = session.query(IadeFisi).filter_by(iade_no=iade_fis.iade_no).first()
    assert guncel.iade_yontemi == iade_yontemi

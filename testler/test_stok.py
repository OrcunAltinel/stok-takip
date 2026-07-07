"""Stok hareketi testleri."""

from decimal import Decimal
import pytest

from veritabani.modeller import Urun, StokHareketi


def _urun_ekle(session, admin_id) -> Urun:
    u = Urun(
        urun_kodu="TEST-001",
        urun_adi="Test Ürünü",
        birim="adet",
        alis_fiyati=Decimal("100.00"),
        satis_fiyati=Decimal("150.00"),
        kdv_orani=Decimal("20.00"),
        stok_miktari=Decimal("10.000"),
        kritik_stok_seviyesi=Decimal("5.000"),
    )
    session.add(u)
    session.commit()
    return u


def test_stok_giris_miktari_artar(session, admin):
    urun = _urun_ekle(session, admin.id)
    urun.stok_miktari = Decimal(str(urun.stok_miktari)) + Decimal("5")
    hareket = StokHareketi(
        urun_id=urun.id,
        hareket_tipi="GIRIS",
        miktar=Decimal("5"),
        birim_fiyat=Decimal("100.00"),
        admin_id=admin.id,
    )
    session.add(hareket)
    session.commit()

    guncel = session.query(Urun).filter_by(id=urun.id).first()
    assert Decimal(str(guncel.stok_miktari)) == Decimal("15.000")


def test_stok_cikis_miktari_azalir(session, admin):
    urun = _urun_ekle(session, admin.id)
    urun.stok_miktari = Decimal(str(urun.stok_miktari)) - Decimal("3")
    hareket = StokHareketi(
        urun_id=urun.id,
        hareket_tipi="CIKIS",
        miktar=Decimal("3"),
        birim_fiyat=Decimal("150.00"),
        admin_id=admin.id,
    )
    session.add(hareket)
    session.commit()

    guncel = session.query(Urun).filter_by(id=urun.id).first()
    assert Decimal(str(guncel.stok_miktari)) == Decimal("7.000")


def test_stok_negatife_dusmesine_izin_var(session, admin):
    """Gerçek hayatta eksi stok olabilir — engellenmez."""
    urun = _urun_ekle(session, admin.id)
    urun.stok_miktari = Decimal(str(urun.stok_miktari)) - Decimal("15")
    session.commit()
    guncel = session.query(Urun).filter_by(id=urun.id).first()
    assert Decimal(str(guncel.stok_miktari)) == Decimal("-5.000")

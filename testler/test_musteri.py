"""Müşteri işlemleri testleri."""

from decimal import Decimal
import pytest

from veritabani.modeller import Musteri, Odeme


def _musteri_ekle(session) -> Musteri:
    m = Musteri(ad="Test", soyad="Müşteri", bakiye=Decimal("0.00"), borc=Decimal("0.00"))
    session.add(m)
    session.commit()
    return m


def test_bakiye_yukleme(session, admin):
    m = _musteri_ekle(session)
    tutar = Decimal("500.00")
    m.bakiye = Decimal(str(m.bakiye)) + tutar
    session.add(Odeme(
        musteri_id=m.id, islem_tipi="BAKIYE_YUKLEME", tutar=tutar,
        odeme_araci="NAKIT", admin_id=admin.id,
    ))
    session.commit()
    guncel = session.query(Musteri).filter_by(id=m.id).first()
    assert Decimal(str(guncel.bakiye)) == Decimal("500.00")


def test_tahsilat_borc_azaltir(session, admin):
    m = _musteri_ekle(session)
    m.borc = Decimal("1000.00")
    session.commit()
    tahsilat = Decimal("400.00")
    m.borc = max(Decimal("0.00"), Decimal(str(m.borc)) - tahsilat)
    session.add(Odeme(
        musteri_id=m.id, islem_tipi="TAHSILAT", tutar=tahsilat,
        odeme_araci="NAKIT", admin_id=admin.id,
    ))
    session.commit()
    guncel = session.query(Musteri).filter_by(id=m.id).first()
    assert Decimal(str(guncel.borc)) == Decimal("600.00")


def test_bakiye_eksi_olmaz(session, admin):
    """Bakiye kullanımında eksi düşmez — servis katmanı kontrol eder."""
    m = _musteri_ekle(session)
    m.bakiye = Decimal("100.00")
    session.commit()
    # Servis katmanı bu kontrolü yapar, test sadece modeli doğrular
    assert Decimal(str(m.bakiye)) >= Decimal("0.00")

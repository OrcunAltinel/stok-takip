"""Müşteri ve KARMA ödeme kırılımı testleri."""

from decimal import Decimal
import pytest

from veritabani.modeller import Musteri, Odeme, SatisFisi


def _musteri_ekle(session) -> Musteri:
    m = Musteri(ad="Test", soyad="Müşteri")
    session.add(m)
    session.commit()
    return m


def test_musteri_olusturma(session):
    m = _musteri_ekle(session)
    guncel = session.query(Musteri).filter_by(id=m.id).first()
    assert guncel.ad == "Test"
    assert guncel.soyad == "Müşteri"
    assert guncel.aktif is True


def test_karma_odeme_kirilimi_toplami_genel_toplama_esit(session, admin):
    m = _musteri_ekle(session)
    genel_toplam = Decimal("540.00")
    fis = SatisFisi(
        fis_no="SF-2026-000001", odeme_tipi="KARMA",
        ara_toplam=Decimal("450.00"), kdv_toplam=Decimal("90.00"),
        genel_toplam=genel_toplam, durum="TAMAMLANDI",
        musteri_id=m.id, admin_id=admin.id,
    )
    session.add(fis)
    session.flush()

    kirilim = [
        ("NAKIT", Decimal("200.00")),
        ("KART", Decimal("240.00")),
        ("CEK", Decimal("100.00")),
    ]
    for arac, tutar in kirilim:
        session.add(Odeme(
            musteri_id=m.id, islem_tipi="SATIS_ODEME", tutar=tutar,
            odeme_araci=arac, iliskili_fis_id=fis.id, admin_id=admin.id,
        ))
    session.commit()

    odemeler = session.query(Odeme).filter_by(iliskili_fis_id=fis.id).all()
    toplam = sum(Decimal(str(o.tutar)) for o in odemeler)
    assert toplam == genel_toplam

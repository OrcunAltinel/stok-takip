"""Müşteri CRUD, bakiye yükleme ve tahsilat işlemleri."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from veritabani.baglanti import get_session
from veritabani.modeller import Musteri, Odeme


def musteri_listesi(sadece_aktif: bool = True) -> list[Musteri]:
    with get_session() as session:
        q = session.query(Musteri)
        if sadece_aktif:
            q = q.filter(Musteri.aktif == True)
        liste = q.order_by(Musteri.ad, Musteri.soyad).all()
        for m in liste:
            session.expunge(m)
        return liste


def musteri_ara(arama: str) -> list[Musteri]:
    with get_session() as session:
        from sqlalchemy import or_
        filtre = f"%{arama}%"
        sonuclar = (
            session.query(Musteri)
            .filter(
                Musteri.aktif == True,
                or_(
                    Musteri.ad.ilike(filtre),
                    Musteri.soyad.ilike(filtre),
                    Musteri.telefon.ilike(filtre),
                    Musteri.firma_adi.ilike(filtre),
                    Musteri.id.ilike(filtre) if arama.isdigit() else False,
                ),
            )
            .order_by(Musteri.ad)
            .limit(50)
            .all()
        )
        for m in sonuclar:
            session.expunge(m)
        return sonuclar


def musteri_bul_id(musteri_id: int) -> Optional[Musteri]:
    with get_session() as session:
        m = session.query(Musteri).filter_by(id=musteri_id).first()
        if m:
            session.expunge(m)
        return m


def musteri_ekle(
    ad: str,
    soyad: str,
    firma_adi: str = None,
    telefon: str = None,
    adres: str = None,
    bolge: str = None,
    ilce: str = None,
    vergi_no: str = None,
    notlar: str = None,
) -> Musteri:
    with get_session() as session:
        m = Musteri(
            ad=ad.strip(),
            soyad=soyad.strip(),
            firma_adi=firma_adi,
            telefon=telefon,
            adres=adres,
            bolge=bolge,
            ilce=ilce,
            vergi_no=vergi_no,
            notlar=notlar,
        )
        session.add(m)
        session.flush()
        session.expunge(m)
        return m


def musteri_guncelle(musteri_id: int, **kwargs) -> Musteri:
    with get_session() as session:
        m = session.query(Musteri).filter_by(id=musteri_id).first()
        for alan, deger in kwargs.items():
            setattr(m, alan, deger)
        session.flush()
        session.expunge(m)
        return m


def musteri_pasife_al(musteri_id: int) -> None:
    with get_session() as session:
        m = session.query(Musteri).filter_by(id=musteri_id).first()
        m.aktif = False
        m.silinme_tarihi = datetime.now()


def bakiye_yukle(musteri_id: int, tutar: Decimal, odeme_araci: str, admin_id: int, aciklama: str = "") -> None:
    """Ödeme alır. Varsa önce borcu kapatır, kalan bakiye olarak eklenir."""
    if tutar <= 0:
        raise ValueError("Tutar sıfırdan büyük olmalıdır.")
    with get_session() as session:
        m = session.query(Musteri).filter_by(id=musteri_id).first()
        tutar = Decimal(str(tutar))
        borc = Decimal(str(m.borc))
        kalan = tutar

        if borc > 0:
            borc_odeme = min(kalan, borc)
            m.borc = borc - borc_odeme
            kalan -= borc_odeme
            session.add(Odeme(
                musteri_id=musteri_id,
                islem_tipi="TAHSILAT",
                tutar=borc_odeme,
                odeme_araci=odeme_araci,
                tarih=datetime.now(),
                aciklama=aciklama or "Borç kapatma",
                admin_id=admin_id,
            ))

        if kalan > 0:
            m.bakiye = Decimal(str(m.bakiye)) + kalan
            session.add(Odeme(
                musteri_id=musteri_id,
                islem_tipi="BAKIYE_YUKLEME",
                tutar=kalan,
                odeme_araci=odeme_araci,
                tarih=datetime.now(),
                aciklama=aciklama or "Bakiye yükleme",
                admin_id=admin_id,
            ))


def tahsilat_al(musteri_id: int, tutar: Decimal, odeme_araci: str, admin_id: int, aciklama: str = "") -> None:
    """Müşterinin borcunu düşürür ve TAHSILAT ödeme kaydı oluşturur."""
    if tutar <= 0:
        raise ValueError("Tutar sıfırdan büyük olmalıdır.")
    with get_session() as session:
        m = session.query(Musteri).filter_by(id=musteri_id).first()
        m.borc = max(Decimal("0.00"), Decimal(str(m.borc)) - tutar)
        odeme = Odeme(
            musteri_id=musteri_id,
            islem_tipi="TAHSILAT",
            tutar=tutar,
            odeme_araci=odeme_araci,
            tarih=datetime.now(),
            aciklama=aciklama or "Borç tahsilatı",
            admin_id=admin_id,
        )
        session.add(odeme)


def cari_hareketler(musteri_id: int, baslangic=None, bitis=None) -> list[dict]:
    """Müşterinin tüm cari hareketlerini kronolojik sıraya döner."""
    with get_session() as session:
        from veritabani.modeller import SatisFisi

        satirlar = []

        # Tüm satış fişleri (nakit, kart, bakiye, veresiye hepsi görünsün)
        fis_q = session.query(SatisFisi).filter(
            SatisFisi.musteri_id == musteri_id,
        )
        if baslangic:
            fis_q = fis_q.filter(SatisFisi.tarih >= baslangic)
        if bitis:
            fis_q = fis_q.filter(SatisFisi.tarih <= bitis)

        _ODEME_ETIKET = {
            "NAKIT": "Nakit", "KART": "Kart",
            "BAKIYE": "Bakiyeden", "VERESIYE": "Veresiye", "KARMA": "Karma",
        }
        for fis in fis_q.all():
            borc = Decimal(str(fis.genel_toplam)) if fis.odeme_tipi == "VERESIYE" else Decimal("0")
            odeme_str = _ODEME_ETIKET.get(fis.odeme_tipi, fis.odeme_tipi)
            satirlar.append({
                "tarih": fis.tarih,
                "tip": "SATIS",
                "display_tip": f"Satış ({odeme_str})",
                "belge": fis.fis_no,
                "borc": borc,
                "tahsilat": Decimal("0"),
                "fis_id": fis.id,
            })

        # Finansal hareketler: tahsilat, bakiye yükleme, iade alacak
        odeme_q = session.query(Odeme).filter(
            Odeme.musteri_id == musteri_id,
            Odeme.islem_tipi.in_(["TAHSILAT", "BAKIYE_YUKLEME", "IADE_ALACAK"]),
        )
        if baslangic:
            odeme_q = odeme_q.filter(Odeme.tarih >= baslangic)
        if bitis:
            odeme_q = odeme_q.filter(Odeme.tarih <= bitis)

        _TIP_ETIKET = {
            "TAHSILAT": "Borç Tahsilatı",
            "BAKIYE_YUKLEME": "Bakiye Yükleme",
            "IADE_ALACAK": "İade Alacağı",
        }
        for o in odeme_q.all():
            satirlar.append({
                "tarih": o.tarih,
                "tip": o.islem_tipi,
                "display_tip": _TIP_ETIKET.get(o.islem_tipi, o.islem_tipi),
                "belge": o.aciklama or "",
                "borc": Decimal("0"),
                "tahsilat": Decimal(str(o.tutar)),
                "fis_id": None,
            })

        satirlar.sort(key=lambda x: x["tarih"])
        return satirlar

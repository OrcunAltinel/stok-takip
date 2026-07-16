"""Müşteri CRUD ve satış/iade geçmişi sorguları."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from veritabani.baglanti import get_session
from veritabani.modeller import IadeFisi, Musteri, SatisFisi


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


_ODEME_ETIKET = {"NAKIT": "Nakit", "KART": "Kart", "CEK": "Çek", "KARMA": "Karma"}
_IADE_YONTEMI_ETIKET = {"NAKIT_ODE": "Nakit", "KART_ODE": "Kart", "CEK_ODE": "Çek"}


def cari_hareketler(musteri_id: int, baslangic=None, bitis=None) -> list[dict]:
    """Müşterinin satış ve iade geçmişini kronolojik sırayla döner."""
    with get_session() as session:
        satirlar = []

        fis_q = session.query(SatisFisi).filter(SatisFisi.musteri_id == musteri_id)
        if baslangic:
            fis_q = fis_q.filter(SatisFisi.tarih >= baslangic)
        if bitis:
            fis_q = fis_q.filter(SatisFisi.tarih <= bitis)
        for fis in fis_q.all():
            odeme_str = _ODEME_ETIKET.get(fis.odeme_tipi, fis.odeme_tipi)
            satirlar.append({
                "tarih": fis.tarih,
                "tip": "SATIS",
                "display_tip": f"Satış ({odeme_str})",
                "belge": fis.fis_no,
                "tutar": Decimal(str(fis.genel_toplam)),
                "fis_id": fis.id,
            })

        iade_q = session.query(IadeFisi).filter(IadeFisi.musteri_id == musteri_id)
        if baslangic:
            iade_q = iade_q.filter(IadeFisi.tarih >= baslangic)
        if bitis:
            iade_q = iade_q.filter(IadeFisi.tarih <= bitis)
        for iade in iade_q.all():
            yontem_str = _IADE_YONTEMI_ETIKET.get(iade.iade_yontemi, iade.iade_yontemi)
            satirlar.append({
                "tarih": iade.tarih,
                "tip": "IADE",
                "display_tip": f"İade ({yontem_str})",
                "belge": iade.iade_no,
                "tutar": -Decimal(str(iade.toplam_tutar)),
                "fis_id": None,
            })

        satirlar.sort(key=lambda x: x["tarih"])
        return satirlar

"""Ürün CRUD işlemleri."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from veritabani.baglanti import get_session
from veritabani.modeller import Urun


def urun_listesi(sadece_aktif: bool = True) -> list[Urun]:
    with get_session() as session:
        q = session.query(Urun)
        if sadece_aktif:
            q = q.filter(Urun.aktif == True)
        urunler = q.order_by(Urun.urun_kodu).all()
        for u in urunler:
            session.expunge(u)
        return urunler


def urun_ara(arama: str, mod: str = "iceride") -> list[Urun]:
    """mod: 'iceride' veya 'baslar'"""
    with get_session() as session:
        q = session.query(Urun).filter(Urun.aktif == True)
        if arama:
            if mod == "baslar":
                filtre = f"{arama}%"
            else:
                filtre = f"%{arama}%"
            from sqlalchemy import or_
            q = q.filter(
                or_(
                    Urun.urun_kodu.ilike(filtre),
                    Urun.urun_adi.ilike(filtre),
                    Urun.oem_no.ilike(filtre),
                )
            )
        sonuclar = q.order_by(Urun.urun_kodu).limit(200).all()
        for u in sonuclar:
            session.expunge(u)
        return sonuclar


def urun_bul_id(urun_id: int) -> Optional[Urun]:
    with get_session() as session:
        u = session.query(Urun).filter_by(id=urun_id).first()
        if u:
            session.expunge(u)
        return u


def urun_bul_kod(kod: str) -> Optional[Urun]:
    with get_session() as session:
        u = session.query(Urun).filter_by(urun_kodu=kod, aktif=True).first()
        if u:
            session.expunge(u)
        return u


def urun_ekle(
    urun_kodu: str,
    urun_adi: str,
    oem_no: str = None,
    marka: str = None,
    kategori: str = None,
    birim: str = "adet",
    alis_fiyati: Decimal = Decimal("0.00"),
    satis_fiyati: Decimal = Decimal("0.00"),
    kdv_orani: Decimal = Decimal("20.00"),
    kritik_stok_seviyesi: Decimal = Decimal("5.000"),
    raf_adresi: str = None,
) -> Urun:
    with get_session() as session:
        urun = Urun(
            urun_kodu=urun_kodu.strip().upper(),
            urun_adi=urun_adi.strip(),
            oem_no=oem_no,
            marka=marka,
            kategori=kategori,
            birim=birim,
            alis_fiyati=alis_fiyati,
            satis_fiyati=satis_fiyati,
            kdv_orani=kdv_orani,
            kritik_stok_seviyesi=kritik_stok_seviyesi,
            raf_adresi=raf_adresi,
        )
        session.add(urun)
        session.flush()
        session.expunge(urun)
        return urun


def urun_guncelle(urun_id: int, **kwargs) -> Urun:
    with get_session() as session:
        urun = session.query(Urun).filter_by(id=urun_id).first()
        for alan, deger in kwargs.items():
            setattr(urun, alan, deger)
        session.flush()
        session.expunge(urun)
        return urun


def urun_pasife_al(urun_id: int) -> None:
    with get_session() as session:
        urun = session.query(Urun).filter_by(id=urun_id).first()
        urun.aktif = False
        urun.silinme_tarihi = datetime.now()


def kritik_stok_urunleri() -> list[Urun]:
    with get_session() as session:
        from sqlalchemy import cast, Numeric
        sonuclar = (
            session.query(Urun)
            .filter(
                Urun.aktif == True,
                Urun.stok_miktari <= Urun.kritik_stok_seviyesi,
            )
            .order_by(Urun.stok_miktari)
            .all()
        )
        for u in sonuclar:
            session.expunge(u)
        return sonuclar

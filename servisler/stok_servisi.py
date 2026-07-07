"""Stok hareketi işlemleri — giriş, çıkış, iade, sayım."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from veritabani.baglanti import get_session
from veritabani.modeller import StokHareketi, Urun


def stok_girisi_kaydet(
    urun_id: int,
    miktar: Decimal,
    birim_fiyat: Decimal,
    admin_id: int,
    tedarikci_id: Optional[int] = None,
    aciklama: str = "",
) -> StokHareketi:
    """Stok girişi kaydeder ve ürünün stok_miktarını artırır."""
    with get_session() as session:
        urun = session.query(Urun).filter_by(id=urun_id).first()
        if urun is None:
            raise ValueError(f"Ürün bulunamadı: id={urun_id}")
        urun.stok_miktari = Decimal(str(urun.stok_miktari)) + miktar
        urun.alis_fiyati = birim_fiyat

        hareket = StokHareketi(
            urun_id=urun_id,
            hareket_tipi="GIRIS",
            miktar=miktar,
            birim_fiyat=birim_fiyat,
            tedarikci_id=tedarikci_id,
            aciklama=aciklama,
            tarih=datetime.now(),
            admin_id=admin_id,
        )
        session.add(hareket)
        session.flush()
        session.expunge(hareket)
        return hareket


def sayim_duzeltme(
    urun_id: int,
    yeni_miktar: Decimal,
    admin_id: int,
    aciklama: str = "",
) -> StokHareketi:
    with get_session() as session:
        urun = session.query(Urun).filter_by(id=urun_id).first()
        fark = yeni_miktar - Decimal(str(urun.stok_miktari))
        urun.stok_miktari = yeni_miktar
        hareket = StokHareketi(
            urun_id=urun_id,
            hareket_tipi="SAYIM_DUZELTME",
            miktar=abs(fark),
            birim_fiyat=Decimal("0.00"),
            aciklama=aciklama or f"Sayım düzeltme: fark {fark:+.3f}",
            tarih=datetime.now(),
            admin_id=admin_id,
        )
        session.add(hareket)
        session.flush()
        session.expunge(hareket)
        return hareket


def urun_stok_gecmisi(urun_id: int) -> list[dict]:
    """Ürünün tüm stok hareketlerini döner."""
    with get_session() as session:
        hareketler = (
            session.query(StokHareketi)
            .filter_by(urun_id=urun_id)
            .order_by(StokHareketi.tarih.desc())
            .all()
        )
        sonuc = []
        for h in hareketler:
            from veritabani.modeller import SatisFisi, Tedarikci, Admin
            tedarikci_adi = ""
            if h.tedarikci_id:
                t = session.query(Tedarikci).filter_by(id=h.tedarikci_id).first()
                if t:
                    tedarikci_adi = t.firma_adi
            fis_no = ""
            if h.satis_fisi_id:
                f = session.query(SatisFisi).filter_by(id=h.satis_fisi_id).first()
                if f:
                    fis_no = f.fis_no
            admin_adi = ""
            a = session.query(Admin).filter_by(id=h.admin_id).first()
            if a:
                admin_adi = a.ad_soyad
            sonuc.append({
                "id": h.id,
                "tarih": h.tarih,
                "hareket_tipi": h.hareket_tipi,
                "miktar": h.miktar,
                "birim_fiyat": h.birim_fiyat,
                "tedarikci": tedarikci_adi,
                "fis_no": fis_no,
                "aciklama": h.aciklama or "",
                "admin": admin_adi,
            })
        return sonuc

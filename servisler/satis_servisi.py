"""Satış fiş oluşturma — tek transaction, tüm ödeme tipleri."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from veritabani.baglanti import get_session
from veritabani.modeller import (
    Musteri, Odeme, SatisFisi, SatisKalemi, StokHareketi, Urun,
)


def _sonraki_fis_no(session, yil: int) -> str:
    son = (
        session.query(SatisFisi)
        .filter(SatisFisi.fis_no.like(f"SF-{yil}-%"))
        .order_by(SatisFisi.id.desc())
        .first()
    )
    sira = int(son.fis_no.split("-")[2]) + 1 if son else 1
    return f"SF-{yil}-{sira:06d}"


def fis_olustur(
    admin_id: int,
    kalemler: list[dict],
    odeme_tipi: str,
    musteri_id: Optional[int] = None,
    karma_odemeler: Optional[list[dict]] = None,
    aciklama: str = "",
) -> SatisFisi:
    """
    kalemler: [{"urun_id": int, "miktar": Decimal, "birim_fiyat": Decimal, "kdv_orani": Decimal}]
    karma_odemeler: [{"tutar": Decimal, "odeme_araci": str}]  — sadece KARMA tipinde
    """
    if not kalemler:
        raise ValueError("En az bir satış kalemi gereklidir.")

    with get_session() as session:
        yil = datetime.now().year
        fis_no = _sonraki_fis_no(session, yil)

        ara_toplam = Decimal("0.00")
        kdv_toplam = Decimal("0.00")

        satis_kalemleri_obj = []
        for k in kalemler:
            miktar = Decimal(str(k["miktar"]))
            fiyat = Decimal(str(k["birim_fiyat"]))
            kdv = Decimal(str(k["kdv_orani"]))
            satis_tutari = (miktar * fiyat).quantize(Decimal("0.01"))
            kdv_tutari = (satis_tutari * kdv / Decimal("100")).quantize(Decimal("0.01"))
            ara_toplam += satis_tutari
            kdv_toplam += kdv_tutari
            satis_kalemleri_obj.append({
                "urun_id": k["urun_id"],
                "miktar": miktar,
                "birim_fiyat": fiyat,
                "kdv_orani": kdv,
                "satir_toplam": satis_tutari + kdv_tutari,
            })

        genel_toplam = ara_toplam + kdv_toplam

        fis = SatisFisi(
            fis_no=fis_no,
            musteri_id=musteri_id,
            tarih=datetime.now(),
            ara_toplam=ara_toplam,
            kdv_toplam=kdv_toplam,
            genel_toplam=genel_toplam,
            odeme_tipi=odeme_tipi,
            durum="TAMAMLANDI",
            aciklama=aciklama,
            admin_id=admin_id,
        )
        session.add(fis)
        session.flush()

        # Satış kalemleri + stok hareketleri
        for k in satis_kalemleri_obj:
            kalem = SatisKalemi(
                satis_fisi_id=fis.id,
                urun_id=k["urun_id"],
                miktar=k["miktar"],
                birim_fiyat=k["birim_fiyat"],
                kdv_orani=k["kdv_orani"],
                satir_toplam=k["satir_toplam"],
            )
            session.add(kalem)

            urun = session.query(Urun).filter_by(id=k["urun_id"]).first()
            urun.stok_miktari = Decimal(str(urun.stok_miktari)) - k["miktar"]

            hareket = StokHareketi(
                urun_id=k["urun_id"],
                hareket_tipi="CIKIS",
                miktar=k["miktar"],
                birim_fiyat=k["birim_fiyat"],
                satis_fisi_id=fis.id,
                tarih=fis.tarih,
                admin_id=admin_id,
            )
            session.add(hareket)

        # KARMA ödeme — her araç için ayrı Odeme kaydı (nakit/kart/çek kırılımı)
        if odeme_tipi == "KARMA" and karma_odemeler:
            for ko in karma_odemeler:
                k_tutar = Decimal(str(ko["tutar"]))
                if k_tutar <= 0:
                    continue
                session.add(Odeme(
                    musteri_id=musteri_id,
                    islem_tipi="SATIS_ODEME",
                    tutar=k_tutar,
                    odeme_araci=ko["odeme_araci"],
                    iliskili_fis_id=fis.id,
                    tarih=fis.tarih,
                    aciklama=f"KARMA ödeme: {fis_no}",
                    admin_id=admin_id,
                ))

        session.flush()
        session.expunge(fis)
        return fis


def fis_iptal(fis_id: int, admin_id: int) -> None:
    """Satış fişini iptal eder ve stokları geri yükler (yeni IADE_GIRIS hareketi olmaz, iade ile yapılır)."""
    with get_session() as session:
        fis = session.query(SatisFisi).filter_by(id=fis_id).first()
        if fis is None:
            raise ValueError("Fiş bulunamadı.")
        if fis.durum == "IPTAL":
            raise ValueError("Fiş zaten iptal edilmiş.")
        fis.durum = "IPTAL"


def tum_fis_numaralari() -> list[str]:
    """Otomatik tamamlama için tüm fiş numaralarını döner (en yeni önce)."""
    with get_session() as session:
        return [
            f[0] for f in
            session.query(SatisFisi.fis_no).order_by(SatisFisi.fis_no.desc()).all()
        ]


def fis_bul_no(fis_no: str) -> Optional[SatisFisi]:
    with get_session() as session:
        fis = session.query(SatisFisi).filter_by(fis_no=fis_no).first()
        if fis:
            session.expunge(fis)
        return fis


def fis_detay(fis_id: int) -> dict:
    """Fiş + kalemleri + müşteri bilgisini dict olarak döner."""
    with get_session() as session:
        fis = session.query(SatisFisi).filter_by(id=fis_id).first()
        if not fis:
            return {}
        kalemler = []
        for k in fis.kalemler:
            urun = session.query(Urun).filter_by(id=k.urun_id).first()
            kalemler.append({
                "urun_kodu": urun.urun_kodu if urun else "?",
                "urun_adi": urun.urun_adi if urun else "?",
                "miktar": k.miktar,
                "birim_fiyat": k.birim_fiyat,
                "kdv_orani": k.kdv_orani,
                "satir_toplam": k.satir_toplam,
                "urun_id": k.urun_id,
            })
        musteri_adi = ""
        if fis.musteri_id:
            m = session.query(Musteri).filter_by(id=fis.musteri_id).first()
            if m:
                musteri_adi = f"{m.ad} {m.soyad}"
                if m.firma_adi:
                    musteri_adi += f" ({m.firma_adi})"
        return {
            "id": fis.id,
            "fis_no": fis.fis_no,
            "tarih": fis.tarih,
            "musteri_adi": musteri_adi,
            "musteri_id": fis.musteri_id,
            "ara_toplam": fis.ara_toplam,
            "kdv_toplam": fis.kdv_toplam,
            "genel_toplam": fis.genel_toplam,
            "odeme_tipi": fis.odeme_tipi,
            "durum": fis.durum,
            "aciklama": fis.aciklama,
            "kalemler": kalemler,
        }


def son_fisler(limit: int = 10) -> list[dict]:
    with get_session() as session:
        fisler = (
            session.query(SatisFisi)
            .order_by(SatisFisi.tarih.desc())
            .limit(limit)
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
                "genel_toplam": f.genel_toplam,
                "odeme_tipi": f.odeme_tipi,
                "durum": f.durum,
            })
        return sonuc

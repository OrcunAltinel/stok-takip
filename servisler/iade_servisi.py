"""İade fişi oluşturma — kısmi iade, stok geri girişi, cari kayıt."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from veritabani.baglanti import get_session
from veritabani.modeller import (
    IadeFisi, IadeKalemi, Musteri, Odeme, SatisFisi, SatisKalemi,
    StokHareketi, Urun,
)


def _sonraki_iade_no(session, yil: int) -> str:
    son = (
        session.query(IadeFisi)
        .filter(IadeFisi.iade_no.like(f"IF-{yil}-%"))
        .order_by(IadeFisi.id.desc())
        .first()
    )
    sira = int(son.iade_no.split("-")[2]) + 1 if son else 1
    return f"IF-{yil}-{sira:06d}"


def iade_olustur(
    admin_id: int,
    orijinal_fis_id: int,
    iade_kalemleri_liste: list[dict],
    iade_yontemi: str,
    aciklama: str = "",
) -> IadeFisi:
    """
    iade_kalemleri_liste: [{"urun_id": int, "miktar": Decimal, "birim_fiyat": Decimal}]
    iade_yontemi: NAKIT_ODE | BAKIYEYE_EKLE | BORCTAN_DUS
    """
    if not iade_kalemleri_liste:
        raise ValueError("En az bir iade kalemi gereklidir.")

    with get_session() as session:
        orijinal = session.query(SatisFisi).filter_by(id=orijinal_fis_id).first()
        if orijinal is None:
            raise ValueError("Orijinal fiş bulunamadı.")

        yil = datetime.now().year
        iade_no = _sonraki_iade_no(session, yil)

        toplam_tutar = Decimal("0.00")
        kalem_obj_list = []
        for ik in iade_kalemleri_liste:
            miktar = Decimal(str(ik["miktar"]))
            fiyat = Decimal(str(ik["birim_fiyat"]))
            satir_toplam = (miktar * fiyat).quantize(Decimal("0.01"))
            toplam_tutar += satir_toplam
            kalem_obj_list.append({
                "urun_id": ik["urun_id"],
                "miktar": miktar,
                "birim_fiyat": fiyat,
                "satir_toplam": satir_toplam,
            })

        fis = IadeFisi(
            iade_no=iade_no,
            orijinal_fis_id=orijinal_fis_id,
            musteri_id=orijinal.musteri_id,
            tarih=datetime.now(),
            toplam_tutar=toplam_tutar,
            iade_yontemi=iade_yontemi,
            aciklama=aciklama,
            admin_id=admin_id,
        )
        session.add(fis)
        session.flush()

        for k in kalem_obj_list:
            kalem = IadeKalemi(
                iade_fisi_id=fis.id,
                urun_id=k["urun_id"],
                miktar=k["miktar"],
                birim_fiyat=k["birim_fiyat"],
                satir_toplam=k["satir_toplam"],
            )
            session.add(kalem)

            urun = session.query(Urun).filter_by(id=k["urun_id"]).first()
            urun.stok_miktari = Decimal(str(urun.stok_miktari)) + k["miktar"]

            hareket = StokHareketi(
                urun_id=k["urun_id"],
                hareket_tipi="IADE_GIRIS",
                miktar=k["miktar"],
                birim_fiyat=k["birim_fiyat"],
                satis_fisi_id=orijinal_fis_id,
                tarih=fis.tarih,
                aciklama=f"İade: {iade_no}",
                admin_id=admin_id,
            )
            session.add(hareket)

        if orijinal.musteri_id:
            musteri = session.query(Musteri).filter_by(id=orijinal.musteri_id).first()
            if iade_yontemi == "BAKIYEYE_EKLE":
                musteri.bakiye = Decimal(str(musteri.bakiye)) + toplam_tutar
                islem_tipi = "IADE_ALACAK"
            elif iade_yontemi == "BORCTAN_DUS":
                musteri.borc = max(Decimal("0.00"), Decimal(str(musteri.borc)) - toplam_tutar)
                islem_tipi = "IADE_ALACAK"
            else:
                islem_tipi = "IADE_ALACAK"

            session.add(Odeme(
                musteri_id=orijinal.musteri_id,
                islem_tipi=islem_tipi,
                tutar=toplam_tutar,
                odeme_araci=iade_yontemi,
                iliskili_fis_id=orijinal_fis_id,
                tarih=fis.tarih,
                aciklama=f"İade: {iade_no} — {iade_yontemi}",
                admin_id=admin_id,
            ))

        session.flush()
        session.expunge(fis)
        return fis


def fis_kalemleri_getir(fis_no: str) -> Optional[dict]:
    """Fiş no ile fişi ve kalemlerini döner (iade için)."""
    with get_session() as session:
        fis = session.query(SatisFisi).filter_by(fis_no=fis_no).first()
        if not fis:
            return None
        kalemler = []
        for k in fis.kalemler:
            urun = session.query(Urun).filter_by(id=k.urun_id).first()
            kalemler.append({
                "urun_id": k.urun_id,
                "urun_kodu": urun.urun_kodu if urun else "?",
                "urun_adi": urun.urun_adi if urun else "?",
                "miktar": k.miktar,
                "birim_fiyat": k.birim_fiyat,
                "satir_toplam": k.satir_toplam,
            })
        musteri_adi = ""
        if fis.musteri_id:
            m = session.query(Musteri).filter_by(id=fis.musteri_id).first()
            if m:
                musteri_adi = f"{m.ad} {m.soyad}"
        return {
            "id": fis.id,
            "fis_no": fis.fis_no,
            "tarih": fis.tarih,
            "musteri_id": fis.musteri_id,
            "musteri_adi": musteri_adi,
            "genel_toplam": fis.genel_toplam,
            "kalemler": kalemler,
        }

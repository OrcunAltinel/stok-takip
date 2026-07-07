"""A4 satış fişi PDF üretimi — reportlab."""

import io
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)


_PARA_STILI = ParagraphStyle(
    "para",
    fontName="Helvetica",
    fontSize=9,
    leading=12,
)
_BASLIK_STILI = ParagraphStyle(
    "baslik",
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    alignment=1,
)
_ORTA_STILI = ParagraphStyle(
    "orta",
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    alignment=1,
)


def fis_pdf_olustur(fis_detay: dict, firma_ayarlari: dict) -> bytes:
    """
    fis_detay: satis_servisi.fis_detay() çıktısı
    firma_ayarlari: {"firma_adi": ..., "adres": ..., "telefon": ...}
    Dönen bytes: PDF içeriği
    """
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    elemanlar = []

    # Firma başlığı
    firma_adi = firma_ayarlari.get("firma_adi") or "Oto Yedek Parça"
    elemanlar.append(Paragraph(firma_adi, _BASLIK_STILI))
    if firma_ayarlari.get("adres"):
        elemanlar.append(Paragraph(firma_ayarlari["adres"], _ORTA_STILI))
    if firma_ayarlari.get("telefon"):
        elemanlar.append(Paragraph(f"Tel: {firma_ayarlari['telefon']}", _ORTA_STILI))
    elemanlar.append(Spacer(1, 0.4 * cm))
    elemanlar.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elemanlar.append(Spacer(1, 0.3 * cm))

    # Fiş bilgileri
    from yardimcilar.formatlayici import tarih_formatla
    bilgi_data = [
        ["Fiş No:", fis_detay["fis_no"], "Tarih:", tarih_formatla(fis_detay["tarih"])],
        ["Müşteri:", fis_detay.get("musteri_adi") or "Perakende", "Durum:", fis_detay["durum"]],
        ["Ödeme:", fis_detay["odeme_tipi"], "", ""],
    ]
    bilgi_tablo = Table(bilgi_data, colWidths=[3 * cm, 7 * cm, 3 * cm, 4 * cm])
    bilgi_tablo.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elemanlar.append(bilgi_tablo)
    elemanlar.append(Spacer(1, 0.4 * cm))
    elemanlar.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elemanlar.append(Spacer(1, 0.3 * cm))

    # Kalemler tablosu
    kalem_sutunlari = ["Ürün Kodu", "Ürün Adı", "Miktar", "Birim Fiyat", "KDV%", "Satır Toplam"]
    kalem_data = [kalem_sutunlari]
    from yardimcilar.formatlayici import miktar_formatla, para_formatla
    for k in fis_detay["kalemler"]:
        kalem_data.append([
            k["urun_kodu"],
            k["urun_adi"],
            miktar_formatla(k["miktar"]),
            para_formatla(k["birim_fiyat"]),
            f"%{k['kdv_orani']}",
            para_formatla(k["satir_toplam"]),
        ])

    kalem_tablo = Table(
        kalem_data,
        colWidths=[3 * cm, 6.5 * cm, 2 * cm, 3 * cm, 1.5 * cm, 3 * cm],
    )
    kalem_tablo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elemanlar.append(kalem_tablo)
    elemanlar.append(Spacer(1, 0.4 * cm))

    # Toplamlar
    toplam_data = [
        ["", "Ara Toplam:", para_formatla(fis_detay["ara_toplam"])],
        ["", "KDV Toplamı:", para_formatla(fis_detay["kdv_toplam"])],
        ["", "GENEL TOPLAM:", para_formatla(fis_detay["genel_toplam"])],
    ]
    toplam_tablo = Table(toplam_data, colWidths=[10 * cm, 4 * cm, 3 * cm])
    toplam_tablo.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (1, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, 2), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (1, 2), (-1, 2), 0.5, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elemanlar.append(toplam_tablo)

    if fis_detay.get("aciklama"):
        elemanlar.append(Spacer(1, 0.3 * cm))
        elemanlar.append(Paragraph(f"Not: {fis_detay['aciklama']}", _PARA_STILI))

    elemanlar.append(Spacer(1, 0.6 * cm))
    elemanlar.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elemanlar.append(Spacer(1, 0.2 * cm))
    elemanlar.append(Paragraph("Teşekkür ederiz.", _ORTA_STILI))

    doc.build(elemanlar)
    return tampon.getvalue()


def fis_pdf_kaydet(fis_detay: dict, firma_ayarlari: dict, kayit_yolu: Path) -> None:
    icerik = fis_pdf_olustur(fis_detay, firma_ayarlari)
    kayit_yolu.write_bytes(icerik)

"""Para ve tarih formatlama yardımcıları."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def para_formatla(tutar) -> str:
    """Decimal veya sayısal değeri Türk para formatına çevirir: 1.457.536,00 ₺"""
    if tutar is None:
        return "0,00 ₺"
    d = Decimal(str(tutar)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tam, ondalik = str(abs(d)).split(".")
    gruplar = []
    while len(tam) > 3:
        gruplar.insert(0, tam[-3:])
        tam = tam[:-3]
    gruplar.insert(0, tam)
    formatted = ".".join(gruplar) + "," + ondalik + " ₺"
    return ("-" + formatted) if d < 0 else formatted


def tarih_formatla(dt) -> str:
    """datetime → GG.AA.YYYY SS:DD"""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%d.%m.%Y %H:%M")


def tarih_kisa_formatla(dt) -> str:
    """datetime → GG.AA.YYYY"""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%d.%m.%Y")


def miktar_formatla(miktar) -> str:
    """Stok miktarını formatlar; tam sayıysa ondalık göstermez."""
    if miktar is None:
        return "0"
    d = Decimal(str(miktar))
    if d == d.to_integral_value():
        return str(int(d))
    return str(d.normalize())

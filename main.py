"""Uygulama giriş noktası."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from veritabani.baglanti import veritabani_olustur
from veritabani.modeller import Admin, FirmaAyarlari
from veritabani.baglanti import get_session


def main():
    veritabani_olustur()

    app = QApplication(sys.argv)
    app.setApplicationName("Stok Takip")
    app.setOrganizationName("OtoYedekParca")

    # Temayı firma ayarlarından oku
    with get_session() as session:
        ayarlar = session.query(FirmaAyarlari).filter_by(id=1).first()
        tema_adi = ayarlar.tema if ayarlar else "koyu"

    from arayuz.tema import tema_al
    app.setStyleSheet(tema_al(tema_adi))

    _baslat(app, tema_adi)
    sys.exit(app.exec())


def _baslat(app: QApplication, tema_adi: str):
    from arayuz.giris_ekrani import GirisEkrani

    giris = GirisEkrani(lambda admin: _giris_basarili(app, admin, tema_adi))
    giris.resize(500, 400)
    giris.setWindowTitle("Giriş — Stok Takip")
    giris.show()
    app._giris_ekrani = giris  # referansı koru


def _giris_basarili(app: QApplication, admin: Admin, tema_adi: str):
    from arayuz.ana_pencere import AnaPencere

    pencere = AnaPencere(admin)
    pencere.show()
    app._giris_ekrani.close()
    app._ana_pencere = pencere  # referansı koru


if __name__ == "__main__":
    main()

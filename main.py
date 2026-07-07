"""Uygulama giriş noktası."""

import sys

from PySide6.QtWidgets import QApplication

from veritabani.baglanti import get_session, veritabani_olustur
from veritabani.modeller import Admin, FirmaAyarlari


def main():
    veritabani_olustur()

    app = QApplication(sys.argv)
    app.setApplicationName("Stok Takip")
    app.setOrganizationName("OtoYedekParca")

    with get_session() as session:
        ayarlar = session.query(FirmaAyarlari).filter_by(id=1).first()
        tema_adi = ayarlar.tema if ayarlar else "koyu"

    from arayuz.tema import tema_al
    app.setStyleSheet(tema_al(tema_adi))

    # Kayıtlı oturum varsa giriş ekranını atla
    from servisler.oturum_servisi import oturum_yukle
    kayitli_admin = oturum_yukle()
    if kayitli_admin:
        _ana_pencereyi_ac(app, kayitli_admin)
    else:
        _giris_ekranini_ac(app, tema_adi)

    sys.exit(app.exec())


def _giris_ekranini_ac(app: QApplication, tema_adi: str):
    from arayuz.giris_ekrani import GirisEkrani

    giris = GirisEkrani(lambda admin: _giris_basarili(app, admin, tema_adi))
    giris.resize(500, 400)
    giris.setWindowTitle("Giriş — Stok Takip")
    giris.show()
    app._giris_ekrani = giris


def _giris_basarili(app: QApplication, admin: Admin, tema_adi: str):
    from servisler.oturum_servisi import oturum_kaydet
    oturum_kaydet(admin.id)
    _ana_pencereyi_ac(app, admin)
    if hasattr(app, "_giris_ekrani"):
        app._giris_ekrani.close()


def _ana_pencereyi_ac(app: QApplication, admin: Admin):
    from arayuz.ana_pencere import AnaPencere

    def cikis_yap_cb():
        from servisler.oturum_servisi import oturum_temizle
        oturum_temizle()
        app._ana_pencere.close()
        _giris_ekranini_ac(app, "koyu")

    pencere = AnaPencere(admin, cikis_yap_cb=cikis_yap_cb)
    pencere.show()
    app._ana_pencere = pencere


if __name__ == "__main__":
    main()

"""Ana pencere — sol menü navigasyonu ve QStackedWidget sayfa yönetimi."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCloseEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QSizePolicy, QStackedWidget,
    QVBoxLayout, QWidget,
)

from servisler import yedek_servisi
from veritabani.modeller import Admin


class AnaPencere(QMainWindow):
    def __init__(self, admin: Admin, cikis_yap_cb=None):
        super().__init__()
        self.admin = admin
        self._cikis_yap_cb = cikis_yap_cb
        self.setWindowTitle("Stok Takip — Oto Yedek Parça Yönetim Sistemi")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 640)
        self._sayfalar: dict[str, QWidget] = {}
        self._menu_butonlari: list[QPushButton] = []
        self._kur()

    def _kur(self):
        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana = QHBoxLayout(merkez)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        # Sol panel
        sol = QFrame()
        sol.setObjectName("sol_panel")
        sol.setFixedWidth(210)
        sol_layout = QVBoxLayout(sol)
        sol_layout.setContentsMargins(8, 16, 8, 16)
        sol_layout.setSpacing(4)

        logo = QLabel("⚙ Stok Takip")
        logo.setObjectName("baslik")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        logo.setFont(f)
        logo.setContentsMargins(12, 0, 0, 0)
        sol_layout.addWidget(logo)

        admin_label = QLabel(f"  {self.admin.ad_soyad}")
        admin_label.setObjectName("alt_baslik")
        sol_layout.addWidget(admin_label)
        sol_layout.addSpacing(16)

        menu_items = [
            ("Ana Panel", "ana_panel"),
            ("Ürünler / Stok", "urunler"),
            ("Stok Girişi", "stok_giris"),
            ("Satış", "satis"),
            ("Müşteriler", "musteriler"),
            ("İade", "iade"),
            ("Raporlar", "raporlar"),
            ("Ayarlar", "ayarlar"),
        ]
        for etiket, sayfa_adi in menu_items:
            btn = QPushButton(etiket)
            btn.setObjectName("menu_btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, s=sayfa_adi: self._sayfaya_git(s))
            sol_layout.addWidget(btn)
            self._menu_butonlari.append((sayfa_adi, btn))

        sol_layout.addStretch()

        if self._cikis_yap_cb:
            cikis_btn = QPushButton("Çıkış Yap")
            cikis_btn.setObjectName("cikis_btn")
            cikis_btn.clicked.connect(self._cikis_yap)
            sol_layout.addWidget(cikis_btn)

        # İçerik alanı
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        ana.addWidget(sol)
        ana.addWidget(self.stack)

        self.statusBar().showMessage(f"Giriş: {self.admin.kullanici_adi}")
        self._sayfaya_git("ana_panel")

    def _sayfa_yukle(self, sayfa_adi: str) -> QWidget:
        if sayfa_adi in self._sayfalar:
            return self._sayfalar[sayfa_adi]

        widget = self._sayfa_olustur(sayfa_adi)
        self.stack.addWidget(widget)
        self._sayfalar[sayfa_adi] = widget
        return widget

    def _sayfa_olustur(self, sayfa_adi: str) -> QWidget:
        if sayfa_adi == "ana_panel":
            from arayuz.ana_panel import AnaPanelEkrani
            return AnaPanelEkrani(self.admin, self._sayfaya_git)
        if sayfa_adi == "urunler":
            from arayuz.urunler_ekrani import UrunlerEkrani
            return UrunlerEkrani(self.admin)
        if sayfa_adi == "stok_giris":
            from arayuz.stok_giris_ekrani import StokGirisEkrani
            return StokGirisEkrani(self.admin)
        if sayfa_adi == "satis":
            from arayuz.satis_ekrani import SatisEkrani
            return SatisEkrani(self.admin)
        if sayfa_adi == "musteriler":
            from arayuz.musteriler_ekrani import MusterilerEkrani
            return MusterilerEkrani(self.admin)
        if sayfa_adi == "iade":
            from arayuz.iade_ekrani import IadeEkrani
            return IadeEkrani(self.admin)
        if sayfa_adi == "raporlar":
            from arayuz.raporlar_ekrani import RaporlarEkrani
            return RaporlarEkrani(self.admin)
        if sayfa_adi == "ayarlar":
            from arayuz.ayarlar_ekrani import AyarlarEkrani
            return AyarlarEkrani(self.admin)
        yer_tutucu = QLabel(f"{sayfa_adi} — yapım aşamasında")
        yer_tutucu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return yer_tutucu

    def _sayfaya_git(self, sayfa_adi: str):
        for ad, btn in self._menu_butonlari:
            btn.setChecked(ad == sayfa_adi)

        widget = self._sayfa_yukle(sayfa_adi)
        self.stack.setCurrentWidget(widget)

        if hasattr(widget, "yenile"):
            widget.yenile()

    def _cikis_yap(self):
        if self._cikis_yap_cb:
            self._cikis_yap_cb()

    def closeEvent(self, event: QCloseEvent):
        try:
            yedek_servisi.otomatik_yedek_al()
        except Exception:
            pass
        super().closeEvent(event)

"""Ana panel (Dashboard) — KPI kartları, kritik stok, son satışlar."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from servisler import rapor_servisi, urun_servisi, satis_servisi
from veritabani.modeller import Admin
from yardimcilar.formatlayici import miktar_formatla, para_formatla, tarih_formatla


class KpiKart(QFrame):
    def __init__(self, etiket: str, renk: str = "#89b4fa"):
        super().__init__()
        self.setObjectName("kpi_kart")
        self.setMinimumWidth(200)
        self.setMinimumHeight(90)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self.deger_label = QLabel("—")
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        self.deger_label.setFont(f)
        self.deger_label.setStyleSheet(f"color: {renk};")
        self.etiket_label = QLabel(etiket)
        self.etiket_label.setObjectName("alt_baslik")
        layout.addWidget(self.deger_label)
        layout.addWidget(self.etiket_label)

    def guncelle(self, deger: str):
        self.deger_label.setText(deger)


class AnaPanelEkrani(QWidget):
    def __init__(self, admin: Admin, sayfa_git_cb=None):
        super().__init__()
        self.admin = admin
        self.sayfa_git_cb = sayfa_git_cb
        self._kur()
        self.yenile()

        # Her 5 dakikada bir yenile
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.yenile)
        self._timer.start(5 * 60 * 1000)

    def _kur(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(20, 16, 20, 16)
        ana.setSpacing(16)

        baslik = QLabel("Ana Panel")
        baslik.setObjectName("baslik")
        ana.addWidget(baslik)

        # KPI kartları
        kpi_satir = QHBoxLayout()
        self.kpi_bugun = KpiKart("Bugün Satış", "#a6e3a1")
        self.kpi_ay = KpiKart("Bu Ay Satış", "#89b4fa")
        self.kpi_veresiye = KpiKart("Toplam Veresiye", "#f38ba8")
        self.kpi_bakiye = KpiKart("Toplam Müşteri Bakiyesi", "#fab387")
        for kpi in [self.kpi_bugun, self.kpi_ay, self.kpi_veresiye, self.kpi_bakiye]:
            kpi.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            kpi_satir.addWidget(kpi)
        ana.addLayout(kpi_satir)

        # Alt bölüm: kritik stok + son satışlar
        alt = QHBoxLayout()

        # Kritik stok
        kritik_grup = QGroupBox("Kritik Stok Altındaki Ürünler")
        kritik_layout = QVBoxLayout(kritik_grup)
        self.kritik_tablo = QTableWidget(0, 4)
        self.kritik_tablo.setHorizontalHeaderLabels(["Kod", "Ürün Adı", "Stok", "Kritik Seviye"])
        self.kritik_tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.kritik_tablo.horizontalHeader().setStretchLastSection(True)
        self.kritik_tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.kritik_tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        kritik_layout.addWidget(self.kritik_tablo)
        kritik_grup.setMinimumWidth(380)
        alt.addWidget(kritik_grup, 1)

        # Son satışlar
        satis_grup = QGroupBox("Son 10 Satış")
        satis_layout = QVBoxLayout(satis_grup)
        self.satis_tablo = QTableWidget(0, 5)
        self.satis_tablo.setHorizontalHeaderLabels(["Fiş No", "Tarih", "Müşteri", "Toplam", "Ödeme"])
        self.satis_tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.satis_tablo.horizontalHeader().setStretchLastSection(True)
        self.satis_tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        satis_layout.addWidget(self.satis_tablo)
        alt.addWidget(satis_grup, 2)

        ana.addLayout(alt, 1)

        # Hızlı erişim butonları
        hizli = QGroupBox("Hızlı Erişim")
        hizli_layout = QHBoxLayout(hizli)
        butonlar = [
            ("+ Yeni Satış", "satis", "btn_basari"),
            ("Stok Girişi", "stok_giris", ""),
            ("Müşteri Ara", "musteriler", ""),
            ("Raporlar", "raporlar", ""),
        ]
        for etiket, sayfa, obj_name in butonlar:
            btn = QPushButton(etiket)
            if obj_name:
                btn.setObjectName(obj_name)
            if self.sayfa_git_cb:
                btn.clicked.connect(lambda _, s=sayfa: self.sayfa_git_cb(s))
            hizli_layout.addWidget(btn)
        hizli_layout.addStretch()
        ana.addWidget(hizli)

    def yenile(self):
        try:
            ozet = rapor_servisi.dashboard_ozet()
            self.kpi_bugun.guncelle(para_formatla(ozet["bugun_satis"]))
            self.kpi_ay.guncelle(para_formatla(ozet["bu_ay_satis"]))
            self.kpi_veresiye.guncelle(para_formatla(ozet["toplam_veresiye"]))
            self.kpi_bakiye.guncelle(para_formatla(ozet["toplam_bakiye"]))
        except Exception:
            pass

        try:
            kritikler = urun_servisi.kritik_stok_urunleri()
            self.kritik_tablo.setRowCount(len(kritikler))
            from decimal import Decimal
            from PySide6.QtGui import QColor
            for i, u in enumerate(kritikler):
                self.kritik_tablo.setItem(i, 0, QTableWidgetItem(u.urun_kodu))
                self.kritik_tablo.setItem(i, 1, QTableWidgetItem(u.urun_adi))
                stok_item = QTableWidgetItem(miktar_formatla(u.stok_miktari))
                stok = Decimal(str(u.stok_miktari))
                stok_item.setForeground(QColor("#f38ba8") if stok <= 0 else QColor("#fab387"))
                self.kritik_tablo.setItem(i, 2, stok_item)
                self.kritik_tablo.setItem(i, 3, QTableWidgetItem(miktar_formatla(u.kritik_stok_seviyesi)))
        except Exception:
            pass

        try:
            son_satislar = satis_servisi.son_fisler(10)
            self.satis_tablo.setRowCount(len(son_satislar))
            from PySide6.QtGui import QColor
            for i, f in enumerate(son_satislar):
                self.satis_tablo.setItem(i, 0, QTableWidgetItem(f["fis_no"]))
                self.satis_tablo.setItem(i, 1, QTableWidgetItem(tarih_formatla(f["tarih"])))
                self.satis_tablo.setItem(i, 2, QTableWidgetItem(f["musteri_adi"] or "Perakende"))
                toplam_item = QTableWidgetItem(para_formatla(f["genel_toplam"]))
                self.satis_tablo.setItem(i, 3, toplam_item)
                self.satis_tablo.setItem(i, 4, QTableWidgetItem(f["odeme_tipi"]))
                if f["durum"] == "IPTAL":
                    for col in range(5):
                        item = self.satis_tablo.item(i, col)
                        if item:
                            item.setForeground(QColor("#6c7086"))
        except Exception:
            pass

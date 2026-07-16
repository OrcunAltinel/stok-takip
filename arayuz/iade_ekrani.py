"""İade ekranı — fiş no ile arama, kısmi iade, yöntem seçimi."""

from decimal import Decimal

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from servisler import iade_servisi, satis_servisi
from veritabani.modeller import Admin
from yardimcilar.formatlayici import miktar_formatla, para_formatla, tarih_formatla


class IadeEkrani(QWidget):
    def __init__(self, admin: Admin):
        super().__init__()
        self.admin = admin
        self._fis_detay = None
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        baslik = QLabel("İade")
        baslik.setObjectName("baslik")
        layout.addWidget(baslik)

        # Fiş arama
        arama_grup = QGroupBox("Orijinal Fiş")
        a_layout = QHBoxLayout(arama_grup)
        self.fis_no_edit = QLineEdit()
        self.fis_no_edit.setPlaceholderText("Fiş no girin (örn: SF-2026-000001) — Tab ile tamamlar")
        self.fis_no_edit.returnPressed.connect(self._fis_ara)
        self._fis_no_tamamlayici = QCompleter()
        self._fis_no_tamamlayici.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._fis_no_tamamlayici.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
        self.fis_no_edit.setCompleter(self._fis_no_tamamlayici)
        ara_btn = QPushButton("Fişi Getir")
        ara_btn.clicked.connect(self._fis_ara)
        self.fis_bilgi = QLabel("")
        self.fis_bilgi.setObjectName("alt_baslik")
        a_layout.addWidget(QLabel("Fiş No:"))
        a_layout.addWidget(self.fis_no_edit, 1)
        a_layout.addWidget(ara_btn)
        a_layout.addWidget(self.fis_bilgi)
        layout.addWidget(arama_grup)

        # Kalemler tablosu (iade miktarı girilebilir)
        self.kalem_tablo = QTableWidget(0, 5)
        self.kalem_tablo.setHorizontalHeaderLabels(
            ["Ürün Kodu", "Ürün Adı", "Satılan Mkt.", "Birim Fiyat", "İade Miktarı"]
        )
        self.kalem_tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.kalem_tablo.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.kalem_tablo, 1)

        # İade yöntemi + toplam
        alt_grup = QGroupBox("İade Ayarları")
        alt_layout = QHBoxLayout(alt_grup)
        self.iade_yontemi = QComboBox()
        self.iade_yontemi.addItems(["NAKIT_ODE", "KART_ODE", "CEK_ODE"])
        self.aciklama_edit = QLineEdit()
        self.aciklama_edit.setPlaceholderText("Açıklama...")
        self.iade_toplam_label = QLabel("İade Tutarı: —")
        self.kaydet_btn = QPushButton("İadeyi Kaydet")
        self.kaydet_btn.setObjectName("btn_basari")
        self.kaydet_btn.setEnabled(False)
        self.kaydet_btn.clicked.connect(self._kaydet)
        alt_layout.addWidget(QLabel("İade Yöntemi:"))
        alt_layout.addWidget(self.iade_yontemi)
        alt_layout.addWidget(QLabel("Açıklama:"))
        alt_layout.addWidget(self.aciklama_edit, 1)
        alt_layout.addStretch()
        alt_layout.addWidget(self.iade_toplam_label)
        alt_layout.addWidget(self.kaydet_btn)
        layout.addWidget(alt_grup)

    def yenile(self):
        self.fis_no_edit.clear()
        self.fis_bilgi.setText("")
        self.kalem_tablo.setRowCount(0)
        self._fis_detay = None
        self.kaydet_btn.setEnabled(False)
        self._fis_no_tamamlayici.setModel(QStringListModel(satis_servisi.tum_fis_numaralari()))

    def _fis_ara(self):
        fis_no = self.fis_no_edit.text().strip().upper()
        if not fis_no:
            QMessageBox.warning(self, "Uyarı", "Fiş no girin.")
            return
        detay = iade_servisi.fis_kalemleri_getir(fis_no)
        if not detay:
            QMessageBox.warning(self, "Bulunamadı", f"{fis_no} numaralı fiş bulunamadı.")
            return
        self._fis_detay = detay
        self.fis_bilgi.setText(
            f"{tarih_formatla(detay['tarih'])} | {detay.get('musteri_adi') or 'Perakende'} | "
            f"Toplam: {para_formatla(detay['genel_toplam'])}"
        )
        self._kalemleri_yukle(detay["kalemler"])
        self.kaydet_btn.setEnabled(True)

    def _kalemleri_yukle(self, kalemler: list[dict]):
        self.kalem_tablo.setRowCount(len(kalemler))
        for i, k in enumerate(kalemler):
            self.kalem_tablo.setItem(i, 0, QTableWidgetItem(k["urun_kodu"]))
            self.kalem_tablo.setItem(i, 1, QTableWidgetItem(k["urun_adi"]))
            self.kalem_tablo.setItem(i, 2, QTableWidgetItem(miktar_formatla(k["miktar"])))
            self.kalem_tablo.setItem(i, 3, QTableWidgetItem(para_formatla(k["birim_fiyat"])))
            miktar_edit = QLineEdit(miktar_formatla(k["miktar"]))
            miktar_edit.textChanged.connect(self._toplami_guncelle)
            self.kalem_tablo.setCellWidget(i, 4, miktar_edit)
        self._toplami_guncelle()

    def _toplami_guncelle(self):
        if not self._fis_detay:
            return
        toplam = Decimal("0.00")
        for i, k in enumerate(self._fis_detay["kalemler"]):
            widget = self.kalem_tablo.cellWidget(i, 4)
            if widget:
                try:
                    miktar = Decimal(widget.text().replace(",", "."))
                except Exception:
                    miktar = Decimal("0")
                toplam += miktar * Decimal(str(k["birim_fiyat"]))
        self.iade_toplam_label.setText(f"İade Tutarı: {para_formatla(toplam)}")

    def _kaydet(self):
        if not self._fis_detay:
            return
        iade_kalemleri = []
        for i, k in enumerate(self._fis_detay["kalemler"]):
            widget = self.kalem_tablo.cellWidget(i, 4)
            try:
                miktar = Decimal(widget.text().replace(",", "."))
            except Exception:
                miktar = Decimal("0")
            if miktar > 0:
                max_miktar = Decimal(str(k["miktar"]))
                if miktar > max_miktar:
                    QMessageBox.warning(self, "Hata",
                        f"{k['urun_kodu']}: İade miktarı satılan miktardan fazla olamaz.")
                    return
                iade_kalemleri.append({
                    "urun_id": k["urun_id"],
                    "miktar": miktar,
                    "birim_fiyat": k["birim_fiyat"],
                })
        if not iade_kalemleri:
            QMessageBox.warning(self, "Uyarı", "En az bir ürün için iade miktarı girin.")
            return
        try:
            fis = iade_servisi.iade_olustur(
                admin_id=self.admin.id,
                orijinal_fis_id=self._fis_detay["id"],
                iade_kalemleri_liste=iade_kalemleri,
                iade_yontemi=self.iade_yontemi.currentText(),
                aciklama=self.aciklama_edit.text(),
            )
            QMessageBox.information(self, "Başarılı", f"İade kaydedildi: {fis.iade_no}")
            self.yenile()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

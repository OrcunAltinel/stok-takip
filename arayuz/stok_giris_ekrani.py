"""Stok girişi ekranı — tedarikçi seç, ürün/miktar/fiyat gir, kaydet."""

from decimal import Decimal

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from arayuz.bilesenler.para_girisi import ParaGirisi
from servisler import stok_servisi, urun_servisi
from veritabani.baglanti import get_session
from veritabani.modeller import Admin, Tedarikci
from yardimcilar.formatlayici import miktar_formatla, para_formatla


class StokGirisEkrani(QWidget):
    def __init__(self, admin: Admin):
        super().__init__()
        self.admin = admin
        self._satirlar: list[dict] = []
        self._kur()
        self.yenile()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        baslik = QLabel("Stok Girişi")
        baslik.setObjectName("baslik")
        layout.addWidget(baslik)

        # Tedarikçi seçimi
        ted_grup = QGroupBox("Tedarikçi")
        ted_layout = QHBoxLayout(ted_grup)
        self.tedarikci_combo = QComboBox()
        self.tedarikci_combo.setMinimumWidth(280)
        self.yeni_tedarikci_btn = QPushButton("+ Tedarikçi Ekle")
        self.yeni_tedarikci_btn.clicked.connect(self._tedarikci_ekle)
        ted_layout.addWidget(QLabel("Tedarikçi:"))
        ted_layout.addWidget(self.tedarikci_combo, 1)
        ted_layout.addWidget(self.yeni_tedarikci_btn)
        layout.addWidget(ted_grup)

        # Ürün ekleme satırı
        ekle_grup = QGroupBox("Ürün Ekle")
        ekle_layout = QHBoxLayout(ekle_grup)

        self.urun_arama = QLineEdit()
        self.urun_arama.setPlaceholderText("Ürün kodu, adı veya RAPA kodu...")
        self.urun_arama.textChanged.connect(self._urun_ara)
        self.urun_sonuc = QComboBox()
        self.urun_sonuc.setMinimumWidth(200)

        self.miktar_edit = QLineEdit("1")
        self.miktar_edit.setFixedWidth(70)
        self.alis_fiyat_edit = ParaGirisi()
        self.alis_fiyat_edit.setFixedWidth(110)
        self.aciklama_edit = QLineEdit()
        self.aciklama_edit.setPlaceholderText("Açıklama (opsiyonel)")

        ekle_btn = QPushButton("Listeye Ekle")
        ekle_btn.clicked.connect(self._satira_ekle)

        ekle_layout.addWidget(QLabel("Ürün:"))
        ekle_layout.addWidget(self.urun_arama)
        ekle_layout.addWidget(self.urun_sonuc, 1)
        ekle_layout.addWidget(QLabel("Miktar:"))
        ekle_layout.addWidget(self.miktar_edit)
        ekle_layout.addWidget(QLabel("Alış:"))
        ekle_layout.addWidget(self.alis_fiyat_edit)
        ekle_layout.addWidget(self.aciklama_edit)
        ekle_layout.addWidget(ekle_btn)
        layout.addWidget(ekle_grup)

        # Liste tablosu
        self.tablo = QTableWidget(0, 5)
        self.tablo.setHorizontalHeaderLabels(["Ürün Kodu", "Ürün Adı", "Miktar", "Alış Fiyatı", "Açıklama"])
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.tablo, 1)

        # Alt butonlar
        alt = QHBoxLayout()
        self.satir_sil_btn = QPushButton("Seçili Satırı Sil")
        self.satir_sil_btn.setObjectName("btn_iptal")
        self.satir_sil_btn.clicked.connect(self._satir_sil)
        self.temizle_btn = QPushButton("Tümünü Temizle")
        self.temizle_btn.setObjectName("btn_iptal")
        self.temizle_btn.clicked.connect(self._temizle)
        self.kaydet_btn = QPushButton("Stok Girişini Kaydet")
        self.kaydet_btn.setObjectName("btn_basari")
        self.kaydet_btn.clicked.connect(self._kaydet)
        self.toplam_label = QLabel("Toplam: —")

        alt.addWidget(self.satir_sil_btn)
        alt.addWidget(self.temizle_btn)
        alt.addStretch()
        alt.addWidget(self.toplam_label)
        alt.addWidget(self.kaydet_btn)
        layout.addLayout(alt)

        self._urunler_cache: list = []

    def yenile(self):
        self._tedarikcileri_yukle()

    def _tedarikcileri_yukle(self):
        self.tedarikci_combo.clear()
        self.tedarikci_combo.addItem("— Tedarikçi Seçin —", None)
        with get_session() as session:
            tedarikciler = session.query(Tedarikci).filter_by(aktif=True).order_by(Tedarikci.firma_adi).all()
            for t in tedarikciler:
                self.tedarikci_combo.addItem(t.firma_adi, t.id)

    def _urun_ara(self, metin: str):
        sonuclar = urun_servisi.urun_ara(metin)
        self._urunler_cache = sonuclar
        self.urun_sonuc.clear()
        for u in sonuclar[:50]:
            self.urun_sonuc.addItem(f"{u.urun_kodu} — {u.urun_adi}", u.id)
        if sonuclar:
            self.alis_fiyat_edit.deger_ata(Decimal(str(sonuclar[0].alis_fiyati)))

    def _satira_ekle(self):
        urun_id = self.urun_sonuc.currentData()
        if urun_id is None:
            QMessageBox.warning(self, "Uyarı", "Ürün seçin.")
            return
        try:
            miktar = Decimal(self.miktar_edit.text().replace(",", "."))
            if miktar <= 0:
                raise ValueError
        except Exception:
            QMessageBox.warning(self, "Uyarı", "Geçerli bir miktar girin.")
            return

        urun = urun_servisi.urun_bul_id(urun_id)
        alis = self.alis_fiyat_edit.deger()
        aciklama = self.aciklama_edit.text()

        self._satirlar.append({"urun": urun, "miktar": miktar, "alis": alis, "aciklama": aciklama})
        self._tabloyu_guncelle()

    def _tabloyu_guncelle(self):
        self.tablo.setRowCount(len(self._satirlar))
        toplam = Decimal("0")
        for i, s in enumerate(self._satirlar):
            self.tablo.setItem(i, 0, QTableWidgetItem(s["urun"].urun_kodu))
            self.tablo.setItem(i, 1, QTableWidgetItem(s["urun"].urun_adi))
            self.tablo.setItem(i, 2, QTableWidgetItem(miktar_formatla(s["miktar"])))
            self.tablo.setItem(i, 3, QTableWidgetItem(para_formatla(s["alis"])))
            self.tablo.setItem(i, 4, QTableWidgetItem(s["aciklama"]))
            toplam += s["miktar"] * s["alis"]
        self.toplam_label.setText(f"Toplam: {para_formatla(toplam)}")

    def _satir_sil(self):
        row = self.tablo.currentRow()
        if 0 <= row < len(self._satirlar):
            self._satirlar.pop(row)
            self._tabloyu_guncelle()

    def _temizle(self):
        self._satirlar.clear()
        self._tabloyu_guncelle()

    def _kaydet(self):
        if not self._satirlar:
            QMessageBox.warning(self, "Uyarı", "Listeye en az bir ürün ekleyin.")
            return
        tedarikci_id = self.tedarikci_combo.currentData()
        try:
            for s in self._satirlar:
                stok_servisi.stok_girisi_kaydet(
                    urun_id=s["urun"].id,
                    miktar=s["miktar"],
                    birim_fiyat=s["alis"],
                    admin_id=self.admin.id,
                    tedarikci_id=tedarikci_id,
                    aciklama=s["aciklama"],
                )
            QMessageBox.information(
                self, "Başarılı",
                f"{len(self._satirlar)} ürün için stok girişi kaydedildi."
            )
            self._temizle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _tedarikci_ekle(self):
        dlg = _TedarikciEkleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._tedarikcileri_yukle()


class _TedarikciEkleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Tedarikçi")
        self.setMinimumWidth(360)
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.firma_adi = QLineEdit()
        self.yetkili = QLineEdit()
        self.telefon = QLineEdit()
        self.adres = QLineEdit()
        form.addRow("Firma Adı *:", self.firma_adi)
        form.addRow("Yetkili:", self.yetkili)
        form.addRow("Telefon:", self.telefon)
        form.addRow("Adres:", self.adres)
        layout.addLayout(form)
        self.hata = QLabel("")
        self.hata.setObjectName("uyari_etiket")
        layout.addWidget(self.hata)
        butonlar = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        butonlar.accepted.connect(self._kaydet)
        butonlar.rejected.connect(self.reject)
        layout.addWidget(butonlar)

    def _kaydet(self):
        ad = self.firma_adi.text().strip()
        if not ad:
            self.hata.setText("Firma adı zorunludur.")
            return
        with get_session() as session:
            t = Tedarikci(
                firma_adi=ad,
                yetkili_adi=self.yetkili.text().strip() or None,
                telefon=self.telefon.text().strip() or None,
                adres=self.adres.text().strip() or None,
            )
            session.add(t)
        self.accept()

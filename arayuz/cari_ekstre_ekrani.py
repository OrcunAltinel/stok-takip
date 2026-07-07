"""Cari ekstre ekranı — müşterinin tüm hareketleri + borç/alacak toplamları."""

from decimal import Decimal

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableView, QVBoxLayout, QWidget,
)

from arayuz.bilesenler.para_girisi import ParaGirisi
from arayuz.bilesenler.tarih_filtresi import TarihFiltresi
from servisler import musteri_servisi
from veritabani.modeller import Admin, Musteri
from yardimcilar.formatlayici import para_formatla, tarih_formatla

_SUTUNLAR = ["Tarih", "İşlem Tipi", "Belge/Açıklama", "Borç", "Alacak"]
_TIP_ETIKET = {
    "SATIS_BORC": "Satış Borcu",
    "TAHSILAT": "Tahsilat",
    "BAKIYE_YUKLEME": "Bakiye Yükleme",
    "IADE_ALACAK": "İade Alacağı",
}


class CariModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._veri: list[dict] = []

    def yenile(self, veri: list[dict]):
        self.beginResetModel()
        self._veri = veri
        self.endResetModel()

    def rowCount(self, p=QModelIndex()):
        return len(self._veri)

    def columnCount(self, p=QModelIndex()):
        return len(_SUTUNLAR)

    def headerData(self, s, o, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and o == Qt.Orientation.Horizontal:
            return _SUTUNLAR[s]

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        r = self._veri[idx.row()]
        col = idx.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return tarih_formatla(r["tarih"])
            if col == 1:
                return _TIP_ETIKET.get(r["tip"], r["tip"])
            if col == 2:
                return r.get("aciklama", "")
            if col == 3:
                return para_formatla(r["borc"]) if r["borc"] else ""
            if col == 4:
                return para_formatla(r["alacak"]) if r["alacak"] else ""

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 3 and r["borc"]:
                return QColor("#f38ba8")
            if col == 4 and r["alacak"]:
                return QColor("#a6e3a1")

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (3, 4):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None


class CariEkstreEkrani(QDialog):
    def __init__(self, musteri: Musteri, admin: Admin, parent=None):
        super().__init__(parent)
        self.musteri = musteri
        self.admin = admin
        self.setWindowTitle(f"Cari Ekstre — {musteri.ad} {musteri.soyad}")
        self.setMinimumSize(860, 580)
        self._kur()
        self.yenile()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Müşteri bilgi satırı
        bilgi = QHBoxLayout()
        bilgi.addWidget(QLabel(f"<b>{self.musteri.ad} {self.musteri.soyad}</b>"))
        if self.musteri.firma_adi:
            bilgi.addWidget(QLabel(f"| {self.musteri.firma_adi}"))
        if self.musteri.telefon:
            bilgi.addWidget(QLabel(f"| {self.musteri.telefon}"))
        bilgi.addStretch()
        layout.addLayout(bilgi)

        # Tarih filtresi
        self.tarih_filtresi = TarihFiltresi()
        self.tarih_filtresi.degisti.connect(self._filtrele)
        layout.addWidget(self.tarih_filtresi)

        # Tablo
        self.model = CariModel()
        self.tablo = QTableView()
        self.tablo.setModel(self.model)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tablo, 1)

        # Toplamlar
        toplam_grup = QGroupBox("Özet")
        toplam_layout = QHBoxLayout(toplam_grup)
        self.borc_toplam_label = QLabel("Borç Toplamı: —")
        self.alacak_toplam_label = QLabel("Alacak Toplamı: —")
        self.bakiye_label = QLabel("Güncel Bakiye: —")
        self.borc_label = QLabel("Güncel Borç: —")
        for w in [self.borc_toplam_label, self.alacak_toplam_label, self.bakiye_label, self.borc_label]:
            toplam_layout.addWidget(w)
        toplam_layout.addStretch()
        layout.addWidget(toplam_grup)

        # Butonlar
        btn_satir = QHBoxLayout()
        tahsilat_btn = QPushButton("Tahsilat Al")
        tahsilat_btn.setObjectName("btn_basari")
        tahsilat_btn.clicked.connect(self._tahsilat_al)
        bakiye_btn = QPushButton("Bakiye Yükle")
        bakiye_btn.clicked.connect(self._bakiye_yukle)
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("btn_iptal")
        kapat_btn.clicked.connect(self.accept)
        btn_satir.addWidget(tahsilat_btn)
        btn_satir.addWidget(bakiye_btn)
        btn_satir.addStretch()
        btn_satir.addWidget(kapat_btn)
        layout.addLayout(btn_satir)

    def yenile(self, baslangic=None, bitis=None):
        m = musteri_servisi.musteri_bul_id(self.musteri.id)
        if m:
            self.musteri = m

        hareketler = musteri_servisi.cari_hareketler(self.musteri.id, baslangic, bitis)
        self.model.yenile(hareketler)

        borc_top = sum(h["borc"] for h in hareketler)
        alacak_top = sum(h["alacak"] for h in hareketler)
        self.borc_toplam_label.setText(f"Borç: {para_formatla(borc_top)}")
        self.alacak_toplam_label.setText(f"Alacak: {para_formatla(alacak_top)}")
        self.bakiye_label.setText(f"Bakiye: {para_formatla(self.musteri.bakiye)}")
        self.borc_label.setText(f"Borç (Güncel): {para_formatla(self.musteri.borc)}")

    def _filtrele(self, bas, bit):
        self.yenile(bas, bit)

    def _tahsilat_al(self):
        dlg = _TahsilatDialog(self.musteri, self.admin, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.yenile()

    def _bakiye_yukle(self):
        dlg = _BakiyeYukleDialog(self.musteri, self.admin, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.yenile()


class _TahsilatDialog(QDialog):
    def __init__(self, musteri: Musteri, admin: Admin, parent=None):
        super().__init__(parent)
        self.musteri = musteri
        self.admin = admin
        self.setWindowTitle("Tahsilat Al")
        self.setFixedSize(380, 260)
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.tutar_edit = ParaGirisi()
        self.arac_combo = QComboBox()
        self.arac_combo.addItems(["NAKIT", "KART"])
        self.aciklama_edit = QLineEdit()
        form.addRow(f"Mevcut Borç:", QLabel(para_formatla(self.musteri.borc)))
        form.addRow("Tahsilat Tutarı:", self.tutar_edit)
        form.addRow("Ödeme Aracı:", self.arac_combo)
        form.addRow("Açıklama:", self.aciklama_edit)
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
        tutar = self.tutar_edit.deger()
        if tutar <= 0:
            self.hata.setText("Tutar sıfırdan büyük olmalıdır.")
            return
        try:
            musteri_servisi.tahsilat_al(
                self.musteri.id, tutar, self.arac_combo.currentText(),
                self.admin.id, self.aciklama_edit.text()
            )
            self.accept()
        except Exception as e:
            self.hata.setText(str(e))


class _BakiyeYukleDialog(QDialog):
    def __init__(self, musteri: Musteri, admin: Admin, parent=None):
        super().__init__(parent)
        self.musteri = musteri
        self.admin = admin
        self.setWindowTitle("Bakiye Yükle")
        self.setFixedSize(380, 240)
        self._kur()

    def _kur(self):
        from PySide6.QtWidgets import QLineEdit
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.tutar_edit = ParaGirisi()
        self.arac_combo = QComboBox()
        self.arac_combo.addItems(["NAKIT", "KART"])
        self.aciklama_edit = QLineEdit()
        form.addRow(f"Mevcut Bakiye:", QLabel(para_formatla(self.musteri.bakiye)))
        form.addRow("Yüklenecek Tutar:", self.tutar_edit)
        form.addRow("Ödeme Aracı:", self.arac_combo)
        form.addRow("Açıklama:", self.aciklama_edit)
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
        tutar = self.tutar_edit.deger()
        if tutar <= 0:
            self.hata.setText("Tutar sıfırdan büyük olmalıdır.")
            return
        try:
            musteri_servisi.bakiye_yukle(
                self.musteri.id, tutar, self.arac_combo.currentText(),
                self.admin.id, self.aciklama_edit.text()
            )
            self.accept()
        except Exception as e:
            self.hata.setText(str(e))

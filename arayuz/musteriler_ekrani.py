"""Müşteriler listesi ekranı."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableView, QVBoxLayout, QWidget,
)

from arayuz.cari_ekstre_ekrani import CariEkstreEkrani
from servisler import musteri_servisi
from veritabani.modeller import Admin, Musteri
from yardimcilar.formatlayici import para_formatla

_SUTUNLAR = [
    ("ID", "id"),
    ("Ad", "ad"),
    ("Soyad", "soyad"),
    ("Firma", "firma_adi"),
    ("Telefon", "telefon"),
    ("İl", "il"),
    ("Bakiye", "bakiye"),
    ("Borç", "borc"),
]


class MusteriModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._veri: list[Musteri] = []

    def yenile(self, liste: list[Musteri]):
        self.beginResetModel()
        self._veri = liste
        self.endResetModel()

    def rowCount(self, p=QModelIndex()):
        return len(self._veri)

    def columnCount(self, p=QModelIndex()):
        return len(_SUTUNLAR)

    def headerData(self, s, o, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and o == Qt.Orientation.Horizontal:
            return _SUTUNLAR[s][0]

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        m = self._veri[idx.row()]
        alan = _SUTUNLAR[idx.column()][1]
        v = getattr(m, alan)
        if role == Qt.ItemDataRole.DisplayRole:
            if alan in ("bakiye", "borc"):
                return para_formatla(v)
            return str(v) if v else ""
        if role == Qt.ItemDataRole.UserRole:
            return m
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if alan in ("bakiye", "borc"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def musteri_satir(self, row: int) -> Musteri:
        return self._veri[row]


class MusterilerEkrani(QWidget):
    def __init__(self, admin: Admin):
        super().__init__()
        self.admin = admin
        self._kur()
        self.yenile()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        baslik = QLabel("Müşteriler")
        baslik.setObjectName("baslik")
        layout.addWidget(baslik)

        # Arama + butonlar
        ust = QHBoxLayout()
        self.arama = QLineEdit()
        self.arama.setPlaceholderText("Ad, soyad, telefon veya firma...")
        self.arama.textChanged.connect(self._ara)
        self.yeni_btn = QPushButton("+ Yeni Müşteri")
        self.yeni_btn.clicked.connect(self._yeni)
        self.duzenle_btn = QPushButton("Düzenle")
        self.duzenle_btn.clicked.connect(self._duzenle)
        self.ekstre_btn = QPushButton("Cari Ekstre")
        self.ekstre_btn.clicked.connect(self._cari_ekstre)
        self.bilgi = QLabel("")
        self.bilgi.setObjectName("alt_baslik")
        ust.addWidget(QLabel("Ara:"))
        ust.addWidget(self.arama, 1)
        ust.addWidget(self.yeni_btn)
        ust.addWidget(self.duzenle_btn)
        ust.addWidget(self.ekstre_btn)
        ust.addStretch()
        ust.addWidget(self.bilgi)
        layout.addLayout(ust)

        # Tablo
        self.model = MusteriModel()
        self.tablo = QTableView()
        self.tablo.setModel(self.model)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setSortingEnabled(True)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.doubleClicked.connect(lambda: self._cari_ekstre())
        layout.addWidget(self.tablo, 1)

    def yenile(self):
        arama = self.arama.text() if hasattr(self, "arama") else ""
        if arama:
            liste = musteri_servisi.musteri_ara(arama)
        else:
            liste = musteri_servisi.musteri_listesi()
        self.model.yenile(liste)
        self.bilgi.setText(f"{len(liste)} müşteri")

    def _ara(self, metin: str):
        if metin:
            liste = musteri_servisi.musteri_ara(metin)
        else:
            liste = musteri_servisi.musteri_listesi()
        self.model.yenile(liste)
        self.bilgi.setText(f"{len(liste)} müşteri")

    def _secili(self) -> Musteri | None:
        idx = self.tablo.currentIndex()
        if not idx.isValid():
            return None
        return self.model.musteri_satir(idx.row())

    def _yeni(self):
        dlg = MusteriDialog(self.admin, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.yenile()

    def _duzenle(self):
        m = self._secili()
        if not m:
            QMessageBox.warning(self, "Uyarı", "Düzenlenecek müşteriyi seçin.")
            return
        dlg = MusteriDialog(self.admin, musteri=m, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.yenile()

    def _cari_ekstre(self):
        m = self._secili()
        if not m:
            QMessageBox.warning(self, "Uyarı", "Müşteri seçin.")
            return
        CariEkstreEkrani(m, self.admin, self).exec()
        self.yenile()


class MusteriDialog(QDialog):
    def __init__(self, admin: Admin, musteri: Musteri = None, parent=None):
        super().__init__(parent)
        self.admin = admin
        self.duzenle = musteri
        self.setWindowTitle("Müşteri Düzenle" if musteri else "Yeni Müşteri")
        self.setMinimumWidth(440)
        self._kur()
        if musteri:
            self._doldur(musteri)

    def _kur(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)
        self.ad = QLineEdit()
        self.soyad = QLineEdit()
        self.firma_adi = QLineEdit()
        self.telefon = QLineEdit()
        self.adres = QLineEdit()
        self.il = QLineEdit()
        self.ilce = QLineEdit()
        self.vergi_no = QLineEdit()
        self.notlar = QLineEdit()
        form.addRow("Ad *:", self.ad)
        form.addRow("Soyad *:", self.soyad)
        form.addRow("Firma Adı:", self.firma_adi)
        form.addRow("Telefon:", self.telefon)
        form.addRow("Adres:", self.adres)
        form.addRow("İl:", self.il)
        form.addRow("İlçe:", self.ilce)
        form.addRow("Vergi No:", self.vergi_no)
        form.addRow("Notlar:", self.notlar)
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

    def _doldur(self, m: Musteri):
        self.ad.setText(m.ad)
        self.soyad.setText(m.soyad)
        self.firma_adi.setText(m.firma_adi or "")
        self.telefon.setText(m.telefon or "")
        self.adres.setText(m.adres or "")
        self.il.setText(m.il or "")
        self.ilce.setText(m.ilce or "")
        self.vergi_no.setText(m.vergi_no or "")
        self.notlar.setText(m.notlar or "")

    def _kaydet(self):
        ad = self.ad.text().strip()
        soyad = self.soyad.text().strip()
        if not ad or not soyad:
            self.hata.setText("Ad ve soyad zorunludur.")
            return
        kwargs = dict(
            ad=ad, soyad=soyad,
            firma_adi=self.firma_adi.text().strip() or None,
            telefon=self.telefon.text().strip() or None,
            adres=self.adres.text().strip() or None,
            il=self.il.text().strip() or None,
            ilce=self.ilce.text().strip() or None,
            vergi_no=self.vergi_no.text().strip() or None,
            notlar=self.notlar.text().strip() or None,
        )
        try:
            if self.duzenle:
                musteri_servisi.musteri_guncelle(self.duzenle.id, **kwargs)
            else:
                musteri_servisi.musteri_ekle(**kwargs)
            self.accept()
        except Exception as e:
            self.hata.setText(str(e))

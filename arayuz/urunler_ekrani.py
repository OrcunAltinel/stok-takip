"""Ürünler / Stok ekranı — anlık arama, sıralanabilir tablo, geçmiş diyaloğu."""

from decimal import Decimal

from PySide6.QtCore import (
    QAbstractTableModel, QModelIndex, Qt, QSortFilterProxyModel,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QTableView,
    QVBoxLayout, QWidget, QComboBox,
)

from arayuz.bilesenler.para_girisi import ParaGirisi
from servisler import urun_servisi, stok_servisi
from veritabani.modeller import Admin, Urun
from yardimcilar.formatlayici import miktar_formatla, para_formatla


_SUTUNLAR = [
    ("Kod", "urun_kodu"),
    ("Ürün Adı", "urun_adi"),
    ("OEM No", "oem_no"),
    ("Marka", "marka"),
    ("Stok", "stok_miktari"),
    ("Kritik", "kritik_stok_seviyesi"),
    ("Alış", "alis_fiyati"),
    ("Satış", "satis_fiyati"),
    ("KDV%", "kdv_orani"),
    ("Birim", "birim"),
    ("Raf", "raf_adresi"),
]


class UrunModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._veri: list[Urun] = []

    def yenile(self, urunler: list[Urun]):
        self.beginResetModel()
        self._veri = urunler
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._veri)

    def columnCount(self, parent=QModelIndex()):
        return len(_SUTUNLAR)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return _SUTUNLAR[section][0]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        urun = self._veri[index.row()]
        alan = _SUTUNLAR[index.column()][1]
        deger = getattr(urun, alan)

        if role == Qt.ItemDataRole.DisplayRole:
            if alan in ("alis_fiyati", "satis_fiyati"):
                return para_formatla(deger)
            if alan in ("stok_miktari", "kritik_stok_seviyesi"):
                return miktar_formatla(deger)
            if alan == "kdv_orani":
                return f"%{deger}"
            return str(deger) if deger is not None else ""

        if role == Qt.ItemDataRole.ForegroundRole:
            if alan == "stok_miktari":
                stok = Decimal(str(deger)) if deger is not None else Decimal("0")
                kritik = Decimal(str(urun.kritik_stok_seviyesi)) if urun.kritik_stok_seviyesi else Decimal("5")
                if stok <= 0:
                    return QColor("#f38ba8")
                if stok <= kritik:
                    return QColor("#fab387")

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if alan in ("stok_miktari", "kritik_stok_seviyesi", "alis_fiyati", "satis_fiyati", "kdv_orani"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        if role == Qt.ItemDataRole.UserRole:
            return urun

        return None

    def urun_satir(self, row: int) -> Urun:
        return self._veri[row]


class UrunEkleDialog(QDialog):
    def __init__(self, parent=None, urun: Urun = None):
        super().__init__(parent)
        self.duzenle_urun = urun
        self.setWindowTitle("Ürün Düzenle" if urun else "Yeni Ürün Ekle")
        self.setMinimumWidth(460)
        self._kur()
        if urun:
            self._doldur(urun)

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.urun_kodu = QLineEdit()
        self.urun_kodu.setPlaceholderText("Örn: DA-9809P")
        self.urun_adi = QLineEdit()
        self.oem_no = QLineEdit()
        self.marka = QLineEdit()
        self.kategori = QLineEdit()

        self.birim = QComboBox()
        self.birim.addItems(["adet", "litre", "takım", "kg", "metre"])

        self.alis_fiyati = ParaGirisi()
        self.satis_fiyati = ParaGirisi()

        self.kdv_orani = QComboBox()
        for oran in ["0", "10", "20"]:
            self.kdv_orani.addItem(f"%{oran}", oran)
        self.kdv_orani.setCurrentIndex(2)

        self.kritik_stok = QLineEdit("5")
        self.raf_adresi = QLineEdit()

        form.addRow("Ürün Kodu *:", self.urun_kodu)
        form.addRow("Ürün Adı *:", self.urun_adi)
        form.addRow("OEM No:", self.oem_no)
        form.addRow("Marka:", self.marka)
        form.addRow("Kategori:", self.kategori)
        form.addRow("Birim:", self.birim)
        form.addRow("Alış Fiyatı:", self.alis_fiyati)
        form.addRow("Satış Fiyatı:", self.satis_fiyati)
        form.addRow("KDV Oranı:", self.kdv_orani)
        form.addRow("Kritik Stok:", self.kritik_stok)
        form.addRow("Raf Adresi:", self.raf_adresi)
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

    def _doldur(self, u: Urun):
        self.urun_kodu.setText(u.urun_kodu)
        self.urun_adi.setText(u.urun_adi)
        self.oem_no.setText(u.oem_no or "")
        self.marka.setText(u.marka or "")
        self.kategori.setText(u.kategori or "")
        idx = self.birim.findText(u.birim)
        if idx >= 0:
            self.birim.setCurrentIndex(idx)
        self.alis_fiyati.deger_ata(Decimal(str(u.alis_fiyati)))
        self.satis_fiyati.deger_ata(Decimal(str(u.satis_fiyati)))
        kdv_str = str(int(Decimal(str(u.kdv_orani))))
        k_idx = self.kdv_orani.findData(kdv_str)
        if k_idx >= 0:
            self.kdv_orani.setCurrentIndex(k_idx)
        self.kritik_stok.setText(miktar_formatla(u.kritik_stok_seviyesi))
        self.raf_adresi.setText(u.raf_adresi or "")

    def _kaydet(self):
        kod = self.urun_kodu.text().strip()
        ad = self.urun_adi.text().strip()
        if not kod or not ad:
            self.hata.setText("Ürün kodu ve adı zorunludur.")
            return
        try:
            kritik = Decimal(self.kritik_stok.text().replace(",", "."))
        except Exception:
            kritik = Decimal("5")
        try:
            kdv = Decimal(self.kdv_orani.currentData())
        except Exception:
            kdv = Decimal("20")

        kwargs = dict(
            urun_kodu=kod,
            urun_adi=ad,
            oem_no=self.oem_no.text().strip() or None,
            marka=self.marka.text().strip() or None,
            kategori=self.kategori.text().strip() or None,
            birim=self.birim.currentText(),
            alis_fiyati=self.alis_fiyati.deger(),
            satis_fiyati=self.satis_fiyati.deger(),
            kdv_orani=kdv,
            kritik_stok_seviyesi=kritik,
            raf_adresi=self.raf_adresi.text().strip() or None,
        )
        try:
            if self.duzenle_urun:
                urun_servisi.urun_guncelle(self.duzenle_urun.id, **kwargs)
            else:
                urun_servisi.urun_ekle(**kwargs)
            self.accept()
        except Exception as e:
            self.hata.setText(str(e))


class StokGecmisiDialog(QDialog):
    def __init__(self, urun: Urun, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Stok Geçmişi — {urun.urun_kodu} / {urun.urun_adi}")
        self.setMinimumSize(800, 460)
        self._kur(urun.id)

    def _kur(self, urun_id: int):
        layout = QVBoxLayout(self)
        tablo = QTableView()
        tablo.setAlternatingRowColors(True)
        tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        gecmis = stok_servisi.urun_stok_gecmisi(urun_id)

        sutunlar = ["Tarih", "Hareket", "Miktar", "Birim Fiyat", "Tedarikçi", "Fiş No", "Açıklama", "Admin"]
        model = QAbstractTableModel()

        class _M(QAbstractTableModel):
            def __init__(self, data):
                super().__init__()
                self._d = data

            def rowCount(self, p=QModelIndex()):
                return len(self._d)

            def columnCount(self, p=QModelIndex()):
                return len(sutunlar)

            def headerData(self, s, o, role=Qt.ItemDataRole.DisplayRole):
                if role == Qt.ItemDataRole.DisplayRole and o == Qt.Orientation.Horizontal:
                    return sutunlar[s]

            def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
                if not idx.isValid():
                    return None
                r = self._d[idx.row()]
                cols = ["tarih", "hareket_tipi", "miktar", "birim_fiyat", "tedarikci", "fis_no", "aciklama", "admin"]
                alan = cols[idx.column()]
                v = r[alan]
                if role == Qt.ItemDataRole.DisplayRole:
                    if alan == "tarih":
                        from yardimcilar.formatlayici import tarih_formatla
                        return tarih_formatla(v)
                    if alan == "birim_fiyat":
                        return para_formatla(v)
                    if alan == "miktar":
                        return miktar_formatla(v)
                    return str(v) if v else ""
                if role == Qt.ItemDataRole.ForegroundRole:
                    tip = r["hareket_tipi"]
                    if tip == "GIRIS" or tip == "IADE_GIRIS":
                        return QColor("#a6e3a1")
                    if tip == "CIKIS":
                        return QColor("#f38ba8")
                return None

        tablo.setModel(_M(gecmis))
        layout.addWidget(tablo)

        kapat = QPushButton("Kapat")
        kapat.clicked.connect(self.accept)
        layout.addWidget(kapat)


class UrunlerEkrani(QWidget):
    def __init__(self, admin: Admin):
        super().__init__()
        self.admin = admin
        self._kur()
        self.yenile()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        baslik = QLabel("Ürünler / Stok")
        baslik.setObjectName("baslik")
        layout.addWidget(baslik)

        # Arama + filtre
        arama_satir = QHBoxLayout()
        self.arama_kutusu = QLineEdit()
        self.arama_kutusu.setPlaceholderText("Kod, ürün adı veya OEM no ile ara...")
        self.arama_kutusu.textChanged.connect(self._anlık_ara)

        self.mod_iceride = QRadioButton("İçinde geçen")
        self.mod_baslar = QRadioButton("İle başlayan")
        self.mod_iceride.setChecked(True)
        self.mod_iceride.toggled.connect(lambda: self._anlık_ara(self.arama_kutusu.text()))

        arama_satir.addWidget(QLabel("Ara:"))
        arama_satir.addWidget(self.arama_kutusu, 1)
        arama_satir.addWidget(self.mod_iceride)
        arama_satir.addWidget(self.mod_baslar)
        layout.addLayout(arama_satir)

        # Butonlar
        btn_satir = QHBoxLayout()
        self.yeni_btn = QPushButton("+ Yeni Ürün")
        self.yeni_btn.clicked.connect(self._yeni_urun)
        self.duzenle_btn = QPushButton("Düzenle")
        self.duzenle_btn.clicked.connect(self._duzenle)
        self.pasif_btn = QPushButton("Pasife Al")
        self.pasif_btn.setObjectName("btn_tehlike")
        self.pasif_btn.clicked.connect(self._pasife_al)
        self.gecmis_btn = QPushButton("Stok Geçmişi")
        self.gecmis_btn.clicked.connect(self._gecmis_goster)
        self.bilgi_label = QLabel("")
        self.bilgi_label.setObjectName("alt_baslik")

        btn_satir.addWidget(self.yeni_btn)
        btn_satir.addWidget(self.duzenle_btn)
        btn_satir.addWidget(self.pasif_btn)
        btn_satir.addWidget(self.gecmis_btn)
        btn_satir.addStretch()
        btn_satir.addWidget(self.bilgi_label)
        layout.addLayout(btn_satir)

        # Tablo
        self.model = UrunModel()
        self.tablo = QTableView()
        self.tablo.setModel(self.model)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSortingEnabled(True)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.doubleClicked.connect(self._cift_tiklandi)
        layout.addWidget(self.tablo)

    def yenile(self):
        arama = self.arama_kutusu.text() if hasattr(self, "arama_kutusu") else ""
        mod = "baslar" if hasattr(self, "mod_baslar") and self.mod_baslar.isChecked() else "iceride"
        urunler = urun_servisi.urun_ara(arama, mod)
        self.model.yenile(urunler)
        self.bilgi_label.setText(f"{len(urunler)} ürün")

    def _anlık_ara(self, metin: str):
        mod = "baslar" if self.mod_baslar.isChecked() else "iceride"
        urunler = urun_servisi.urun_ara(metin, mod)
        self.model.yenile(urunler)
        self.bilgi_label.setText(f"{len(urunler)} ürün")

    def _secili_urun(self):
        idx = self.tablo.currentIndex()
        if not idx.isValid():
            return None
        return self.model.urun_satir(idx.row())

    def _yeni_urun(self):
        dlg = UrunEkleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.yenile()

    def _duzenle(self):
        urun = self._secili_urun()
        if not urun:
            QMessageBox.warning(self, "Uyarı", "Düzenlenecek ürünü seçin.")
            return
        dlg = UrunEkleDialog(self, urun)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.yenile()

    def _pasife_al(self):
        urun = self._secili_urun()
        if not urun:
            QMessageBox.warning(self, "Uyarı", "Pasife alınacak ürünü seçin.")
            return
        cevap = QMessageBox.question(
            self, "Onay", f"{urun.urun_kodu} — {urun.urun_adi} pasife alınacak. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if cevap == QMessageBox.StandardButton.Yes:
            urun_servisi.urun_pasife_al(urun.id)
            self.yenile()

    def _gecmis_goster(self):
        urun = self._secili_urun()
        if not urun:
            QMessageBox.warning(self, "Uyarı", "Geçmişi görüntülenecek ürünü seçin.")
            return
        StokGecmisiDialog(urun, self).exec()

    def _cift_tiklandi(self, index):
        urun = self.model.urun_satir(index.row())
        StokGecmisiDialog(urun, self).exec()

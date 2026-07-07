"""Cari ekstre ekranı — müşterinin tüm hareketleri."""

from decimal import Decimal

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableView, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from arayuz.bilesenler.para_girisi import ParaGirisi
from arayuz.bilesenler.tarih_filtresi import TarihFiltresi
from servisler import musteri_servisi, satis_servisi
from veritabani.modeller import Admin, Musteri
from yardimcilar.formatlayici import miktar_formatla, para_formatla, tarih_formatla

_SUTUNLAR = ["Tarih", "İşlem", "Fiş / Açıklama", "Borç (₺)", "Tahsilat / Alacak (₺)"]


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
        if role == Qt.ItemDataRole.FontRole and o == Qt.Orientation.Horizontal:
            f = QFont()
            f.setBold(True)
            return f

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        r = self._veri[idx.row()]
        col = idx.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return tarih_formatla(r["tarih"])
            if col == 1:
                return r.get("display_tip", r["tip"])
            if col == 2:
                return r.get("belge", "")
            if col == 3:
                return para_formatla(r["borc"]) if r["borc"] else "—"
            if col == 4:
                return para_formatla(r["tahsilat"]) if r["tahsilat"] else "—"

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 3 and r["borc"]:
                return QColor("#f38ba8")
            if col == 4 and r["tahsilat"]:
                return QColor("#a6e3a1")

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (3, 4):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        if role == Qt.ItemDataRole.ToolTipRole:
            if r.get("fis_id"):
                return "Çift tıklayın — satın alınan ürünleri görüntüleyin"

        return None


class CariEkstreEkrani(QDialog):
    def __init__(self, musteri: Musteri, admin: Admin, parent=None):
        super().__init__(parent)
        self.musteri = musteri
        self.admin = admin
        self.setWindowTitle(f"Hesap Hareketleri — {musteri.ad} {musteri.soyad}")
        self.setMinimumSize(920, 600)
        self._kur()
        self.yenile()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Müşteri bilgi satırı
        bilgi = QHBoxLayout()
        isim = QLabel(f"<b>{self.musteri.ad} {self.musteri.soyad}</b>")
        isim.setObjectName("baslik")
        bilgi.addWidget(isim)
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
        self.tablo.doubleClicked.connect(self._detay_goster)
        layout.addWidget(self.tablo, 1)

        # Özet kutusu
        ozet = QGroupBox("Hesap Özeti")
        ozet_layout = QHBoxLayout(ozet)
        ozet_layout.setSpacing(24)

        self.lbl_donem_borc = QLabel()
        self.lbl_donem_tahsilat = QLabel()
        self.lbl_guncel_borc = QLabel()
        self.lbl_guncel_bakiye = QLabel()

        for lbl in [self.lbl_donem_borc, self.lbl_donem_tahsilat,
                    self.lbl_guncel_borc, self.lbl_guncel_bakiye]:
            ozet_layout.addWidget(lbl)
        ozet_layout.addStretch()
        layout.addWidget(ozet)

        # Butonlar
        btn_satir = QHBoxLayout()
        tahsilat_btn = QPushButton("Tahsilat Al")
        tahsilat_btn.setObjectName("btn_basari")
        tahsilat_btn.clicked.connect(self._tahsilat_al)
        tahsilat_btn.setToolTip("Veresiye borcunu tahsil et")

        odeme_btn = QPushButton("Ödeme / Bakiye Yükle")
        odeme_btn.clicked.connect(self._bakiye_yukle)
        odeme_btn.setToolTip("Ödeme al — borç varsa önce kapatılır, kalan bakiye olarak eklenir")

        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("btn_iptal")
        kapat_btn.clicked.connect(self.accept)

        btn_satir.addWidget(tahsilat_btn)
        btn_satir.addWidget(odeme_btn)
        btn_satir.addStretch()
        btn_satir.addWidget(kapat_btn)
        layout.addLayout(btn_satir)

    def yenile(self, baslangic=None, bitis=None):
        m = musteri_servisi.musteri_bul_id(self.musteri.id)
        if m:
            self.musteri = m

        hareketler = musteri_servisi.cari_hareketler(self.musteri.id, baslangic, bitis)
        self.model.yenile(hareketler)

        donem_borc = sum(h["borc"] for h in hareketler)
        donem_tahsilat = sum(h["tahsilat"] for h in hareketler)

        self.lbl_donem_borc.setText(
            f"<span style='color:#f38ba8'><b>Dönem Borç:</b> {para_formatla(donem_borc)}</span>"
        )
        self.lbl_donem_tahsilat.setText(
            f"<span style='color:#a6e3a1'><b>Dönem Tahsilat:</b> {para_formatla(donem_tahsilat)}</span>"
        )
        borc_renk = "#f38ba8" if self.musteri.borc > 0 else "#a6e3a1"
        self.lbl_guncel_borc.setText(
            f"<span style='color:{borc_renk}'><b>Güncel Borç:</b> {para_formatla(self.musteri.borc)}</span>"
        )
        bakiye_renk = "#a6e3a1" if self.musteri.bakiye > 0 else "#cdd6f4"
        self.lbl_guncel_bakiye.setText(
            f"<span style='color:{bakiye_renk}'><b>Bakiye:</b> {para_formatla(self.musteri.bakiye)}</span>"
        )

    def _filtrele(self, bas, bit):
        self.yenile(bas, bit)

    def _detay_goster(self, idx):
        satir = self.model._veri[idx.row()]
        fis_id = satir.get("fis_id")
        if not fis_id:
            return
        detay = satis_servisi.fis_detay(fis_id)
        if not detay:
            return
        _FisDetayDialog(detay, self).exec()

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
        self.setFixedSize(400, 260)
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        self.tutar_edit = ParaGirisi()
        self.arac_combo = QComboBox()
        self.arac_combo.addItems(["NAKİT", "KART"])
        self.aciklama_edit = QLineEdit()

        borc_lbl = QLabel(f"<b style='color:#f38ba8'>{para_formatla(self.musteri.borc)}</b>")
        form.addRow("Mevcut Borç:", borc_lbl)
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
        self.setWindowTitle("Ödeme / Bakiye Yükle")
        self.setFixedSize(420, 300)
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        self.tutar_edit = ParaGirisi()
        self.arac_combo = QComboBox()
        self.arac_combo.addItems(["NAKİT", "KART"])
        self.aciklama_edit = QLineEdit()

        if self.musteri.borc > 0:
            borc_lbl = QLabel(f"<b style='color:#f38ba8'>{para_formatla(self.musteri.borc)}</b>")
            form.addRow("Mevcut Borç:", borc_lbl)
            bilgi = QLabel("⚠ Borç varsa önce kapatılır, kalan bakiye olarak eklenir.")
            bilgi.setObjectName("uyari_etiket")
            layout.addWidget(bilgi)
        else:
            bakiye_lbl = QLabel(f"<b style='color:#a6e3a1'>{para_formatla(self.musteri.bakiye)}</b>")
            form.addRow("Mevcut Bakiye:", bakiye_lbl)

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


class _FisDetayDialog(QDialog):
    def __init__(self, detay: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Fiş Detayı — {detay['fis_no']}")
        self.setMinimumSize(700, 420)
        self._kur(detay)

    def _kur(self, d: dict):
        layout = QVBoxLayout(self)

        bilgi = QHBoxLayout()
        bilgi.addWidget(QLabel(f"<b>Fiş No:</b> {d['fis_no']}"))
        bilgi.addWidget(QLabel(f"<b>Tarih:</b> {tarih_formatla(d['tarih'])}"))
        bilgi.addWidget(QLabel(f"<b>Ödeme:</b> {d['odeme_tipi']}"))
        bilgi.addStretch()
        layout.addLayout(bilgi)

        sutunlar = ["Ürün Kodu", "Ürün Adı", "Miktar", "Birim Fiyat", "KDV%", "Satır Toplam"]
        tablo = QTableWidget(len(d["kalemler"]), len(sutunlar))
        tablo.setHorizontalHeaderLabels(sutunlar)
        tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tablo.setAlternatingRowColors(True)
        tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tablo.horizontalHeader().setStretchLastSection(True)

        for r, k in enumerate(d["kalemler"]):
            degerler = [
                k["urun_kodu"], k["urun_adi"],
                miktar_formatla(k["miktar"]),
                para_formatla(k["birim_fiyat"]),
                f"%{k['kdv_orani']}",
                para_formatla(k["satir_toplam"]),
            ]
            for c, val in enumerate(degerler):
                item = QTableWidgetItem(val)
                if c in (2, 3, 4, 5):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                tablo.setItem(r, c, item)

        layout.addWidget(tablo, 1)

        top_layout = QHBoxLayout()
        top_layout.addStretch()
        for etiket, tutar in [
            ("Ara Toplam", d["ara_toplam"]),
            ("KDV", d["kdv_toplam"]),
            ("Genel Toplam", d["genel_toplam"]),
        ]:
            top_layout.addWidget(QLabel(f"<b>{etiket}:</b> {para_formatla(tutar)}"))
        layout.addLayout(top_layout)

        if d.get("aciklama"):
            layout.addWidget(QLabel(f"Not: {d['aciklama']}"))

        kapat = QPushButton("Kapat")
        kapat.clicked.connect(self.accept)
        layout.addWidget(kapat)

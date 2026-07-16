"""Müşteri geçmişi ekranı — satış ve iade hareketleri."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QTableView, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from arayuz.bilesenler.tarih_filtresi import TarihFiltresi
from servisler import musteri_servisi, satis_servisi
from veritabani.modeller import Admin, Musteri
from yardimcilar.formatlayici import miktar_formatla, para_formatla, tarih_formatla

_SUTUNLAR = ["Tarih", "İşlem", "Fiş / Açıklama", "Tutar (₺)"]


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
                return para_formatla(abs(r["tutar"]))

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 3:
                return QColor("#a6e3a1") if r["tutar"] < 0 else QColor("#f38ba8")

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 3:
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
        self.setWindowTitle(f"Satış / İade Geçmişi — {musteri.ad} {musteri.soyad}")
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
        ozet = QGroupBox("Dönem Özeti")
        ozet_layout = QHBoxLayout(ozet)
        ozet_layout.setSpacing(24)

        self.lbl_donem_satis = QLabel()
        self.lbl_donem_iade = QLabel()
        self.lbl_net = QLabel()

        for lbl in [self.lbl_donem_satis, self.lbl_donem_iade, self.lbl_net]:
            ozet_layout.addWidget(lbl)
        ozet_layout.addStretch()
        layout.addWidget(ozet)

        # Butonlar
        btn_satir = QHBoxLayout()
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("btn_iptal")
        kapat_btn.clicked.connect(self.accept)

        btn_satir.addStretch()
        btn_satir.addWidget(kapat_btn)
        layout.addLayout(btn_satir)

    def yenile(self, baslangic=None, bitis=None):
        m = musteri_servisi.musteri_bul_id(self.musteri.id)
        if m:
            self.musteri = m

        hareketler = musteri_servisi.cari_hareketler(self.musteri.id, baslangic, bitis)
        self.model.yenile(hareketler)

        donem_satis = sum(h["tutar"] for h in hareketler if h["tutar"] > 0)
        donem_iade = sum(-h["tutar"] for h in hareketler if h["tutar"] < 0)

        self.lbl_donem_satis.setText(
            f"<span style='color:#f38ba8'><b>Dönem Satış:</b> {para_formatla(donem_satis)}</span>"
        )
        self.lbl_donem_iade.setText(
            f"<span style='color:#a6e3a1'><b>Dönem İade:</b> {para_formatla(donem_iade)}</span>"
        )
        self.lbl_net.setText(
            f"<b>Net:</b> {para_formatla(donem_satis - donem_iade)}"
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

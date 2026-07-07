"""Raporlar ekranı — 5 sekme, tarih filtresi, Excel/PDF aktarım."""

import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QTabWidget, QTableView,
    QVBoxLayout, QWidget,
)

from arayuz.bilesenler.tarih_filtresi import TarihFiltresi
from servisler import rapor_servisi
from veritabani.modeller import Admin
from yardimcilar.formatlayici import miktar_formatla, para_formatla, tarih_formatla


class _SatirModel(QAbstractTableModel):
    def __init__(self, sutunlar, veri):
        super().__init__()
        self._sutunlar = sutunlar
        self._veri = veri

    def rowCount(self, p=QModelIndex()):
        return len(self._veri)

    def columnCount(self, p=QModelIndex()):
        return len(self._sutunlar)

    def headerData(self, s, o, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and o == Qt.Orientation.Horizontal:
            return self._sutunlar[s]

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._veri[idx.row()][idx.column()])
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        return None

    def ham_veri(self):
        return self._veri


def _tablo_widget(sutunlar, veri) -> tuple[QTableView, _SatirModel]:
    model = _SatirModel(sutunlar, veri)
    tablo = QTableView()
    tablo.setModel(model)
    tablo.setAlternatingRowColors(True)
    tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tablo.setSortingEnabled(True)
    tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    tablo.horizontalHeader().setStretchLastSection(True)
    return tablo, model


class _RaporSekmesi(QWidget):
    def __init__(self, sutunlar: list[str]):
        super().__init__()
        self.sutunlar = sutunlar
        self._model = None
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.tablo, self._model = _tablo_widget(self.sutunlar, [])
        layout.addWidget(self.tablo)

        btn_satir = QHBoxLayout()
        self.kayit_sayisi = QLabel("— kayıt")
        excel_btn = QPushButton("Excel'e Aktar")
        excel_btn.clicked.connect(self._excel_aktar)
        btn_satir.addWidget(self.kayit_sayisi)
        btn_satir.addStretch()
        btn_satir.addWidget(excel_btn)
        layout.addLayout(btn_satir)

    def guncelle(self, veri: list[list]):
        self._model = _SatirModel(self.sutunlar, veri)
        self.tablo.setModel(self._model)
        self.kayit_sayisi.setText(f"{len(veri)} kayıt")

    def _excel_aktar(self):
        if not self._model or not self._model.ham_veri():
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak veri yok.")
            return
        yol, _ = QFileDialog.getSaveFileName(self, "Excel Kaydet", "", "Excel (*.xlsx)")
        if not yol:
            return
        from yardimcilar.excel_aktar import excel_aktar
        try:
            excel_aktar(
                "Rapor",
                self.sutunlar,
                self._model.ham_veri(),
                Path(yol),
            )
            os.startfile(yol)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))


class RaporlarEkrani(QWidget):
    def __init__(self, admin: Admin):
        super().__init__()
        self.admin = admin
        self._bas = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        self._bit = datetime.now().replace(hour=23, minute=59, second=59)
        self._kur()
        self.yenile()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        baslik = QLabel("Raporlar")
        baslik.setObjectName("baslik")
        layout.addWidget(baslik)

        self.filtre = TarihFiltresi()
        self.filtre.degisti.connect(self._filtrele)
        layout.addWidget(self.filtre)

        self.tabs = QTabWidget()

        self.satis_sekme = _RaporSekmesi(
            ["Fiş No", "Tarih", "Müşteri", "Ara Toplam", "KDV", "Genel Toplam", "Ödeme Tipi"]
        )
        self.urun_bazli_sekme = _RaporSekmesi(
            ["Ürün Kodu", "Ürün Adı", "Satılan Miktar", "Toplam Tutar"]
        )
        self.stok_sekme = _RaporSekmesi(
            ["Tarih", "Ürün Kodu", "Ürün Adı", "Hareket", "Miktar", "Birim Fiyat", "Açıklama"]
        )
        self.borclu_sekme = _RaporSekmesi(
            ["ID", "Müşteri", "Firma", "Telefon", "Borç", "Bakiye"]
        )
        self.kar_sekme = _RaporSekmesi(
            ["Ürün Kodu", "Ürün Adı", "Satılan Miktar", "Ciro", "Maliyet", "Kâr"]
        )

        self.tabs.addTab(self.satis_sekme, "Satış Raporu")
        self.tabs.addTab(self.urun_bazli_sekme, "En Çok Satanlar")
        self.tabs.addTab(self.stok_sekme, "Stok Hareketleri")
        self.tabs.addTab(self.borclu_sekme, "Borçlu Müşteriler")
        self.tabs.addTab(self.kar_sekme, "Kâr Raporu")
        layout.addWidget(self.tabs)

    def yenile(self):
        self._yukle(self._bas, self._bit)

    def _filtrele(self, bas: datetime, bit: datetime):
        self._bas = bas
        self._bit = bit
        self._yukle(bas, bit)

    def _yukle(self, bas: datetime, bit: datetime):
        try:
            satislar = rapor_servisi.satis_raporu(bas, bit)
            self.satis_sekme.guncelle([
                [
                    r["fis_no"],
                    tarih_formatla(r["tarih"]),
                    r["musteri_adi"],
                    para_formatla(r["ara_toplam"]),
                    para_formatla(r["kdv_toplam"]),
                    para_formatla(r["genel_toplam"]),
                    r["odeme_tipi"],
                ]
                for r in satislar
            ])

            urun_bazli = rapor_servisi.urun_bazli_satis(bas, bit)
            self.urun_bazli_sekme.guncelle([
                [r["urun_kodu"], r["urun_adi"], miktar_formatla(r["toplam_miktar"]), para_formatla(r["toplam_tutar"])]
                for r in urun_bazli
            ])

            stok = rapor_servisi.stok_hareket_raporu(bas, bit)
            self.stok_sekme.guncelle([
                [
                    tarih_formatla(r["tarih"]),
                    r["urun_kodu"], r["urun_adi"],
                    r["hareket_tipi"],
                    miktar_formatla(r["miktar"]),
                    para_formatla(r["birim_fiyat"]),
                    r["aciklama"],
                ]
                for r in stok
            ])

            borclu = rapor_servisi.borclu_musteriler()
            self.borclu_sekme.guncelle([
                [str(r["id"]), r["musteri"], r["firma"], r["telefon"],
                 para_formatla(r["borc"]), para_formatla(r["bakiye"])]
                for r in borclu
            ])

            kar = rapor_servisi.kar_raporu(bas, bit)
            self.kar_sekme.guncelle([
                [
                    r["urun_kodu"], r["urun_adi"],
                    miktar_formatla(r["toplam_miktar"]),
                    para_formatla(r["ciro"]),
                    para_formatla(r["maliyet"]),
                    para_formatla(r["kar"]),
                ]
                for r in kar
            ])
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Raporlar yüklenemedi: {e}")

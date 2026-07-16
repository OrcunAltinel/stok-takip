"""Satış ekranı — müşteri seçimi, sepet, ödeme ve PDF fiş."""

import os
import tempfile
from decimal import Decimal

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableView, QVBoxLayout, QWidget,
)

from arayuz.bilesenler.para_girisi import ParaGirisi
from servisler import musteri_servisi, satis_servisi, urun_servisi
from veritabani.baglanti import get_session
from veritabani.modeller import Admin, FirmaAyarlari
from yardimcilar.formatlayici import miktar_formatla, para_formatla

_SEPET_SUTUNLARI = ["Kod", "Ürün Adı", "Miktar", "Birim Fiyat", "KDV%", "Satır Toplam"]


class SepetModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._satirlar: list[dict] = []

    def satirlar(self):
        return self._satirlar

    def rowCount(self, p=QModelIndex()):
        return len(self._satirlar)

    def columnCount(self, p=QModelIndex()):
        return len(_SEPET_SUTUNLARI)

    def headerData(self, s, o, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and o == Qt.Orientation.Horizontal:
            return _SEPET_SUTUNLARI[s]

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        s = self._satirlar[idx.row()]
        col = idx.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return s["urun_kodu"]
            if col == 1:
                return s["urun_adi"]
            if col == 2:
                return miktar_formatla(s["miktar"])
            if col == 3:
                return para_formatla(s["birim_fiyat"])
            if col == 4:
                return f"%{s['kdv_orani']}"
            if col == 5:
                return para_formatla(s["satir_toplam"])
        if role == Qt.ItemDataRole.EditRole:
            if col == 2:
                return miktar_formatla(s["miktar"])
        if role == Qt.ItemDataRole.ForegroundRole:
            if s.get("stok_uyari"):
                return QColor("#fab387")
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (2, 3, 4, 5):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def flags(self, idx):
        temel = super().flags(idx)
        if idx.isValid() and idx.column() == 2:
            return temel | Qt.ItemFlag.ItemIsEditable
        return temel

    def setData(self, idx, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not idx.isValid() or idx.column() != 2:
            return False
        try:
            miktar = Decimal(str(value).replace(",", "."))
            if miktar <= 0:
                raise ValueError
        except Exception:
            return False

        s = self._satirlar[idx.row()]
        s["miktar"] = miktar
        fiyat = Decimal(str(s["birim_fiyat"]))
        kdv = Decimal(str(s["kdv_orani"]))
        satis_tutari = (miktar * fiyat).quantize(Decimal("0.01"))
        kdv_tutari = (satis_tutari * kdv / Decimal("100")).quantize(Decimal("0.01"))
        s["satir_toplam"] = satis_tutari + kdv_tutari

        from servisler import urun_servisi
        urun = urun_servisi.urun_bul_id(s["urun_id"])
        s["stok_uyari"] = urun is not None and Decimal(str(urun.stok_miktari)) < miktar

        self.dataChanged.emit(
            self.index(idx.row(), 0), self.index(idx.row(), self.columnCount() - 1)
        )
        return True

    def ekle(self, satir: dict):
        self.beginInsertRows(QModelIndex(), len(self._satirlar), len(self._satirlar))
        self._satirlar.append(satir)
        self.endInsertRows()

    def sil(self, row: int):
        self.beginRemoveRows(QModelIndex(), row, row)
        self._satirlar.pop(row)
        self.endRemoveRows()

    def temizle(self):
        self.beginResetModel()
        self._satirlar.clear()
        self.endResetModel()

    def genel_toplam(self) -> Decimal:
        return sum(Decimal(str(s["satir_toplam"])) for s in self._satirlar)

    def ara_toplam(self) -> Decimal:
        return sum(Decimal(str(s["miktar"])) * Decimal(str(s["birim_fiyat"])) for s in self._satirlar)

    def kdv_toplam(self) -> Decimal:
        return self.genel_toplam() - self.ara_toplam()


class SatisEkrani(QWidget):
    def __init__(self, admin: Admin):
        super().__init__()
        self.admin = admin
        self._musteri = None
        self._urunler_cache: list = []
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        baslik = QLabel("Satış")
        baslik.setObjectName("baslik")
        layout.addWidget(baslik)

        # Müşteri seçimi
        musteri_grup = QGroupBox("Müşteri")
        m_layout = QHBoxLayout(musteri_grup)
        self.musteri_arama = QLineEdit()
        self.musteri_arama.setPlaceholderText("Ad, soyad, telefon veya ID...")
        self.musteri_arama.textChanged.connect(self._musteri_ara)
        self.musteri_combo = QComboBox()
        self.musteri_combo.setMinimumWidth(240)
        self.musteri_combo.currentIndexChanged.connect(self._musteri_secildi)
        self.musteri_bilgi = QLabel("Müşteri seçilmedi (perakende)")
        self.musteri_bilgi.setObjectName("alt_baslik")
        m_layout.addWidget(QLabel("Ara:"))
        m_layout.addWidget(self.musteri_arama)
        m_layout.addWidget(self.musteri_combo, 1)
        m_layout.addWidget(self.musteri_bilgi)
        layout.addWidget(musteri_grup)

        # Ürün ekleme
        urun_grup = QGroupBox("Ürün Ekle")
        u_layout = QHBoxLayout(urun_grup)
        self.urun_arama = QLineEdit()
        self.urun_arama.setPlaceholderText("Ürün kodu, adı veya RAPA kodu...")
        self.urun_arama.textChanged.connect(self._urun_ara)
        self.urun_combo = QComboBox()
        self.urun_combo.setMinimumWidth(200)
        self.urun_combo.currentIndexChanged.connect(self._urun_secildi)
        self.miktar_edit = QLineEdit("1")
        self.miktar_edit.setFixedWidth(60)
        self.fiyat_edit = ParaGirisi()
        self.fiyat_edit.setFixedWidth(110)
        ekle_btn = QPushButton("Sepete Ekle")
        ekle_btn.clicked.connect(self._sepete_ekle)
        u_layout.addWidget(QLabel("Ürün:"))
        u_layout.addWidget(self.urun_arama)
        u_layout.addWidget(self.urun_combo, 1)
        u_layout.addWidget(QLabel("Miktar:"))
        u_layout.addWidget(self.miktar_edit)
        u_layout.addWidget(QLabel("Fiyat:"))
        u_layout.addWidget(self.fiyat_edit)
        u_layout.addWidget(ekle_btn)
        layout.addWidget(urun_grup)

        # Sepet tablosu
        self.sepet_model = SepetModel()
        self.sepet_tablo = QTableView()
        self.sepet_tablo.setModel(self.sepet_model)
        self.sepet_tablo.setAlternatingRowColors(True)
        self.sepet_tablo.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.sepet_tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sepet_tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.sepet_tablo.horizontalHeader().setStretchLastSection(True)
        self.sepet_model.dataChanged.connect(lambda *_: self._toplamları_guncelle())
        layout.addWidget(self.sepet_tablo, 1)

        # Sepet işlemleri + toplamlar
        sepet_alt = QHBoxLayout()
        sil_btn = QPushButton("Seçili Satırı Sil")
        sil_btn.setObjectName("btn_iptal")
        sil_btn.clicked.connect(self._satir_sil)
        temizle_btn = QPushButton("Sepeti Temizle")
        temizle_btn.setObjectName("btn_iptal")
        temizle_btn.clicked.connect(self._sepet_temizle)
        self.ara_toplam_label = QLabel("Ara: —")
        self.kdv_toplam_label = QLabel("KDV: —")
        self.genel_toplam_label = QLabel("Toplam: —")
        sepet_alt.addWidget(sil_btn)
        sepet_alt.addWidget(temizle_btn)
        sepet_alt.addStretch()
        sepet_alt.addWidget(self.ara_toplam_label)
        sepet_alt.addWidget(self.kdv_toplam_label)
        sepet_alt.addWidget(self.genel_toplam_label)
        layout.addLayout(sepet_alt)

        # Ödeme + tamamla
        odeme_grup = QGroupBox("Ödeme")
        odeme_layout = QHBoxLayout(odeme_grup)
        self.odeme_tipi = QComboBox()
        self.odeme_tipi.addItems(["NAKIT", "KART", "CEK", "KARMA"])
        self.odeme_tipi.currentTextChanged.connect(self._odeme_tipi_degisti)
        self.aciklama_edit = QLineEdit()
        self.aciklama_edit.setPlaceholderText("Açıklama (opsiyonel)")
        self.tamamla_btn = QPushButton("Satışı Tamamla")
        self.tamamla_btn.setObjectName("btn_basari")
        self.tamamla_btn.clicked.connect(self._tamamla)
        odeme_layout.addWidget(QLabel("Ödeme Tipi:"))
        odeme_layout.addWidget(self.odeme_tipi)
        odeme_layout.addWidget(QLabel("Açıklama:"))
        odeme_layout.addWidget(self.aciklama_edit, 1)
        odeme_layout.addWidget(self.tamamla_btn)
        layout.addWidget(odeme_grup)

    def yenile(self):
        pass

    def _musteri_ara(self, metin: str):
        self.musteri_combo.blockSignals(True)
        self.musteri_combo.clear()
        eslesenler = musteri_servisi.musteri_ara(metin) if metin else []
        for m in eslesenler:
            self.musteri_combo.addItem(f"#{m.id} {m.ad} {m.soyad}", m.id)
        self.musteri_combo.addItem("— Perakende (müşterisiz) —", None)
        self.musteri_combo.blockSignals(False)
        self.musteri_combo.setCurrentIndex(0)
        self._musteri_secildi(0)

    def _musteri_secildi(self, idx: int):
        musteri_id = self.musteri_combo.currentData()
        if musteri_id:
            self._musteri = musteri_servisi.musteri_bul_id(musteri_id)
            bilgi = f"{self._musteri.ad} {self._musteri.soyad}"
            if self._musteri.firma_adi:
                bilgi += f" — {self._musteri.firma_adi}"
            self.musteri_bilgi.setText(bilgi)
        else:
            self._musteri = None
            self.musteri_bilgi.setText("Müşteri seçilmedi (perakende)")

    def _urun_ara(self, metin: str):
        self._urunler_cache = urun_servisi.urun_ara(metin)
        self.urun_combo.blockSignals(True)
        self.urun_combo.clear()
        for u in self._urunler_cache[:50]:
            self.urun_combo.addItem(f"{u.urun_kodu} — {u.urun_adi}", u.id)
        self.urun_combo.blockSignals(False)
        if self._urunler_cache:
            self._urun_secildi(0)

    def _urun_secildi(self, idx: int):
        if idx < 0 or not self._urunler_cache:
            return
        urun_id = self.urun_combo.currentData()
        for u in self._urunler_cache:
            if u.id == urun_id:
                self.fiyat_edit.deger_ata(Decimal(str(u.satis_fiyati)))
                break

    def _sepete_ekle(self):
        urun_id = self.urun_combo.currentData()
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
        if urun is None:
            return
        fiyat = self.fiyat_edit.deger()
        kdv = Decimal(str(urun.kdv_orani))
        satis_tutari = (miktar * fiyat).quantize(Decimal("0.01"))
        kdv_tutari = (satis_tutari * kdv / Decimal("100")).quantize(Decimal("0.01"))
        stok_uyari = Decimal(str(urun.stok_miktari)) < miktar

        self.sepet_model.ekle({
            "urun_id": urun.id,
            "urun_kodu": urun.urun_kodu,
            "urun_adi": urun.urun_adi,
            "miktar": miktar,
            "birim_fiyat": fiyat,
            "kdv_orani": kdv,
            "satir_toplam": satis_tutari + kdv_tutari,
            "stok_uyari": stok_uyari,
        })
        if stok_uyari:
            QMessageBox.warning(self, "Stok Uyarısı",
                f"{urun.urun_kodu}: Stokta {miktar_formatla(urun.stok_miktari)} {urun.birim} var, "
                f"{miktar_formatla(miktar)} girildi. Yine de satışa devam edebilirsiniz."
            )
        self._toplamları_guncelle()

    def _satir_sil(self):
        idx = self.sepet_tablo.currentIndex()
        if idx.isValid():
            self.sepet_model.sil(idx.row())
            self._toplamları_guncelle()

    def _sepet_temizle(self):
        self.sepet_model.temizle()
        self._toplamları_guncelle()

    def _toplamları_guncelle(self):
        self.ara_toplam_label.setText(f"Ara: {para_formatla(self.sepet_model.ara_toplam())}")
        self.kdv_toplam_label.setText(f"KDV: {para_formatla(self.sepet_model.kdv_toplam())}")
        self.genel_toplam_label.setText(f"Toplam: {para_formatla(self.sepet_model.genel_toplam())}")

    def _odeme_tipi_degisti(self, tip: str):
        pass

    def _tamamla(self):
        if not self.sepet_model.satirlar():
            QMessageBox.warning(self, "Uyarı", "Sepet boş.")
            return

        odeme_tipi = self.odeme_tipi.currentText()
        musteri_id = self._musteri.id if self._musteri else None

        karma_odemeler = None
        if odeme_tipi == "KARMA":
            if not musteri_id:
                QMessageBox.warning(self, "Uyarı", "KARMA ödeme için müşteri seçilmelidir.")
                return
            karma_odemeler = self._karma_ode_dialog()
            if karma_odemeler is None:
                return

        kalemler = [
            {
                "urun_id": s["urun_id"],
                "miktar": s["miktar"],
                "birim_fiyat": s["birim_fiyat"],
                "kdv_orani": s["kdv_orani"],
            }
            for s in self.sepet_model.satirlar()
        ]

        try:
            fis = satis_servisi.fis_olustur(
                admin_id=self.admin.id,
                kalemler=kalemler,
                odeme_tipi=odeme_tipi,
                musteri_id=musteri_id,
                karma_odemeler=karma_odemeler,
                aciklama=self.aciklama_edit.text(),
            )
            self._sepet_temizle()
            self._musteri = None
            self.musteri_combo.setCurrentIndex(0)
            self.musteri_bilgi.setText("Müşteri seçilmedi (perakende)")
            self._pdf_goster(fis.id if hasattr(fis, "id") else None, fis)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _karma_ode_dialog(self):
        dlg = KarmaOdemeDialog(self.sepet_model.genel_toplam(), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.odemeler()
        return None

    def _pdf_goster(self, fis_id, fis):
        try:
            detay = satis_servisi.fis_detay(fis_id) if fis_id else {}
            if not detay:
                QMessageBox.information(self, "Başarılı", "Satış kaydedildi.")
                return
            with get_session() as session:
                ayarlar = session.query(FirmaAyarlari).filter_by(id=1).first()
                firma = {
                    "firma_adi": ayarlar.firma_adi if ayarlar else "",
                    "adres": ayarlar.adres if ayarlar else "",
                    "telefon": ayarlar.telefon if ayarlar else "",
                }
            from yardimcilar.pdf_fis import fis_pdf_olustur
            self._son_pdf_bytes = fis_pdf_olustur(detay, firma)
            self._son_fis_no = detay["fis_no"]

            msg = QMessageBox(self)
            msg.setWindowTitle("Satış Tamamlandı")
            msg.setText(f"Fiş kaydedildi: <b>{detay['fis_no']}</b>")
            msg.setInformativeText(f"Toplam: {para_formatla(detay['genel_toplam'])}")
            msg.setIcon(QMessageBox.Icon.Information)
            yazdir_btn = msg.addButton("Fişi Görüntüle / Yazdır", QMessageBox.ButtonRole.ActionRole)
            msg.addButton("Kapat", QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            if msg.clickedButton() == yazdir_btn:
                self._pdf_ac()
        except Exception as e:
            QMessageBox.warning(self, "PDF Hatası", f"PDF oluşturulamadı: {e}")

    def _pdf_ac(self):
        if not hasattr(self, "_son_pdf_bytes"):
            return
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf",
                                          prefix=f"{self._son_fis_no}_")
        tmp.write(self._son_pdf_bytes)
        tmp.close()
        os.startfile(tmp.name)


class KarmaOdemeDialog(QDialog):
    def __init__(self, toplam: Decimal, parent=None):
        super().__init__(parent)
        self.toplam = toplam
        self.setWindowTitle("KARMA Ödeme Dağılımı")
        self.setFixedSize(420, 300)
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Toplam: {para_formatla(self.toplam)}"))
        layout.addWidget(QLabel("Her ödeme aracı için tutarı girin (0 bırakılanlar dahil edilmez):"))

        form = QFormLayout()
        self.nakit_edit = ParaGirisi()
        self.kart_edit = ParaGirisi()
        self.cek_edit = ParaGirisi()
        form.addRow("Nakit:", self.nakit_edit)
        form.addRow("Kart:", self.kart_edit)
        form.addRow("Çek:", self.cek_edit)
        layout.addLayout(form)

        self.hata = QLabel("")
        self.hata.setObjectName("uyari_etiket")
        layout.addWidget(self.hata)

        btn_satir = QHBoxLayout()
        tamam = QPushButton("Onayla")
        tamam.clicked.connect(self._onayla)
        iptal = QPushButton("İptal")
        iptal.setObjectName("btn_iptal")
        iptal.clicked.connect(self.reject)
        btn_satir.addStretch()
        btn_satir.addWidget(iptal)
        btn_satir.addWidget(tamam)
        layout.addLayout(btn_satir)

    def _onayla(self):
        toplam_girilen = (
            self.nakit_edit.deger() + self.kart_edit.deger() + self.cek_edit.deger()
        )
        if toplam_girilen != self.toplam:
            self.hata.setText(
                f"Girilen toplam ({para_formatla(toplam_girilen)}) "
                f"satış toplamıyla ({para_formatla(self.toplam)}) eşleşmiyor."
            )
            return
        self.accept()

    def odemeler(self) -> list[dict]:
        sonuc = []
        for arac, deger in [
            ("NAKIT", self.nakit_edit.deger()),
            ("KART", self.kart_edit.deger()),
            ("CEK", self.cek_edit.deger()),
        ]:
            if deger > 0:
                sonuc.append({"odeme_araci": arac, "tutar": deger})
        return sonuc

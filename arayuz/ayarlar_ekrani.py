"""Ayarlar ekranı — firma bilgileri, parola değiştirme, yedekleme, tema."""

from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from servisler import auth_servisi, yedek_servisi
from veritabani.baglanti import get_session
from veritabani.modeller import Admin, FirmaAyarlari
from arayuz.tema import tema_al


class AyarlarEkrani(QWidget):
    def __init__(self, admin: Admin):
        super().__init__()
        self.admin = admin
        self._kur()
        self.yenile()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        baslik = QLabel("Ayarlar")
        baslik.setObjectName("baslik")
        layout.addWidget(baslik)

        # Firma bilgileri
        firma_grup = QGroupBox("Firma Bilgileri")
        firma_form = QFormLayout(firma_grup)
        self.firma_adi = QLineEdit()
        self.firma_adres = QLineEdit()
        self.firma_tel = QLineEdit()
        self.firma_vergi_dairesi = QLineEdit()
        self.firma_vergi_no = QLineEdit()
        firma_form.addRow("Firma Adı:", self.firma_adi)
        firma_form.addRow("Adres:", self.firma_adres)
        firma_form.addRow("Telefon:", self.firma_tel)
        firma_form.addRow("Vergi Dairesi:", self.firma_vergi_dairesi)
        firma_form.addRow("Vergi No:", self.firma_vergi_no)
        firma_kaydet_btn = QPushButton("Firma Bilgilerini Kaydet")
        firma_kaydet_btn.setObjectName("btn_basari")
        firma_kaydet_btn.clicked.connect(self._firma_kaydet)
        firma_form.addRow("", firma_kaydet_btn)
        layout.addWidget(firma_grup)

        # Tema
        tema_grup = QGroupBox("Görünüm")
        tema_layout = QHBoxLayout(tema_grup)
        self.tema_combo = QComboBox()
        self.tema_combo.addItem("Koyu Tema", "koyu")
        self.tema_combo.addItem("Açık Tema", "acik")
        tema_uygula_btn = QPushButton("Temayı Uygula")
        tema_uygula_btn.clicked.connect(self._tema_uygula)
        tema_layout.addWidget(QLabel("Tema:"))
        tema_layout.addWidget(self.tema_combo)
        tema_layout.addWidget(tema_uygula_btn)
        tema_layout.addStretch()
        layout.addWidget(tema_grup)

        # Parola değiştirme
        parola_grup = QGroupBox("Parola Değiştir")
        parola_form = QFormLayout(parola_grup)
        self.mevcut_parola = QLineEdit()
        self.mevcut_parola.setEchoMode(QLineEdit.EchoMode.Password)
        self.yeni_parola = QLineEdit()
        self.yeni_parola.setEchoMode(QLineEdit.EchoMode.Password)
        self.yeni_parola_tekrar = QLineEdit()
        self.yeni_parola_tekrar.setEchoMode(QLineEdit.EchoMode.Password)
        self.parola_hata = QLabel("")
        self.parola_hata.setObjectName("uyari_etiket")
        parola_form.addRow("Mevcut Parola:", self.mevcut_parola)
        parola_form.addRow("Yeni Parola:", self.yeni_parola)
        parola_form.addRow("Tekrar:", self.yeni_parola_tekrar)
        parola_form.addRow("", self.parola_hata)
        parola_degistir_btn = QPushButton("Parolayı Değiştir")
        parola_degistir_btn.clicked.connect(self._parola_degistir)
        parola_form.addRow("", parola_degistir_btn)
        layout.addWidget(parola_grup)

        # Yedekleme
        yedek_grup = QGroupBox("Yedekleme")
        yedek_layout = QVBoxLayout(yedek_grup)
        self.yedek_bilgi = QLabel("")
        self.yedek_bilgi.setObjectName("alt_baslik")
        yedek_btn = QPushButton("Şimdi Yedekle")
        yedek_btn.setObjectName("btn_basari")
        yedek_btn.clicked.connect(self._yedek_al)
        yedek_layout.addWidget(self.yedek_bilgi)
        yedek_layout.addWidget(yedek_btn)
        layout.addWidget(yedek_grup)

        layout.addStretch()

    def yenile(self):
        with get_session() as session:
            ayarlar = session.query(FirmaAyarlari).filter_by(id=1).first()
            if ayarlar:
                self.firma_adi.setText(ayarlar.firma_adi or "")
                self.firma_adres.setText(ayarlar.adres or "")
                self.firma_tel.setText(ayarlar.telefon or "")
                self.firma_vergi_dairesi.setText(ayarlar.vergi_dairesi or "")
                self.firma_vergi_no.setText(ayarlar.vergi_no or "")
                idx = self.tema_combo.findData(ayarlar.tema or "koyu")
                if idx >= 0:
                    self.tema_combo.setCurrentIndex(idx)

        yedekler = yedek_servisi.yedek_listesi()
        if yedekler:
            son = yedekler[0]
            from yardimcilar.formatlayici import tarih_kisa_formatla
            import datetime
            mt = datetime.datetime.fromtimestamp(son.stat().st_mtime)
            self.yedek_bilgi.setText(
                f"Son yedek: {son.name} | {mt.strftime('%d.%m.%Y %H:%M')} | "
                f"Toplam: {len(yedekler)} yedek"
            )
        else:
            self.yedek_bilgi.setText("Henüz yedek yok.")

    def _firma_kaydet(self):
        with get_session() as session:
            ayarlar = session.query(FirmaAyarlari).filter_by(id=1).first()
            ayarlar.firma_adi = self.firma_adi.text().strip()
            ayarlar.adres = self.firma_adres.text().strip()
            ayarlar.telefon = self.firma_tel.text().strip()
            ayarlar.vergi_dairesi = self.firma_vergi_dairesi.text().strip()
            ayarlar.vergi_no = self.firma_vergi_no.text().strip()
        QMessageBox.information(self, "Başarılı", "Firma bilgileri kaydedildi.")

    def _tema_uygula(self):
        tema_adi = self.tema_combo.currentData()
        with get_session() as session:
            ayarlar = session.query(FirmaAyarlari).filter_by(id=1).first()
            ayarlar.tema = tema_adi
        app = QApplication.instance()
        if app:
            app.setStyleSheet(tema_al(tema_adi))
        QMessageBox.information(self, "Tema", "Tema uygulandı.")

    def _parola_degistir(self):
        mevcut = self.mevcut_parola.text()
        yeni = self.yeni_parola.text()
        tekrar = self.yeni_parola_tekrar.text()

        if not auth_servisi.mevcut_parola_dogru_mu(self.admin.id, mevcut):
            self.parola_hata.setText("Mevcut parola yanlış.")
            return
        if len(yeni) < 6:
            self.parola_hata.setText("Yeni parola en az 6 karakter olmalıdır.")
            return
        if yeni != tekrar:
            self.parola_hata.setText("Yeni parolalar eşleşmiyor.")
            return

        auth_servisi.parola_degistir(self.admin.id, yeni)
        self.parola_hata.setText("")
        self.mevcut_parola.clear()
        self.yeni_parola.clear()
        self.yeni_parola_tekrar.clear()
        QMessageBox.information(self, "Başarılı", "Parola değiştirildi.")

    def _yedek_al(self):
        try:
            yol = yedek_servisi.yedek_al("manuel")
            self.yenile()
            QMessageBox.information(self, "Yedekleme", f"Yedek alındı:\n{yol.name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

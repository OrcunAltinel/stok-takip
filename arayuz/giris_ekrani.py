"""Giriş ekranı — bcrypt doğrulama, 3 hata → 30s kilit."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from servisler import auth_servisi
from veritabani.modeller import Admin


class ParolaDegistirDialog(QDialog):
    """İlk girişte parola değiştirme zorunluluk ekranı."""

    def __init__(self, admin_id: int, parent=None):
        super().__init__(parent)
        self.admin_id = admin_id
        self.setWindowTitle("Parola Değiştirme Zorunlu")
        self.setFixedSize(380, 260)
        self._kur()

    def _kur(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 24, 30, 24)

        uyari = QLabel("İlk girişinizde parolanızı değiştirmeniz gerekmektedir.")
        uyari.setWordWrap(True)
        uyari.setObjectName("uyari_etiket")
        layout.addWidget(uyari)

        form = QFormLayout()
        form.setSpacing(10)

        self.yeni_parola = QLineEdit()
        self.yeni_parola.setEchoMode(QLineEdit.EchoMode.Password)
        self.yeni_parola.setPlaceholderText("En az 6 karakter")

        self.yeni_parola_tekrar = QLineEdit()
        self.yeni_parola_tekrar.setEchoMode(QLineEdit.EchoMode.Password)
        self.yeni_parola_tekrar.setPlaceholderText("Yeni parolayı tekrar girin")

        form.addRow("Yeni Parola:", self.yeni_parola)
        form.addRow("Tekrar:", self.yeni_parola_tekrar)
        layout.addLayout(form)

        self.hata_label = QLabel("")
        self.hata_label.setObjectName("uyari_etiket")
        layout.addWidget(self.hata_label)

        btn = QPushButton("Parolayı Kaydet")
        btn.clicked.connect(self._kaydet)
        layout.addWidget(btn)

    def _kaydet(self):
        yeni = self.yeni_parola.text()
        tekrar = self.yeni_parola_tekrar.text()
        if len(yeni) < 6:
            self.hata_label.setText("Parola en az 6 karakter olmalıdır.")
            return
        if yeni != tekrar:
            self.hata_label.setText("Parolalar eşleşmiyor.")
            return
        auth_servisi.parola_degistir(self.admin_id, yeni)
        self.accept()


class GirisEkrani(QWidget):
    """Login formu — sinyal: giris_basarili(Admin)"""

    def __init__(self, giris_basarili_cb, parent=None):
        super().__init__(parent)
        self.giris_basarili_cb = giris_basarili_cb
        self._hatali_deneme = 0
        self._kilit_timer = QTimer(self)
        self._kilit_timer.timeout.connect(self._kilit_geri_sayim)
        self._kilit_saniye = 0
        self._kur()

    def _kur(self):
        ana_layout = QVBoxLayout(self)
        ana_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        kart = QWidget()
        kart.setFixedSize(380, 340)
        kart_layout = QVBoxLayout(kart)
        kart_layout.setSpacing(14)
        kart_layout.setContentsMargins(36, 36, 36, 36)

        baslik = QLabel("Stok Takip")
        baslik.setObjectName("baslik")
        baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont()
        f.setPointSize(22)
        f.setBold(True)
        baslik.setFont(f)
        kart_layout.addWidget(baslik)

        alt = QLabel("Oto Yedek Parça Yönetim Sistemi")
        alt.setObjectName("alt_baslik")
        alt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kart_layout.addWidget(alt)
        kart_layout.addSpacing(10)

        form = QFormLayout()
        form.setSpacing(10)

        self.kullanici_adi = QLineEdit()
        self.kullanici_adi.setPlaceholderText("Kullanıcı adı")
        self.kullanici_adi.returnPressed.connect(self._giris_yap)

        self.parola = QLineEdit()
        self.parola.setEchoMode(QLineEdit.EchoMode.Password)
        self.parola.setPlaceholderText("Parola")
        self.parola.returnPressed.connect(self._giris_yap)

        form.addRow("Kullanıcı Adı:", self.kullanici_adi)
        form.addRow("Parola:", self.parola)
        kart_layout.addLayout(form)

        self.hata_label = QLabel("")
        self.hata_label.setObjectName("uyari_etiket")
        self.hata_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hata_label.setWordWrap(True)
        kart_layout.addWidget(self.hata_label)

        self.giris_btn = QPushButton("Giriş Yap")
        self.giris_btn.clicked.connect(self._giris_yap)
        kart_layout.addWidget(self.giris_btn)

        ana_layout.addWidget(kart)

    def _giris_yap(self):
        if not self.giris_btn.isEnabled():
            return
        kadi = self.kullanici_adi.text().strip()
        parola = self.parola.text()
        if not kadi or not parola:
            self.hata_label.setText("Kullanıcı adı ve parola gereklidir.")
            return

        admin = auth_servisi.giris_yap(kadi, parola)
        if admin is None:
            self._hatali_deneme += 1
            kalan = 3 - self._hatali_deneme
            if self._hatali_deneme >= 3:
                self._kilitle()
            else:
                self.hata_label.setText(
                    f"Hatalı kullanıcı adı veya parola. ({kalan} hak kaldı)"
                )
            self.parola.clear()
            return

        self._hatali_deneme = 0
        self.hata_label.setText("")

        if admin.ilk_giris:
            dlg = ParolaDegistirDialog(admin.id, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

        self.giris_basarili_cb(admin)

    def _kilitle(self):
        self._kilit_saniye = 30
        self.giris_btn.setEnabled(False)
        self.kullanici_adi.setEnabled(False)
        self.parola.setEnabled(False)
        self._kilit_timer.start(1000)
        self.hata_label.setText(f"Çok fazla hatalı giriş. 30 saniye bekleyin...")

    def _kilit_geri_sayim(self):
        self._kilit_saniye -= 1
        if self._kilit_saniye <= 0:
            self._kilit_timer.stop()
            self.giris_btn.setEnabled(True)
            self.kullanici_adi.setEnabled(True)
            self.parola.setEnabled(True)
            self.hata_label.setText("")
            self._hatali_deneme = 0
        else:
            self.hata_label.setText(
                f"Çok fazla hatalı giriş. {self._kilit_saniye} saniye bekleyin..."
            )

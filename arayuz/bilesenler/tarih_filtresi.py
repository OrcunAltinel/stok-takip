"""Tarih aralığı filtresi bileşeni — Bugün/Hafta/Ay/Özel seçenekleri."""

from datetime import datetime, timedelta

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QDateEdit, QHBoxLayout, QLabel, QPushButton, QWidget,
)


class TarihFiltresi(QWidget):
    """Tarih aralığı seçici; degisti sinyali (baslangic, bitis) datetime tuple yayınlar."""

    degisti = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._kur()

    def _kur(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for etiket, slot in [
            ("Bugün", self._bugun),
            ("Bu Hafta", self._bu_hafta),
            ("Bu Ay", self._bu_ay),
        ]:
            btn = QPushButton(etiket)
            btn.setFixedHeight(28)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        layout.addWidget(QLabel("Özel:"))
        self.baslangic_edit = QDateEdit()
        self.baslangic_edit.setCalendarPopup(True)
        self.baslangic_edit.setDisplayFormat("dd.MM.yyyy")
        self.baslangic_edit.setDate(QDate.currentDate().addDays(-30))

        self.bitis_edit = QDateEdit()
        self.bitis_edit.setCalendarPopup(True)
        self.bitis_edit.setDisplayFormat("dd.MM.yyyy")
        self.bitis_edit.setDate(QDate.currentDate())

        layout.addWidget(self.baslangic_edit)
        layout.addWidget(QLabel("–"))
        layout.addWidget(self.bitis_edit)

        uygula = QPushButton("Uygula")
        uygula.setFixedHeight(28)
        uygula.clicked.connect(self._ozel_uygula)
        layout.addWidget(uygula)
        layout.addStretch()

    def aralik(self) -> tuple[datetime, datetime]:
        bas = self.baslangic_edit.date().toPython()
        bit = self.bitis_edit.date().toPython()
        return (
            datetime(bas.year, bas.month, bas.day, 0, 0, 0),
            datetime(bit.year, bit.month, bit.day, 23, 59, 59),
        )

    def _bugun(self):
        bugun = datetime.now()
        bas = bugun.replace(hour=0, minute=0, second=0, microsecond=0)
        bit = bugun.replace(hour=23, minute=59, second=59, microsecond=0)
        self._guncelle(bas, bit)

    def _bu_hafta(self):
        bugun = datetime.now()
        bas = (bugun - timedelta(days=bugun.weekday())).replace(hour=0, minute=0, second=0)
        bit = bugun.replace(hour=23, minute=59, second=59)
        self._guncelle(bas, bit)

    def _bu_ay(self):
        bugun = datetime.now()
        bas = bugun.replace(day=1, hour=0, minute=0, second=0)
        bit = bugun.replace(hour=23, minute=59, second=59)
        self._guncelle(bas, bit)

    def _ozel_uygula(self):
        bas, bit = self.aralik()
        self.degisti.emit(bas, bit)

    def _guncelle(self, bas: datetime, bit: datetime):
        from PySide6.QtCore import QDate
        self.baslangic_edit.setDate(QDate(bas.year, bas.month, bas.day))
        self.bitis_edit.setDate(QDate(bit.year, bit.month, bit.day))
        self.degisti.emit(bas, bit)

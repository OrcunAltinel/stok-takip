"""Decimal para girişi için özelleştirilmiş QLineEdit."""

import re
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QRegularExpression, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QLineEdit


class ParaGirisi(QLineEdit):
    """Yalnızca ondalıklı sayı kabul eder; değer Decimal olarak alınır."""

    deger_degisti = Signal(object)  # Decimal

    def __init__(self, varsayilan: Decimal = Decimal("0.00"), parent=None):
        super().__init__(parent)
        self.setPlaceholderText("0,00")
        rx = QRegularExpression(r"^\d{0,12}([.,]\d{0,2})?$")
        self.setValidator(QRegularExpressionValidator(rx, self))
        self.setText(str(varsayilan).replace(".", ","))
        self.textChanged.connect(self._degeri_yayinla)

    def deger(self) -> Decimal:
        metin = self.text().replace(",", ".").strip()
        try:
            return Decimal(metin) if metin else Decimal("0.00")
        except InvalidOperation:
            return Decimal("0.00")

    def deger_ata(self, tutar: Decimal):
        self.setText(str(tutar).replace(".", ","))

    def _degeri_yayinla(self):
        self.deger_degisti.emit(self.deger())

"""SQLAlchemy ORM modelleri — tüm veritabanı tabloları."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Admin(Base):
    __tablename__ = "adminler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kullanici_adi = Column(String(50), unique=True, nullable=False)
    parola_hash = Column(String(255), nullable=False)
    ad_soyad = Column(String(100), nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.now)
    aktif = Column(Boolean, default=True, nullable=False)
    silinme_tarihi = Column(DateTime, nullable=True)
    ilk_giris = Column(Boolean, default=True, nullable=False)


class Musteri(Base):
    __tablename__ = "musteriler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ad = Column(String(50), nullable=False)
    soyad = Column(String(50), nullable=False)
    firma_adi = Column(String(150), nullable=True)
    telefon = Column(String(20), nullable=True)
    adres = Column(Text, nullable=True)
    bolge = Column(String(50), nullable=True)
    ilce = Column(String(50), nullable=True)
    vergi_no = Column(String(20), nullable=True)
    bakiye = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    borc = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    notlar = Column(Text, nullable=True)
    kayit_tarihi = Column(DateTime, default=datetime.now)
    aktif = Column(Boolean, default=True, nullable=False)
    silinme_tarihi = Column(DateTime, nullable=True)

    satislar = relationship("SatisFisi", back_populates="musteri")
    iadeler = relationship("IadeFisi", back_populates="musteri")
    odemeler = relationship("Odeme", back_populates="musteri")


class Tedarikci(Base):
    __tablename__ = "tedarikciler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firma_adi = Column(String(150), nullable=False)
    yetkili_adi = Column(String(100), nullable=True)
    telefon = Column(String(20), nullable=True)
    adres = Column(Text, nullable=True)
    notlar = Column(Text, nullable=True)
    kayit_tarihi = Column(DateTime, default=datetime.now)
    aktif = Column(Boolean, default=True, nullable=False)
    silinme_tarihi = Column(DateTime, nullable=True)

    stok_hareketleri = relationship("StokHareketi", back_populates="tedarikci")


class Urun(Base):
    __tablename__ = "urunler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    urun_kodu = Column(String(50), unique=True, nullable=False)
    urun_adi = Column(String(200), nullable=False)
    oem_no = Column(String(100), nullable=True)
    marka = Column(String(100), nullable=True)
    kategori = Column(String(100), nullable=True)
    birim = Column(String(20), default="adet", nullable=False)
    alis_fiyati = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    satis_fiyati = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    kdv_orani = Column(Numeric(precision=5, scale=2), default=Decimal("20.00"), nullable=False)
    stok_miktari = Column(Numeric(precision=12, scale=3), default=Decimal("0.000"), nullable=False)
    kritik_stok_seviyesi = Column(Numeric(precision=12, scale=3), default=Decimal("5.000"), nullable=False)
    raf_adresi = Column(String(50), nullable=True)
    kayit_tarihi = Column(DateTime, default=datetime.now)
    aktif = Column(Boolean, default=True, nullable=False)
    silinme_tarihi = Column(DateTime, nullable=True)

    stok_hareketleri = relationship("StokHareketi", back_populates="urun")
    satis_kalemleri = relationship("SatisKalemi", back_populates="urun")
    iade_kalemleri = relationship("IadeKalemi", back_populates="urun")


class StokHareketi(Base):
    __tablename__ = "stok_hareketleri"

    id = Column(Integer, primary_key=True, autoincrement=True)
    urun_id = Column(Integer, ForeignKey("urunler.id"), nullable=False)
    hareket_tipi = Column(String(20), nullable=False)  # GIRIS / CIKIS / IADE_GIRIS / SAYIM_DUZELTME
    miktar = Column(Numeric(precision=12, scale=3), nullable=False)
    birim_fiyat = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    tedarikci_id = Column(Integer, ForeignKey("tedarikciler.id"), nullable=True)
    satis_fisi_id = Column(Integer, ForeignKey("satis_fisleri.id"), nullable=True)
    aciklama = Column(Text, nullable=True)
    tarih = Column(DateTime, default=datetime.now)
    admin_id = Column(Integer, ForeignKey("adminler.id"), nullable=False)

    urun = relationship("Urun", back_populates="stok_hareketleri")
    tedarikci = relationship("Tedarikci", back_populates="stok_hareketleri")
    admin = relationship("Admin")


class SatisFisi(Base):
    __tablename__ = "satis_fisleri"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fis_no = Column(String(20), unique=True, nullable=False)
    musteri_id = Column(Integer, ForeignKey("musteriler.id"), nullable=True)
    tarih = Column(DateTime, default=datetime.now)
    ara_toplam = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    kdv_toplam = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    genel_toplam = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    odeme_tipi = Column(String(20), nullable=False)  # NAKIT / KART / BAKIYE / VERESIYE / KARMA
    durum = Column(String(20), default="TAMAMLANDI", nullable=False)  # TAMAMLANDI / IPTAL
    aciklama = Column(Text, nullable=True)
    admin_id = Column(Integer, ForeignKey("adminler.id"), nullable=False)

    musteri = relationship("Musteri", back_populates="satislar")
    admin = relationship("Admin")
    kalemler = relationship("SatisKalemi", back_populates="satis_fisi", cascade="all, delete-orphan")
    stok_hareketleri = relationship("StokHareketi", foreign_keys=[StokHareketi.satis_fisi_id])
    odemeler = relationship("Odeme", foreign_keys="Odeme.iliskili_fis_id")


class SatisKalemi(Base):
    __tablename__ = "satis_kalemleri"

    id = Column(Integer, primary_key=True, autoincrement=True)
    satis_fisi_id = Column(Integer, ForeignKey("satis_fisleri.id"), nullable=False)
    urun_id = Column(Integer, ForeignKey("urunler.id"), nullable=False)
    miktar = Column(Numeric(precision=12, scale=3), nullable=False)
    birim_fiyat = Column(Numeric(precision=12, scale=2), nullable=False)
    kdv_orani = Column(Numeric(precision=5, scale=2), nullable=False)
    satir_toplam = Column(Numeric(precision=12, scale=2), nullable=False)

    satis_fisi = relationship("SatisFisi", back_populates="kalemler")
    urun = relationship("Urun", back_populates="satis_kalemleri")


class IadeFisi(Base):
    __tablename__ = "iade_fisleri"

    id = Column(Integer, primary_key=True, autoincrement=True)
    iade_no = Column(String(20), unique=True, nullable=False)
    orijinal_fis_id = Column(Integer, ForeignKey("satis_fisleri.id"), nullable=False)
    musteri_id = Column(Integer, ForeignKey("musteriler.id"), nullable=True)
    tarih = Column(DateTime, default=datetime.now)
    toplam_tutar = Column(Numeric(precision=12, scale=2), default=Decimal("0.00"), nullable=False)
    iade_yontemi = Column(String(20), nullable=False)  # NAKIT_ODE / BAKIYEYE_EKLE / BORCTAN_DUS
    aciklama = Column(Text, nullable=True)
    admin_id = Column(Integer, ForeignKey("adminler.id"), nullable=False)

    orijinal_fis = relationship("SatisFisi")
    musteri = relationship("Musteri", back_populates="iadeler")
    admin = relationship("Admin")
    kalemler = relationship("IadeKalemi", back_populates="iade_fisi", cascade="all, delete-orphan")


class IadeKalemi(Base):
    __tablename__ = "iade_kalemleri"

    id = Column(Integer, primary_key=True, autoincrement=True)
    iade_fisi_id = Column(Integer, ForeignKey("iade_fisleri.id"), nullable=False)
    urun_id = Column(Integer, ForeignKey("urunler.id"), nullable=False)
    miktar = Column(Numeric(precision=12, scale=3), nullable=False)
    birim_fiyat = Column(Numeric(precision=12, scale=2), nullable=False)
    satir_toplam = Column(Numeric(precision=12, scale=2), nullable=False)

    iade_fisi = relationship("IadeFisi", back_populates="kalemler")
    urun = relationship("Urun", back_populates="iade_kalemleri")


class Odeme(Base):
    __tablename__ = "odemeler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    musteri_id = Column(Integer, ForeignKey("musteriler.id"), nullable=False)
    islem_tipi = Column(String(20), nullable=False)  # TAHSILAT / BAKIYE_YUKLEME / SATIS_BORC / IADE_ALACAK
    tutar = Column(Numeric(precision=12, scale=2), nullable=False)
    odeme_araci = Column(String(20), nullable=True)  # NAKIT / KART / BAKIYE
    iliskili_fis_id = Column(Integer, ForeignKey("satis_fisleri.id"), nullable=True)
    tarih = Column(DateTime, default=datetime.now)
    aciklama = Column(Text, nullable=True)
    admin_id = Column(Integer, ForeignKey("adminler.id"), nullable=False)

    musteri = relationship("Musteri", back_populates="odemeler")
    admin = relationship("Admin")


class FirmaAyarlari(Base):
    __tablename__ = "firma_ayarlari"

    id = Column(Integer, primary_key=True, default=1)
    firma_adi = Column(String(200), default="")
    adres = Column(Text, default="")
    telefon = Column(String(50), default="")
    vergi_dairesi = Column(String(100), default="")
    vergi_no = Column(String(20), default="")
    tema = Column(String(10), default="koyu")
    demo_yuklendi = Column(Boolean, default=False)

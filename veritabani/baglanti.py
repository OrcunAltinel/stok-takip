"""Veritabanı bağlantısı, session yönetimi ve ilk kurulum."""

import os
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import bcrypt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from veritabani.modeller import (
    Admin, Base, FirmaAyarlari, Musteri, Tedarikci, Urun,
)

_PROJE_DIZIN = Path(__file__).parent.parent
DB_DIZIN = _PROJE_DIZIN / "veritabani"
DB_YOL = DB_DIZIN / "stok_takip.db"

DB_DIZIN.mkdir(exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_YOL}",
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _sqlite_ayarla(dbapi_connection, connection_record):
    dbapi_connection.execute("PRAGMA journal_mode=WAL")
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_session() -> Session:
    """Transaction yönetimli session context manager."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def veritabani_olustur():
    """Tabloları oluşturur ve ilk veriyi yükler."""
    Base.metadata.create_all(engine)
    from veritabani.migrasyonlar import tum_migrasyonlari_calistir
    tum_migrasyonlari_calistir(engine)
    with get_session() as session:
        _admin_seed(session)
        _firma_ayarlari_seed(session)
        session.flush()
        ayarlar = session.query(FirmaAyarlari).filter_by(id=1).first()
        if ayarlar and not ayarlar.demo_yuklendi:
            demo_veri_yukle(session)
            ayarlar.demo_yuklendi = True


def _admin_seed(session: Session):
    """Varsayılan admin hesabı yoksa oluşturur."""
    var_mi = session.query(Admin).filter_by(kullanici_adi="admin").first()
    if var_mi:
        return
    parola_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
    admin = Admin(
        kullanici_adi="admin",
        parola_hash=parola_hash,
        ad_soyad="Sistem Yöneticisi",
        ilk_giris=True,
    )
    session.add(admin)


def _firma_ayarlari_seed(session: Session):
    """Firma ayarları kaydı yoksa boş kayıt oluşturur."""
    var_mi = session.query(FirmaAyarlari).filter_by(id=1).first()
    if not var_mi:
        session.add(FirmaAyarlari(id=1))


def demo_veri_yukle(session: Session):
    """İlk çalıştırmada örnek veri yükler."""
    tedarikci = Tedarikci(
        firma_adi="Oto Parça Toptan A.Ş.",
        yetkili_adi="Mehmet Demir",
        telefon="0212 555 00 01",
        adres="İkitelli OSB, İstanbul",
    )
    session.add(tedarikci)
    session.flush()

    urunler = [
        Urun(
            urun_kodu="DA-9809P",
            urun_adi="Balata Ön Takım",
            oem_no="45022-SDA-A00",
            marka="TRW",
            kategori="Fren Sistemi",
            birim="takım",
            alis_fiyati=Decimal("280.00"),
            satis_fiyati=Decimal("420.00"),
            kdv_orani=Decimal("20.00"),
            stok_miktari=Decimal("24.000"),
            kritik_stok_seviyesi=Decimal("5.000"),
            raf_adresi="A-01",
        ),
        Urun(
            urun_kodu="FR-1122",
            urun_adi="Yağ Filtresi",
            oem_no="15400-PCX-004",
            marka="Bosch",
            kategori="Filtreler",
            birim="adet",
            alis_fiyati=Decimal("45.00"),
            satis_fiyati=Decimal("85.00"),
            kdv_orani=Decimal("20.00"),
            stok_miktari=Decimal("60.000"),
            kritik_stok_seviyesi=Decimal("10.000"),
            raf_adresi="B-03",
        ),
        Urun(
            urun_kodu="SP-4411",
            urun_adi="Ateşleme Buji Takımı",
            oem_no="NGK-BKR6E",
            marka="NGK",
            kategori="Ateşleme",
            birim="takım",
            alis_fiyati=Decimal("120.00"),
            satis_fiyati=Decimal("210.00"),
            kdv_orani=Decimal("20.00"),
            stok_miktari=Decimal("15.000"),
            kritik_stok_seviyesi=Decimal("5.000"),
            raf_adresi="C-02",
        ),
        Urun(
            urun_kodu="AM-0050",
            urun_adi="Amortisör Ön Sol",
            oem_no="51605-SNA-A05",
            marka="Monroe",
            kategori="Süspansiyon",
            birim="adet",
            alis_fiyati=Decimal("650.00"),
            satis_fiyati=Decimal("950.00"),
            kdv_orani=Decimal("20.00"),
            stok_miktari=Decimal("3.000"),
            kritik_stok_seviyesi=Decimal("4.000"),
            raf_adresi="D-01",
        ),
        Urun(
            urun_kodu="HV-7721",
            urun_adi="Motor Yağı 5W-40 (4 lt)",
            oem_no=None,
            marka="Castrol",
            kategori="Yağlar",
            birim="litre",
            alis_fiyati=Decimal("380.00"),
            satis_fiyati=Decimal("580.00"),
            kdv_orani=Decimal("20.00"),
            stok_miktari=Decimal("40.000"),
            kritik_stok_seviyesi=Decimal("8.000"),
            raf_adresi="E-05",
        ),
    ]
    for u in urunler:
        session.add(u)

    musteriler = [
        Musteri(
            ad="Ahmet",
            soyad="Yılmaz",
            firma_adi="Yılmaz Oto Servis",
            telefon="0532 100 20 30",
            bolge="İstanbul",
            ilce="Bağcılar",
        ),
        Musteri(
            ad="Fatma",
            soyad="Kaya",
            telefon="0544 200 30 40",
            bolge="İstanbul",
            ilce="Küçükçekmece",
        ),
    ]
    for m in musteriler:
        session.add(m)

"""pytest fixtures — in-memory SQLite ile temiz session."""

import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from veritabani.modeller import Base, Admin, FirmaAyarlari
import bcrypt


@pytest.fixture(scope="function")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture(scope="function")
def session(engine):
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture(scope="function")
def admin(session):
    parola_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
    a = Admin(kullanici_adi="admin", parola_hash=parola_hash, ad_soyad="Test Admin", ilk_giris=False)
    session.add(a)
    session.add(FirmaAyarlari(id=1))
    session.commit()
    return a

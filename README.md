# Oto Yedek Parça Stok Takip Sistemi

Windows masaüstü uygulaması — PySide6 + SQLite + SQLAlchemy.

## Gereksinimler

- Python 3.12+
- Windows 10/11

## Kurulum

```bash
cd C:\Users\DC\Desktop\stok
pip install -r requirements.txt
```

## Çalıştırma

```bash
python main.py
```

İlk çalıştırmada:
- Veritabanı `veritabani/stok_takip.db` oluşturulur
- Varsayılan admin: kullanıcı adı `admin`, parola `admin123`
- İlk girişte parola değiştirme zorunlu
- Demo veriler otomatik yüklenir (5 ürün, 2 müşteri, 1 tedarikçi)

## Testleri Çalıştırma

```bash
pip install pytest
pytest testler/ -v
```

## PyInstaller ile Tek EXE Oluşturma

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "StokTakip" main.py
```

Çıktı: `dist/StokTakip.exe`

> **Not:** EXE'nin yanında `veritabani/` klasörü de olmalıdır.
> Taşınabilir paket için `--add-data "veritabani;veritabani"` ekleyin.

```bash
pyinstaller --onefile --windowed --name "StokTakip" \
  --add-data "veritabani;veritabani" \
  main.py
```

## Proje Yapısı

```
stok/
├── main.py                  # Giriş noktası
├── veritabani/
│   ├── modeller.py          # SQLAlchemy ORM tabloları
│   └── baglanti.py          # Engine, session, seed
├── servisler/               # İş mantığı katmanı (arayüzden bağımsız)
│   ├── auth_servisi.py
│   ├── urun_servisi.py
│   ├── stok_servisi.py
│   ├── musteri_servisi.py
│   ├── satis_servisi.py
│   ├── iade_servisi.py
│   ├── rapor_servisi.py
│   └── yedek_servisi.py
├── arayuz/                  # PySide6 ekranları
│   ├── tema.py              # Koyu/açık tema
│   ├── ana_pencere.py
│   ├── giris_ekrani.py
│   ├── ana_panel.py
│   ├── urunler_ekrani.py
│   ├── stok_giris_ekrani.py
│   ├── satis_ekrani.py
│   ├── musteriler_ekrani.py
│   ├── cari_ekstre_ekrani.py
│   ├── iade_ekrani.py
│   ├── raporlar_ekrani.py
│   └── ayarlar_ekrani.py
├── yardimcilar/
│   ├── pdf_fis.py           # A4 PDF fiş (reportlab)
│   ├── excel_aktar.py       # xlsx dışa aktarım
│   └── formatlayici.py      # Para ve tarih formatlama
├── testler/                 # pytest testleri
└── yedekler/                # Otomatik DB yedekleri (runtime)
```

## Özellikler

- Koyu/Açık tema (Ayarlar'dan değiştirilebilir)
- Satış fişi: NAKIT, KART, BAKIYE, VERESİYE, KARMA ödeme
- Müşteri cari ekstresi (Netsis benzeri)
- 5 rapor tipi + Excel aktarımı
- A4 PDF fiş (os.startfile ile önizleme)
- Otomatik yedekleme (uygulama kapanışında, son 30 yedek)
- Soft delete (hiçbir kayıt kalıcı silinmez)
- Tüm para işlemleri `Decimal` ile (float kullanılmaz)

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Komutlar

```bash
# Uygulamayı çalıştır (Python launcher kullan — `python` PATH'te değil)
py main.py

# Tüm testler
py -m pytest testler/ -v

# Tek test dosyası
py -m pytest testler/test_satis.py -v

# Tek test fonksiyonu
py -m pytest testler/test_satis.py::test_nakit_satis_stok_dusuyor -v

# Bağımlılıkları kur
py -m pip install -r requirements.txt
```

## Mimari

### Katman Ayrımı (Kesinlikle Korunmalı)
`servisler/` iş mantığını içerir; `arayuz/` yalnızca servis metodlarını çağırır. `arayuz/` içinde hiçbir SQLAlchemy/ORM kodu bulunmaz.

```
main.py  →  arayuz/  →  servisler/  →  veritabani/
```

### Session Yönetimi
Tüm veritabanı işlemleri `veritabani/baglanti.py`'deki `get_session()` context manager üzerinden yapılır. `autoflush=False` olduğundan, aynı session içinde eklenen nesneleri sorgulamadan önce `session.flush()` çağrılmalıdır. Her servis metodu kendi `with get_session()` bloğunu açar; session'dan döndürülen ORM nesneleri `session.expunge()` ile detach edilir.

### Arayüz Sayfa Yönetimi
`arayuz/ana_pencere.py` bir `QStackedWidget` üzerinden sayfaları yönetir. Sayfalar lazy olarak yüklenir (`_sayfa_yukle`). Her ekran `yenile()` metodunu implemente ederse, sayfa değişiminde otomatik çağrılır.

### Stok Değişikliği
Stok miktarı asla doğrudan güncellenmez; her değişiklik bir `StokHareketi` kaydı ile birlikte yapılır. Tipler: `GIRIS`, `CIKIS`, `IADE_GIRIS`, `SAYIM_DUZELTME`. Eksi stoka izin verilir (gerçek hayat gereği).

### Para
Tüm tutarlar `decimal.Decimal` — float kullanılmaz. Veritabanında `Numeric(precision=12, scale=2)`. Gösterim için `yardimcilar/formatlayici.py::para_formatla()` kullanılır (örn. `1.457.536,00 ₺`).

### Soft Delete
Hiçbir kayıt kalıcı silinmez. Her tabloda `aktif=True/False` ve `silinme_tarihi` alanı vardır. Tüm sorgularda `.filter(Model.aktif == True)` filtresi uygulanır.

### Fiş/İade Numaraları
`SF-{yıl}-{sıra:06d}` ve `IF-{yıl}-{sıra:06d}` formatı. Her yıl 000001'den başlar. Üretim `satis_servisi._sonraki_fis_no()` ve `iade_servisi._sonraki_iade_no()` içindedir.

## İsimlendirme Kuralları

Tüm değişken, fonksiyon, sınıf ve tablo adları Türkçe, ASCII uyumlu yazılır:
- `musteri` (müşteri), `urun` (ürün), `satis_fisi`, `odeme`, `tedarikci`
- Model sınıfları PascalCase: `SatisFisi`, `StokHareketi`, `IadeFisi`
- Servis fonksiyonları snake_case: `fis_olustur`, `stok_girisi_kaydet`

## Testler

`testler/conftest.py` in-memory SQLite kullanır; servis katmanının `get_session()` global engine'ini bypass eden `session` fixture'ı ile çalışır. Bu nedenle testler servis metodlarını **doğrudan çağıramaz** (farklı engine kullanırlar) — ORM nesnelerini manuel oluşturarak model davranışını test ederler.

## Önemli Kısıtlamalar

- **Ödeme yöntemleri**: Satış anında sadece NAKIT, KART, CEK veya bunların KARMA kombinasyonu ile ödeme alınır. Borç/veresiye ve müşteri bakiyesi (ön ödeme/cari hesap) kavramları yoktur — `Musteri` modelinde `borc`/`bakiye` alanı bulunmaz.
- **KARMA ödeme**: Tutarlar toplamı `genel_toplam`'a tam eşit olmalı; her araç (NAKIT/KART/CEK) için ayrı `Odeme` kaydı (`islem_tipi="SATIS_ODEME"`) düşülür. KARMA satış için müşteri seçilmesi zorunludur (`Odeme.musteri_id` NOT NULL).
- **İade → Stok**: `iade_servisi.iade_olustur()` her kalem için otomatik `IADE_GIRIS` stok hareketi oluşturur ve `stok_miktari`'nı artırır. İade yöntemi (`NAKIT_ODE`/`KART_ODE`/`CEK_ODE`) sadece bilgi amaçlıdır, müşteri bakiyesini etkilemez.
- **Müşteri geçmişi**: `musteri_servisi.cari_hareketler()` müşterinin satış (`SatisFisi`) ve iade (`IadeFisi`) kayıtlarını doğrudan sorgulayıp kronolojik döner; ayrı bir borç/bakiye defteri tutulmaz.
- **Yedekleme**: `yedek_servisi.otomatik_yedek_al()` `AnaPencere.closeEvent()` içinde çağrılır; son 30 yedek `yedekler/` klasöründe tutulur.

## BİLİNEN SORUN — BİR SONRAKİ SESSION'DA ÇÖZÜLECEK

**Hata**: İade ekranında "Fişi Getir" butonuna basınca çöküyor:
```
File "servisler\iade_servisi.py", line 122, in fis_kalemleri_getir
    m = session.query(Musteri).filter_by(id=fis.musteri_id).first()
NameError: name 'Musteri' is not defined
```

**Sebep**: Borç/veresiye/bakiye kaldırma refaktöründe `servisler/iade_servisi.py` içindeki `Musteri` importu "artık kullanılmıyor" sanılarak silindi, ama `fis_kalemleri_getir()` fonksiyonu müşteri adını göstermek için hâlâ `Musteri` modelini kullanıyor.

**Çözüm**: `servisler/iade_servisi.py` dosyasının import satırına `Musteri`'yi geri ekle:
```python
from veritabani.modeller import (
    IadeFisi, IadeKalemi, Musteri, SatisFisi, StokHareketi, Urun,
)
```

**ÖNEMLİ — bu bölümü çözdükten sonra bu "BİLİNEN SORUN" bölümünü CLAUDE.md'den tamamen sil.**

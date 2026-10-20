# 📦 QNB eSolutions - e-Fatura & Konşimento Otomatik Eşleştirici

**Firma:** Doğruer Gümrük Müşavirliği A.Ş.  
**Müşteri:** Hankook Lastikleri A.Ş.  
**Sürüm:** 2.0 (Canlı Hedef Sayacı, Akıllı Sayfalama, Birleşik PDF & Excel Çıktısı)

---

## 🎯 Ne İşe Yarar?
QNB eSolutions (`https://portal.qnbesolutions.com.tr`) portalında firmanıza gelen yüzlerce e-fatura arasından, **hangi faturanın sizin aktif işlerinize (konşimento / beyanname / referans no) ait olduğunu otomatik olarak tespit eder**.

Eskiden her faturayı tek tek büyüteçle açıp alta inerek konşimento kontrolü yapmak **2-3 saat** sürerken, bu araç ile **20-30 saniyede** tüm sayfalar taranır ve bize ait olan faturalar tek bir sonuç tablosunda listelenir.

---

## 🚀 Başlıca Özellikler

1. **Çoklu Arama Desteği (Serbest Format):**
   - **Konşimento (BL No):** `HLCUSEL260665279`, `MEDUKC610616`, `ONEYSELG51548500` vb. (Ön ekleri otomatik normalize eder).
   - **Gümrük Beyanname / Tescil No:** `26410300IM00103169` vb.
   - **PO / Referans No:** `4200782901` vb.
   - **Konteyner No:** `MSMU7098488` vb.
2. **Akıllı Sayfalama (Multi-Page Navigation):**
   - Sayfa 1'den 9'a (veya son sayfaya) kadar portaldeki tüm sayfaları otomatik olarak gezer.
   - QNB sunucusu yavaş yüklendiğinde akıllıca bekler (`Smart Wait`), asla durmaz veya hata vermez.
3. **🎯 Hedef Odaklı Erken Durma:**
   - Örneğin 15 adet konşimento yapıştırdıysanız ve hepsi 3. sayfada bulunduysa, gereksiz yere kalan sayfaları taramadan anında durur.
4. **📊 Canlı İlerleme Çubuğu & Sayaç:**
   - Ekranda canlı olarak `🎯 Bulunan Faturalar: 5 / 15 (%33)` şeklinde görsel sayaç ve ilerleme çubuğu gösterir.
5. **📑 Birleşik Tek PDF Olarak İndirme:**
   - Tespit edilen tüm faturaların orijinal e-fatura şablonlarını alt alta birleştirir ve tek tıkla **tek bir A4 PDF dosyası** olarak kaydetmenizi sağlar.
6. **📊 Excel (CSV) Raporu:**
   - Tespit edilen faturaları Fatura No, Dosya No, Konşimento, Referans No ve Gönderen Firma bilgileriyle Excel formatında indirir.

---

## 🛠️ Kurulum ve Kullanım Yolları

### YÖNTEM 1: Tarayıcı Yer İmi (Bookmarklet - Tavsiye Edilen)
1. Tarayıcınızda (Edge / Chrome) `Ctrl + Shift + B` yaparak **Sık Kullanılanlar Çubuğu**'nu açın.
2. Çubuğa **sağ tıklayın** -> **Sayfa Ekle** (veya *Sık Kullanılan Ekle*) deyin.
3. **Ad:** `⚡ Fatura Eşleştirici`
4. **URL:** [`bookmarklet_kodu.txt`](./bookmarklet_kodu.txt) dosyasındaki tek satırlık kodu yapıştırın ve kaydedin.
5. QNB sekmesindeyken bu butona **1 kez basmanız yeterlidir!**

### YÖNTEM 2: Geliştirici Konsolu (F12)
1. QNB portalındayken klavyeden `F12` tuşuna basın.
2. **Console** sekmesine [`fatura_eslestirici.js`](./fatura_eslestirici.js) dosyasındaki kodun tamamını yapıştırıp `Enter`'a basın.

---

## 📂 Dosya Yapısı
- [`fatura_eslestirici.js`](./fatura_eslestirici.js) -> Açıklamalı ve temiz kaynak kod.
- [`bookmarklet_kodu.txt`](./bookmarklet_kodu.txt) -> Tarayıcı yer imine yapıştırılmaya hazır tek satır kod.
- [`README.md`](./README.md) -> Bu dokümantasyon dosyası.

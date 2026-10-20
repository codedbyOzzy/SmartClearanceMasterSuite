# HANKOOK GÜMRÜK OTONOMİSİ VE OPERASYON MASASI — AI ASİSTAN BRİFİNGİ

Bu doküman, Doğruer Gümrük Müşavirliği bünyesinde yürütülen **Hankook Lastikleri İthalat Gümrük Süreci** ve bu süreci yöneten **Hankook Operasyon Masası** yazılımının tam teknik ve operasyonel rehberidir. Başka bir AI asistana veya yeni bir modele bu metin doğrudan sistem talimatı olarak verilebilir.

---

## 1. SİSTEMİN AMACI VE YAPILAN İŞ
Hankook ithalat dosyalarının operasyonel takibini, evrak mutabakatını, Evrim gümrük yazılımına veri aktarımını ve beyanname robotunun girdi hazırlığını tamamen otomatikleştiren bir ekosistemdir.

* **Ana Proje Dizini:** `C:\HANKOOK_OPERASYON_MASASI\`
* **Başlatıcı:** `C:\HANKOOK_OPERASYON_MASASI\HANKOOK_MASASI_BASLAT.bat` (veya Masaüstü Kısayolu)

---

## 2. BİLEŞENLER VE VERİ KAYNAKLARI

### A. İş Takip Raporu (Merkezi Operasyon Raporu):
* **Varsayılan Dosya:** `\\Dgfile01\ithalat\ITH28\Halit ENGELEK\RAPOR\HANKOOK İŞ TAKİP RAPORU.xlsx`
* **Dinamik Yol:** Kullanıcı arayüzdeki "Dosya Değiştir" butonuyla farklı bir yol (örn. yerel bir kopya) seçebilir. Seçilen yol `C:\HANKOOK_OPERASYON_MASASI\ayarlar.json` dosyasında saklanır.
* **Kritik Sütunlar (0-tabanlı python / 1-tabanlı excel):**
  - Col 1 (A): Dosya No (`26-XXXXXX`)
  - Col 3 (C): Referans No / PO (`4200XXXXXX`)
  - Col 7 (G): Ordino Teslim Tarihi
  - Col 9 (I): TAREKS Başvuru Tarihi
  - Col 10 (J): TAREKS Sonuç Tarihi
  - Col 11 (K): Fiili Denetim Durumu (TSE Heyet vb.)
  - Col 12 (L): Tescil Tarihi
  - Col 14 (N): Kapanış Tarihi
  - Col 19 (S): Fiili Varış Tarihi
  - Col 20 (T): ETA (Tahmini Varış)
  - Col 22 (V): Liman
  - Col 23 (W): Gemi Adı

### B. Master Data (Ürün Kütüphanesi):
* **Dosya:** `mastergtip (X).xls` (Downloads klasörüne indirilir).
* **Format Uyarısı:** `.xls` uzantılı olmasına rağmen gerçekte HTML tablo formatındadır; `pandas.read_html()` ile okunmalıdır.
* CMMF lastik kodlarının Evrim sistemindeki karşılıklarını (GTİP, Türkçe tanım, statü) tutar.
* **Eksik CMMF Tespiti & Yükleme:** Master datada bulunmayan ürünler için Evrim toplu ürün yükleme formatında `mastera_eklenecek.xlsx` şablonu doldurulur:
  - Firma No: `9122`
  - İhracatçı No: `413049` (Hankook Tire & Technology Co. Ltd.)
  - GTİP: Noktasız 12 hane (Binek: `401110009012`, Kamyon/Ağır Vasıta: `401120900011`)
  - Menşei: `Kore Cumhuriyeti` | Anlaşma Kodu: `KORE`
  - KDV: `20` | İlişki: `VAR` | Tip: `T` (İthalat)

### C. Gümrük Aktarım Excel Şablonu (`_Aktarim.xlsx`):
* Evrim sistemine kalem kalem veri basan aktarım tablosudur (`sablon.xlsx` baz alınır).
* **Format ve Sütun Standartları:**
  - Sütun F: Miktar (EA)
  - Sütun G: Birim (`AD`)
  - Sütun I: CMMF Kodu (Kesinlikle Metin / `@` formatı, başında/sonunda boşluksuz)
  - Sütun K: Kalem Tutarı (Sayı, format: `0.00`)
  - Sütun L: Fatura Para Birimi (`TRY`, `USD`, `EUR`)
  - Sütun M: Menşe Ülke Evrim Kodu (Kore: `728`, Macaristan: `064`, Çin: `156`)
  - Sütun N: Brüt Ağırlık (Sayı, format: `0.000`)
  - Sütun O: Net Ağırlık (Sayı, format: `0.000`)
  - Sütun P: Fatura Numarası (Metin)
  - Sütun Q: Fatura Tarihi (Format: `mm-dd-yy`)
  - Sütun R: Sipariş Referansı (`PO_NO/HNKRE`)
  - Sütun S: `11` | Sütun T: `K1` | Sütun U: `9` | Sütun X: `0100` (Edi Belge Kodu)
  - Tüm sütun genişlikleri: `20`

### D. Beyanname Robot Şablonu (`Otonom_Sablon.xlsx`):
* `C:\OTONOMAKTARIM_AYARLAR\beyanname_otonom_arayuz.py` robotunun okuduğu tablodur.
* **Sabit Parametreler:**
  - `1 Beyan`: `4000` (Serbest Dolaşıma Giriş)
  - `29 Giriş Gümrük`: `18` (Derince Gümrük Müdürlüğü)
  - `22 Fatura Bedeli`: `F4`
  - `Banka Bilgisi`: `14661`
  - `Ödeme Şekli`: `7` | `Ödeme Kısa`: `71`
  - `25 Sınırdaki` & `26 Dahili`: `10` (Denizyolu konteyner)
  - `T19 Kntynr` & `Tür-Knt Sayısı`: `1`
  - `EDI Karne`: `30`
* **Belgeden / Rapordan Çıkarılan Dinamik Parametreler:**
  - `Teslim Şekli`: `CIP`
  - `Teslim Şehri`: Faturadaki teslim yerine bakılır (`Gebze Kocaeli` → `KOCAELİ`, `Istanbul Turkey` → `İSTANBUL`).
  - `Gemi Adı`: Faturada aktarma gemisi yazsa dahi Takip Raporu'ndaki fiili ana gemi adı (örn. *MAERSK LEBU*, *MSC MIRJA*, *MISSOURI EXPRESS*) yazılır.
  - `Liman`: Hapag & Yang Ming → `DP`, MSC & Glovis & ONE → `EVYAP`.

---

## 3. MASAÜSTÜ YAZILIM MİMARİSİ (`C:\HANKOOK_OPERASYON_MASASI\`)
Python 3.12 ve PyQt6 ile inşa edilmiştir:

1. **`main.py`**:
   Uygulama giriş noktası. Olası çökmeleri yakalar, `hata_log.txt` dosyasına yazar ve konsolun aniden kapanmasını önler.
2. **`app/theme.py`**:
   Bloomberg/Terminal esintili, göz yormayan profesyonel koyu tema (`#12151C`). Durum renkleri, tipografi ve tablo stilleri merkezi olarak tanımlanır.
3. **`app/config.py`**:
   `C:\HANKOOK_OPERASYON_MASASI\ayarlar.json` üzerinden izlenen rapor dosyasının yolunu kalıcı olarak tutar.
4. **`app/data_loader.py`**:
   `DataLoaderThread(QThread)` ile arka planda çalışarak ana arayüzün donmasını engeller. Raporu okur ve kayıtları şu 8 duruma göre sınıflandırır:
   - `DEMURAJ_RISKI`: Varış üzerinden 7+ gün geçmiş ve tescil olmamış (Kırmızı)
   - `BANKA_ID_BEKLER`: Banka referansı bekleyen tescil aşamasındaki dosyalar (Turuncu)
   - `TAREKS_DENETIM`: TAREKS fiili denetime yönlendirilenler (Mor)
   - `ORDINO_BEKLER`: Gemi yanaşmış, ordino bekleyenler (Sarı)
   - `ETA_YAKLASAN`: 7 gün içinde limana varacak olanlar (Mavi)
   - `DOSYA_YOK`: Raporlanmış ama henüz Evrim dosya no'su atanmamış olanlar (Gri)
   - `TESCIL_BEKLER`: Tescil yapılmış, kapanış bekleyenler
   - `NORMAL`: Diğer açık operasyonlar
5. **`app/main_window.py`**:
   Ana pencere. `QFileSystemWatcher` ile izlenen Excel dosyasındaki değişiklikleri anlık yakalar; dosya her kaydedildiğinde 2 saniye içinde arayüzü otomatik olarak yeniden yükler. Üst barda dosya seçici ve izleme durumu lambası bulunur.
6. **`app/dashboard_tab.py`**:
   6 adet KPI kartı ve otomatik metin üreten Günlük Operasyon Brifingi paneli.
7. **`app/shipments_tab.py`**:
   Filtreleme butonları, anlık metin arama kutusu ve çift tıklamayla açılan detaylı dosya kartı pop-up penceresi.
8. **`app/actions_tab.py`**:
   Operasyonel işlemler: Robot Şablonu güncelleme, klasör seçerek dinamik Master Data CMMF kontrolü ve çalışma klasörünü açma butonları (işlem log ekranı ile).

---

## 4. ASLA ÇİĞNENMEYECEK GÜMRÜK KURALLARI (GOLDEN RULES)

1. **Asla Tahmin Yapma:**
   Menşe, teslim yeri, gemi adı veya liman bilgisi asla uydurulmaz; mutlaka fatura Kutu 17, konşimento ve takip raporundan teyit edilir.
2. **Transit / Üçgen Ticaret Kuralı (Singapur Faturaları):**
   Singapur üzerinden faturalanan dosyalarda (Kore imalatçı faturası + Singapur satış faturası), Türkiye'deki ithalatçının ödeyeceği ve gümrük beyannamesinde tescil edilecek asıl ticari fatura **Singapur faturasıdır (TRY)**. Kore faturası ise menşe ve tedarik zincirini tevsik eden refakat belgesidir. Malların fiziki menşei Kore'dir (`728`).
3. **YFKS Zorunluluğu (2019/24 Sayılı Genelge):**
   Yeni yabancı tedarikçilerde (örn. *Hankook Tire Singapore Pte. Ltd*) Ticaret Bakanlığı Yabancı Firma Kayıt Sistemi numarası (`26SG...`) Derince Gümrük Müdürlüğü'ne resmi dilekçe ile sunularak onaylatılır.
4. **Dosya Kilidi Güvenliği (WinError 32):**
   Kullanıcının açık unuttuğu Excel dosyaları doğrudan ezilmeye çalışılmaz; kilit kontrolü yapılır veya geçici kopyalar üzerinden güvenle işlem yapılır.

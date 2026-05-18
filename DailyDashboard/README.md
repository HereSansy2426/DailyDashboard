# Daily Dashboard

Python ve CustomTkinter kullanılarak geliştirilmiş modern bir masaüstü günlük kontrol paneli uygulaması. Daily Dashboard; tek ve şık bir arayüz üzerinden güncel haberleri takip etmenizi, piyasa trendlerini incelemenizi, hava durumunu öğrenmenizi ve günlük görevlerinizi yönetmenizi sağlar.

## 🚀 Özellikler

*   **Kullanıcı Girişi (Authentication):** MySQL veritabanı ile entegre, güvenli giriş ve kayıt (Sign In / Sign Up) sistemi.
*   **Günün Haberleri (Trending News):** NewsAPI kullanarak İş, Teknoloji, Spor vb. kategorilerdeki en güncel haber başlıklarını çeker ve gösterir.
*   **Piyasa Takibi (Market Watch):** MarketStack API aracılığıyla canlı borsa ve kripto para verilerini (NVDA, AAPL, BTC, ETH vb.) anlık takip eder.
*   **Hava Durumu Aracı (Weather Widget):** WeatherStack API kullanarak anlık hava durumu koşullarını gösterir.
*   **Günlük Planlayıcı (Daily Planner):** Zaman çizelgesi (timeline) tabanlı etkinlik ve görev planlayıcı.
*   **Hızlı Notlar (Quick Notes):** Kısa notlar ve hatırlatıcılar kaydetmek için yerleşik bir not tutma aracı.
*   **Modern Arayüz (UI):** CustomTkinter ile tasarlanmış temiz, duyarlı (responsive) ve estetik kullanıcı arayüzü.

## 🛠️ Kullanılan Teknolojiler

*   **Dil:** Python 3.x
*   **Arayüz (GUI) Kütüphanesi:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
*   **Veritabanı:** MySQL
*   **Görüntü İşleme:** Pillow (PIL)
*   **HTTP İstekleri:** Requests kütüphanesi

### Kullanılan API'lar
*   [NewsAPI](https://newsapi.org/) - Güncel haberler için
*   [MarketStack](https://marketstack.com/) - Borsa verileri için
*   [WeatherStack](https://weatherstack.com/) - Hava durumu tahmini için

## ⚙️ Kurulum ve Ayarlar

### 1. Projeyi İndirin (Clone)
```bash
git clone https://github.com/kullaniciadiniz/DailyDashboard.git
cd DailyDashboard
```

### 2. Gerekli Kütüphaneleri Yükleyin
Bilgisayarınızda Python yüklü olduğundan emin olun. Daha sonra aşağıdaki komutla gerekli paketleri kurun:
```bash
pip install customtkinter Pillow requests mysql-connector-python
```

### 3. Veritabanı Yapılandırması
1.  MySQL kurulu olduğundan ve sunucunun çalıştığından emin olun.
2.  `dailydashboard` adında yeni bir veritabanı oluşturun.
3.  Tabloları kurmak için projede bulunan SQL dosyasını içeri aktarın:
    ```bash
    mysql -u root -p dailydashboard < DailyDashboard.sql
    ```
4.  `signin.py` ve `signup.py` dosyalarını açıp, eğer MySQL ayarlarınız (kullanıcı adı/şifre) farklıysa ilgili yerleri güncelleyin.

### 4. API Key (Anahtar) Ayarları
`main.py` dosyasını açın ve aşağıdaki API bağlantılarındaki örnek anahtarları kendi API key'lerinizle değiştirin:
```python
WEATHER_API_URL = "https://api.weatherstack.com/current?access_key=BURAYA_API_KEY_GELECEK&query=Izmir&unit=m"
MARKET_API_KEY = "BURAYA_MARKET_API_KEY_GELECEK"
NEWS_API_URL = "https://newsapi.org/v2/top-headlines?country=us&apiKey=BURAYA_NEWS_API_KEY_GELECEK"
```

## 🎯 Nasıl Çalıştırılır?

Uygulamayı başlatmak için giriş (sign in) modülünü çalıştırın:

```bash
python signin.py
```
*(Başarıyla giriş yaptıktan sonra ana panel otomatik olarak açılacaktır.)*

## 📸 Ekran Görüntüleri

*(Projenizin ekran görüntülerini buraya ekleyebilirsiniz)*
* **Giriş / Kayıt Ekranı**
* **Ana Dashboard Görünümü**
* **Haberler Detay Görünümü**

---
**Not:** Bu proje, Python masaüstü uygulamaları için modern bir UI (kullanıcı arayüzü) örneği olarak geliştirilmiştir. İstediğiniz gibi çatallayabilir (fork) ve düzenleyebilirsiniz!

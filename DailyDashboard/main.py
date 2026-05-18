import customtkinter as ctk
from PIL import Image, ImageOps, ImageDraw
import requests
from io import BytesIO
import threading
from datetime import date, timedelta
import sys
import mysql.connector
import webbrowser
import re

# --- Renk Paleti (Tasarım görselinden alındı) ---
WEATHER_API_URL = "https://api.weatherstack.com/current?access_key=0379687784e623d734bea52478ac14ba&query=Izmir&unit=m"
#MARKET_API_KEY = "d0979859918b42807acd814cffbfebec" #-- MAIN
MARKET_API_KEY = "5f6c0433f4abd0fac1ffb39e14b3f013" #-- DUMMY
MARKET_BASE_URL = "https://api.marketstack.com/v1/eod"
NEWS_API_URL = "https://newsapi.org/v2/top-headlines?country=us&apiKey=c58acfb6867441debbeb6ff6c1b42a10"

# Market Watch - sembol -> şirket adı (UI'da göstermek için)
MARKET_SYMBOL_NAMES = {
    "NVDA": "NVIDIA",
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "GOOG": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta",
    "MSFT": "Microsoft",
    "NFLX": "Netflix",
    "MRT": "Martı",
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
}

COLORS = {
    "bg_main": "#F1F5F9",  # Arka plan açık gri
    "card_bg": "#FFFFFF",  # Kart arka planı beyaz
    "primary": "#6366f1",  # Indigo
    "primary_dark": "#4338ca",
    "text_dark": "#0F172A",  # Koyu metin
    "text_gray": "#64748B",  # Gri metin
    "green_bg": "#DCFCE7", "green_text": "#16A34A",
    "red_bg": "#FEE2E2", "red_text": "#DC2626",
    "weather_grad": "#4F46E5",  # Gradient yerine solid renk
    "input_bg": "#F8FAFC"
}


# --- Yardımcı Fonksiyonlar ---

REQUEST_TIMEOUT = 10

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # Pillow<9
    RESAMPLE_LANCZOS = Image.LANCZOS


def fetch_pil_image(url, *, mode="RGBA", timeout=REQUEST_TIMEOUT):
    """URL'den resim indirir ve PIL Image döndürür. Hata durumunda None."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        return img.convert(mode) if mode else img
    except Exception:
        return None


def fit_pil_image(pil_image, size, *, centering=(0.5, 0.5)):
    """Oranı bozmadan crop/zoom yaparak hedef boyuta sığdırır."""
    return ImageOps.fit(pil_image, size, method=RESAMPLE_LANCZOS, centering=centering)


def add_rounded_corners(pil_image, radius, corners=(True, True, True, True)):
    """
    PIL image'e seçmeli köşe yuvarlama uygular.
    corners sırası: (top_left, top_right, bottom_right, bottom_left)
    """
    img = pil_image.convert("RGBA")
    w, h = img.size
    r = max(0, min(int(radius), w // 2, h // 2))
    if r == 0:
        return img

    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)

    # Orta alanlar
    draw.rectangle([r, 0, w - r, h], fill=255)
    draw.rectangle([0, r, r, h - r], fill=255)
    draw.rectangle([w - r, r, w, h - r], fill=255)

    tl, tr, br, bl = corners

    # TL
    if tl:
        draw.pieslice([0, 0, 2 * r, 2 * r], 180, 270, fill=255)
    else:
        draw.rectangle([0, 0, r, r], fill=255)

    # TR
    if tr:
        draw.pieslice([w - 2 * r, 0, w, 2 * r], 270, 360, fill=255)
    else:
        draw.rectangle([w - r, 0, w, r], fill=255)

    # BR
    if br:
        draw.pieslice([w - 2 * r, h - 2 * r, w, h], 0, 90, fill=255)
    else:
        draw.rectangle([w - r, h - r, w, h], fill=255)

    # BL
    if bl:
        draw.pieslice([0, h - 2 * r, 2 * r, h], 90, 180, fill=255)
    else:
        draw.rectangle([0, h - r, r, h], fill=255)

    img.putalpha(mask)
    return img


def add_rounded_corners_aa(pil_image, radius, corners=(True, True, True, True), scale=4):
    """
    Anti-aliased (yumuşak) köşe yuvarlama.
    scale yükseldikçe köşeler daha pürüzsüz olur (maliyet artar).
    """
    img = pil_image.convert("RGBA")
    w, h = img.size
    if w <= 0 or h <= 0:
        return img

    s = max(1, int(scale))
    big = img.resize((w * s, h * s), RESAMPLE_LANCZOS)
    big = add_rounded_corners(big, radius=int(radius) * s, corners=corners)
    return big.resize((w, h), RESAMPLE_LANCZOS)


def make_circular(pil_image):
    """PIL resmini yuvarlak yapar."""
    pil_image = pil_image.convert("RGBA")
    mask = Image.new('L', pil_image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + pil_image.size, fill=255)
    output = ImageOps.fit(pil_image, mask.size, method=RESAMPLE_LANCZOS, centering=(0.5, 0.5))
    output.putalpha(mask)
    return output


# --- Bileşen Sınıfları ---

class NewsCard(ctk.CTkFrame):
    def __init__(self, parent, img_url, category, title, color_code, url=None, **kwargs):
        super().__init__(parent, fg_color=COLORS["input_bg"], corner_radius=16, **kwargs)

        self._img_url = img_url
        self._article_url = url  # Article URL for opening in browser
        self._pending_pil_image = None
        self._pending_size = None
        self._image_load_done = False
        self._ctk_image = None  # GC olmaması için referans tut

        # Use grid layout for precise control
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Image row
        self.grid_rowconfigure(1, weight=0)  # Category row
        self.grid_rowconfigure(2, weight=1)  # Title row

        # Resim Alanı - using a frame to contain the image with matching corners
        self.img_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.img_container.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        
        self.img_label = ctk.CTkLabel(self.img_container, text="", fg_color="transparent", 
                                       cursor="hand2" if url else "")
        self.img_label.pack(fill="x", expand=True, padx=0, pady=0)
        
        # Bind click event to open URL
        if url:
            self.img_label.bind("<Button-1>", self._on_image_click)
            self.img_container.bind("<Button-1>", self._on_image_click)

        # Resim Yükleme (önce genişlik oluşsun, sonra oran-korumalı crop/zoom uygula)
        self.after(0, self._ensure_image_loaded)

        # Kategori
        self.cat_lbl = ctk.CTkLabel(self, text=category.upper(), text_color=color_code,
                                    font=("Outfit", 10, "bold"), anchor="w")
        self.cat_lbl.grid(row=1, column=0, sticky="ew", padx=12, pady=(2, 0))

        # Başlık - Daha okunabilir olması için font biraz küçültüldü, alan açıldı
        self.title_lbl = ctk.CTkLabel(self, text=title, text_color=COLORS["text_dark"],
                                      font=("Inter", 11, "bold"), wraplength=250, anchor="w", justify="left")
        self.title_lbl.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))

    def _on_image_click(self, event=None):
        """Open article URL in default browser when image is clicked"""
        if self._article_url:
            webbrowser.open(self._article_url)

    def _ensure_image_loaded(self):
        w = self.winfo_width()  # Use card width instead of label width
        if w <= 1:
            self.after(50, self._ensure_image_loaded)
            return

        # Fotoğrafı boyuna iyice kısalt -> Başlıklar görünsün (2 satır rahat sığsın)
        h = max(35, min(int(w * 0.20), 50))
        size = (w, h)

        threading.Thread(target=self._load_image_worker, args=(self._img_url, size), daemon=True).start()
        self.after(50, self._try_apply_loaded_image)

    def _load_image_worker(self, url, size):
        try:
            pil_image = fetch_pil_image(url, mode="RGBA")
            if pil_image is None:
                return
            pil_image = fit_pil_image(pil_image, size)
            pil_image = add_rounded_corners_aa(pil_image, radius=16, corners=(True, True, False, False), scale=4)

            self._pending_pil_image = pil_image
            self._pending_size = size
        except Exception:
            pass
        finally:
            self._image_load_done = True

    def _try_apply_loaded_image(self):
        if self._pending_pil_image is not None and self._pending_size is not None:
            pil_image = self._pending_pil_image
            size = self._pending_size
            self._pending_pil_image = None
            self._pending_size = None

            # CTkImage/PhotoImage üretimi UI thread'de kalsın
            self._ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
            self.img_label.configure(image=self._ctk_image)
            return

        if self._image_load_done:
            return

        self.after(50, self._try_apply_loaded_image)


class MarketTicker(ctk.CTkFrame):
    def __init__(self, parent, symbol, name, price, change, is_positive, **kwargs):
        # Sadece şirket ismi gösteriliyor
        super().__init__(parent, fg_color=COLORS["input_bg"], corner_radius=12, width=165, height=90, **kwargs)
        self.pack_propagate(False)

        # Company name icon circle
        self.icon_bg = ctk.CTkFrame(self, width=30, height=30, corner_radius=15, fg_color="white")
        self.icon_bg.place(relx=0.5, rely=0.22, anchor="center")
        ctk.CTkLabel(self.icon_bg, text=name[0], font=("Arial", 11, "bold"), text_color="black").place(relx=0.5,
                                                                                                        rely=0.5,
                                                                                                        anchor="center")

        self.name_lbl = ctk.CTkLabel(self, text=name, font=("Inter", 11, "bold"), text_color=COLORS["text_dark"])
        self.name_lbl.place(relx=0.5, rely=0.48, anchor="center")

        self.price_lbl = ctk.CTkLabel(self, text=price, font=("Inter", 13, "bold"), text_color=COLORS["text_dark"])
        self.price_lbl.place(relx=0.5, rely=0.68, anchor="center")

        bg = COLORS["green_bg"] if is_positive else COLORS["red_bg"]
        fg = COLORS["green_text"] if is_positive else COLORS["red_text"]

        self.pill = ctk.CTkFrame(self, fg_color=bg, corner_radius=8, height=18, width=50)
        self.pill.place(relx=0.5, rely=0.86, anchor="center")
        self.change_lbl = ctk.CTkLabel(self.pill, text=change, text_color=fg, font=("Inter", 10, "bold"))
        self.change_lbl.place(relx=0.5, rely=0.5, anchor="center")

    def update_data(self, name, price, change, is_positive):
        self.name_lbl.configure(text=name)
        self.price_lbl.configure(text=price)
        self.change_lbl.configure(text=change)
        
        bg = COLORS["green_bg"] if is_positive else COLORS["red_bg"]
        fg = COLORS["green_text"] if is_positive else COLORS["red_text"]
        
        self.pill.configure(fg_color=bg)
        self.change_lbl.configure(text_color=fg)


class PlannerItem(ctk.CTkFrame):
    def __init__(self, parent, time_range, title, circle_text="09", is_active=False, full_text=None, full_date=None, app_ref=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self._full_text = full_text or title
        self._full_date = full_date or time_range
        self._app_ref = app_ref

        self.grid_columnconfigure(0, minsize=44)
        self.grid_columnconfigure(1, weight=1)

        circle_color = COLORS["primary"] if is_active else "white"
        text_color = "white" if is_active else "gray"
        border_color = COLORS["primary"] if is_active else "#CBD5E1"

        # Sol taraf (Zaman çizgisi)
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left_frame.grid_columnconfigure(0, weight=1)

        circle = ctk.CTkFrame(left_frame, width=32, height=32, corner_radius=16,
                              fg_color=circle_color, border_width=2, border_color=border_color)
        circle.grid(row=0, column=0, pady=(0, 2))
        circle.grid_propagate(False)
        ctk.CTkLabel(circle, text=circle_text, text_color=text_color, font=("Inter", 10, "bold")).place(relx=0.5,
                                                                                                        rely=0.5,
                                                                                                        anchor="center")

        # Çizgi: Kısaltılmış sabit yükseklik (ekranın stok halinde yazı kutusu görülebilsin)
        line = ctk.CTkFrame(left_frame, width=2, height=15, fg_color="#E2E8F0")
        line.grid(row=1, column=0, sticky="n", pady=(2, 0))

        # İçerik Kartı
        card_bg = COLORS["primary"] + "1A" if is_active else COLORS["input_bg"]  # Transparent primary fake
        if is_active: card_bg = "#EEF2FF"  # Very light indigo

        content = ctk.CTkFrame(self, fg_color=card_bg, corner_radius=12, border_width=1 if not is_active else 0,
                               border_color="#E2E8F0")
        content.grid(row=0, column=1, sticky="ew")

        # Truncate title if too long
        display_title = title
        is_truncated = len(title) > 25
        if is_truncated:
            display_title = title[:22] + "..."
        
        title_lbl = ctk.CTkLabel(content, text=display_title, font=("Inter", 13, "bold"), 
                                  text_color=COLORS["text_dark"], anchor="w",
                                  cursor="hand2" if is_truncated else "")
        title_lbl.pack(fill="x", padx=10, pady=(5, 0))
        
        if is_truncated and app_ref:
            title_lbl.bind("<Button-1>", lambda e: self._show_full_detail())
        
        ctk.CTkLabel(content, text=time_range, font=("Inter", 11),
                     text_color=COLORS["primary"] if is_active else COLORS["text_gray"], anchor="w").pack(fill="x",
                                                                                                          padx=10,
                                                                                                          pady=(0, 5))

    def _show_full_detail(self):
        """Shows popup with full reminder text"""
        if not self._app_ref:
            return
            
        popup = ctk.CTkToplevel(self._app_ref)
        popup.title("Reminder Details")
        popup.geometry("400x200")
        popup.transient(self._app_ref)
        popup.grab_set()
        popup.resizable(False, False)
        
        # Content
        content = ctk.CTkFrame(popup, fg_color=COLORS["card_bg"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(content, text="📅 " + self._full_date, font=("Inter", 14, "bold"),
                     text_color=COLORS["primary"]).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(content, text=self._full_text, font=("Inter", 13),
                     text_color=COLORS["text_dark"], wraplength=340, 
                     justify="left", anchor="w").pack(fill="x", pady=(0, 15))
        
        ctk.CTkButton(content, text="Close", fg_color=COLORS["primary"],
                      hover_color=COLORS["primary_dark"], command=popup.destroy).pack()


# --- Ana Uygulama ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Kullanıcı adı ve username'i komut satırından al (signin.py'den gelecek)
        self.user_name = sys.argv[1] if len(sys.argv) > 1 else "Alex Morgan"
        self.username = sys.argv[2] if len(sys.argv) > 2 else "admin"

        # Pencere Ayarları
        self.title("Daily Dashboard")
        self.geometry("1550x650")
        # Tam ekran / maximize kapalı: uygulama tek parça ve sabit ölçüde kalsın
        self.minsize(1550, 650)
        self.maxsize(1550, 650)
        self.resizable(False, False)
        try:
            self.attributes("-fullscreen", False)
        except Exception:
            pass
        # Yaygın fullscreen kısayollarını da blokla
        self.bind("<F11>", lambda _e: "break")
        self.bind("<Alt-Return>", lambda _e: "break")
        ctk.set_appearance_mode("Light")

        # Ana Konteyner
        # Dikey scroll olmasın: ana konteyner scrollable değil
        self.main_container = ctk.CTkFrame(self, fg_color=COLORS["bg_main"], corner_radius=0)
        self.main_container.pack(fill="both", expand=True)

        self.setup_header()
        self.setup_grid_layout()

    def setup_header(self):
        header = ctk.CTkFrame(self.main_container, fg_color=COLORS["card_bg"], height=80, corner_radius=16)
        header.pack(fill="x", padx=20, pady=(12, 10))
        header.pack_propagate(False)

        # Logo Area
        logo_box = ctk.CTkFrame(header, fg_color="#EEF2FF", width=40, height=40, corner_radius=8)
        logo_box.pack(side="left", padx=16, pady=16)
        ctk.CTkLabel(logo_box, text="dashboard", font=("Material Icons", 18), text_color=COLORS["primary"]).place(
            relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(header, text="Daily Dashboard", font=("Outfit", 20, "bold"), text_color=COLORS["text_dark"]).pack(
            side="left")

        # Profile Area
        profile_frame = ctk.CTkFrame(header, fg_color="transparent")
        profile_frame.pack(side="right", padx=16)

        # İsim
        info_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        info_frame.pack(side="left", padx=8)
        ctk.CTkLabel(info_frame, text=self.user_name, font=("Inter", 13, "bold"), text_color=COLORS["text_dark"]).pack(
            anchor="e")

        # Avatar (Yer tutucu)
        avatar_box = ctk.CTkFrame(profile_frame, width=40, height=40, corner_radius=20, fg_color="transparent")
        avatar_box.pack(side="left")
        threading.Thread(target=self.load_avatar, args=(avatar_box,), daemon=True).start()

    def load_avatar(self, parent):
        url = "https://lh3.googleusercontent.com/aida-public/AB6AXuCYOX75c97OtX6zR7z4ddbhl0BSe55KJwoDEqmC4Fq1W7M4wmSov5TKEUhv-gYa3hqwXZoM0kbZwoidmnnZIgJohmS-__O977IrsiEeOOMDDxjnowS6MPHbpLXA4CwLm9Gtj9fm0WNM3eaQI_osvPgFBcbVi1dZ3K0kptkziWRNcKh4fm2ovy_DMW6J9V_U-yJjwvOK23dRKth6RI_a8ROoqk5JMrKXTrbauodGToNSscEnF0b8pncyo94GGLSbEZdGRkvneoU8S08"
        img = fetch_pil_image(url, mode="RGBA")
        if img is None:
            return
        img = make_circular(img)
        self.after(0, self._set_avatar_image, parent, img)

    def _set_avatar_image(self, parent, pil_image):
        ctk_img = ctk.CTkImage(pil_image, size=(40, 40))
        lbl = ctk.CTkLabel(parent, text="", image=ctk_img, fg_color="transparent")
        lbl.image = ctk_img  # GC engelle
        lbl.place(relx=0.5, rely=0.5, anchor="center")

    def setup_grid_layout(self):
        # Grid Yapısı: Sol (Geniş) - Sağ (Dar)
        content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        content_frame.grid_columnconfigure(0, weight=12)  # Sol kolon (Trending News çok daha geniş)
        content_frame.grid_columnconfigure(1, weight=1)  # Sağ kolon (Sidebar çok daha dar)
        content_frame.grid_rowconfigure(0, weight=1)

        # === SOL KOLON ===
        left_col = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        # Sol kolon: 3 eşit panel (arada sabit boşluk)
        left_col.grid_columnconfigure(0, weight=1)
        left_col.grid_rowconfigure(0, weight=1, uniform="left_panels")
        left_col.grid_rowconfigure(1, weight=0, minsize=10)
        left_col.grid_rowconfigure(2, weight=1, uniform="left_panels")
        left_col.grid_rowconfigure(3, weight=0, minsize=10)
        left_col.grid_rowconfigure(4, weight=1, uniform="left_panels")

        # 1. Trending News Section
        self.create_news_section(left_col, row=0)

        # 2. Market Watch Section
        self.create_market_section(left_col, row=2)

        # 3. Daily Read
        self.create_daily_read(left_col, row=4)

        # === SAĞ KOLON (Sidebar) ===
        right_col = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.grid_columnconfigure(0, weight=1)
        right_col.grid_rowconfigure((0, 1, 2), weight=1, uniform="sidebar")

        # 1. Weather Widget
        self.create_weather_widget(right_col, row=0)

        # 2. Planner
        self.create_planner_widget(right_col, row=1)

        # 3. Quick Notes
        self.create_notes_widget(right_col, row=2)

    def create_news_section(self, parent, row=0):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"], corner_radius=20, height=170)
        frame.grid(row=row, column=0, sticky="nsew")
        frame.grid_propagate(False)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=1)

        # Header
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkLabel(head, text="Trending News", font=("Outfit", 18, "bold"), text_color=COLORS["text_dark"]).pack(
            side="left")
        
        # View All - clickable label
        view_all_lbl = ctk.CTkLabel(head, text="View All", font=("Inter", 12, "bold"), 
                                     text_color=COLORS["primary"], cursor="hand2")
        view_all_lbl.pack(side="right")
        view_all_lbl.bind("<Button-1>", lambda e: self.open_all_news_window())

        # Grid items
        self.news_grid_box = ctk.CTkFrame(frame, fg_color="transparent")
        self.news_grid_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        self.news_grid_box.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.news_grid_box.grid_rowconfigure(0, weight=1)

        # Store news articles for View All
        self.news_articles = []
        
        # Category colors mapping
        self.category_colors = {
            "business": COLORS["primary"],
            "tech": "#A855F7",
            "technology": "#A855F7",
            "entertainment": "#22C55E",
            "sports": "#F97316",
            "health": "#EC4899",
            "science": "#14B8A6",
            "general": "#6366F1",
        }

        # Fetch news from API
        threading.Thread(target=self.fetch_news_data, daemon=True).start()

    def fetch_news_data(self):
        """Fetch news from NewsAPI"""
        try:
            resp = requests.get(NEWS_API_URL, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            
            articles = data.get("articles", [])
            
            # Process articles for display
            news_data = []
            for article in articles:
                if not article:
                    continue
                    
                img_url = article.get("urlToImage") or ""
                source_name = article.get("source", {}).get("name", "News")
                title = article.get("title", "")
                url = article.get("url", "")
                
                # Skip articles without essential data
                if not title or title == "[Removed]":
                    continue
                
                # Get color based on source name (simplified category detection)
                source_lower = source_name.lower()
                color = COLORS["primary"]  # default
                for cat, col in self.category_colors.items():
                    if cat in source_lower:
                        color = col
                        break
                
                news_data.append({
                    "img_url": img_url,
                    "category": source_name,
                    "title": title,
                    "color": color,
                    "url": url
                })
            
            # Store all articles and update UI
            self.after(0, self.update_news_ui, news_data)
            
        except Exception as e:
            print(f"News API Error: {e}")
            # Fallback data if API fails
            fallback_data = [
                {"img_url": "", "category": "BUSINESS", "title": "Global Markets Update", "color": COLORS["primary"], "url": ""},
                {"img_url": "", "category": "TECH", "title": "Technology News", "color": "#A855F7", "url": ""},
                {"img_url": "", "category": "STARTUPS", "title": "Startup News", "color": "#22C55E", "url": ""},
                {"img_url": "", "category": "HARDWARE", "title": "Hardware Updates", "color": "#F97316", "url": ""},
            ]
            self.after(0, self.update_news_ui, fallback_data)

    def update_news_ui(self, news_data):
        """Update news section with fetched data"""
        # Store all articles for View All
        self.news_articles = news_data
        
        # Clear existing cards
        for widget in self.news_grid_box.winfo_children():
            widget.destroy()
        
        # Display first 4 articles
        for i, article in enumerate(news_data[:4]):
            card = NewsCard(
                self.news_grid_box,
                img_url=article["img_url"],
                category=article["category"],
                title=article["title"][:50] + "..." if len(article["title"]) > 50 else article["title"],
                color_code=article["color"],
                url=article["url"]
            )
            card.grid(row=0, column=i, padx=5, sticky="nsew")

    def open_all_news_window(self):
        """Open a new window showing all news articles"""
        if not self.news_articles:
            return
            
        # Create toplevel window
        all_news_window = ctk.CTkToplevel(self)
        all_news_window.title("All News")
        all_news_window.geometry("800x600")
        all_news_window.transient(self)
        all_news_window.grab_set()
        
        # Header
        header = ctk.CTkFrame(all_news_window, fg_color=COLORS["card_bg"], height=60)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, text="All Trending News", font=("Outfit", 20, "bold"), 
                     text_color=COLORS["text_dark"]).pack(side="left", padx=20, pady=15)
        
        # Scrollable content
        scroll_frame = ctk.CTkScrollableFrame(all_news_window, fg_color=COLORS["bg_main"])
        scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # News items
        for article in self.news_articles:
            item_frame = ctk.CTkFrame(scroll_frame, fg_color=COLORS["card_bg"], corner_radius=12, height=100)
            item_frame.pack(fill="x", padx=15, pady=6)
            item_frame.pack_propagate(False)
            
            # Content container
            content = ctk.CTkFrame(item_frame, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=15, pady=10)
            
            # Image placeholder (left side) - clickable
            img_frame = ctk.CTkFrame(content, width=120, height=80, fg_color=COLORS["input_bg"], corner_radius=8)
            img_frame.pack(side="left", padx=(0, 15))
            img_frame.pack_propagate(False)
            
            if article["url"]:
                img_frame.configure(cursor="hand2")
                url = article["url"]
                img_frame.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
                
                # Add click indicator
                ctk.CTkLabel(img_frame, text="🔗 Click to read", font=("Inter", 10), 
                            text_color=COLORS["text_gray"]).place(relx=0.5, rely=0.5, anchor="center")
            
            # Load image async
            if article["img_url"]:
                threading.Thread(target=self._load_news_list_image, 
                               args=(img_frame, article["img_url"], article["url"]), daemon=True).start()
            
            # Text content (right side)
            text_frame = ctk.CTkFrame(content, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True)
            
            # Source/Category
            ctk.CTkLabel(text_frame, text=article["category"].upper(), 
                        font=("Outfit", 10, "bold"), text_color=article["color"], anchor="w").pack(fill="x")
            
            # Title
            ctk.CTkLabel(text_frame, text=article["title"], font=("Inter", 12, "bold"),
                        text_color=COLORS["text_dark"], anchor="w", wraplength=500, 
                        justify="left").pack(fill="x", pady=(4, 0))

    def _load_news_list_image(self, parent, img_url, article_url):
        """Load image for news list item"""
        try:
            pil_image = fetch_pil_image(img_url, mode="RGBA")
            if pil_image is None:
                return
            pil_image = fit_pil_image(pil_image, (120, 80))
            pil_image = add_rounded_corners_aa(pil_image, radius=8)
            self.after(0, self._apply_news_list_image, parent, pil_image, article_url)
        except Exception:
            pass

    def _apply_news_list_image(self, parent, pil_image, article_url):
        """Apply loaded image to news list item"""
        try:
            # Clear placeholder
            for widget in parent.winfo_children():
                widget.destroy()
            
            ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(120, 80))
            lbl = ctk.CTkLabel(parent, text="", image=ctk_img, cursor="hand2" if article_url else "")
            lbl.image = ctk_img  # Prevent GC
            lbl.pack(fill="both", expand=True)
            
            if article_url:
                lbl.bind("<Button-1>", lambda e, u=article_url: webbrowser.open(u))
        except Exception:
            pass


    def create_market_section(self, parent, row=2):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"], corner_radius=20, height=170)
        frame.grid(row=row, column=0, sticky="nsew")
        frame.grid_propagate(False)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=1)

        # Header
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkLabel(head, text="Market Watch", font=("Outfit", 18, "bold"), text_color=COLORS["text_dark"]).pack(
            side="left"
        )
        self.market_status_lbl = ctk.CTkLabel(
            head, text="Updating...", font=("Inter", 11), text_color=COLORS["text_gray"]
        )
        self.market_status_lbl.pack(side="right")

        # 12 borsa: 6'sı görünür, altta scrollbar ile kalan 6'ya kaydırılabilir
        self.market_scroll = ctk.CTkScrollableFrame(frame, orientation="horizontal", fg_color="transparent", height=100)
        self.market_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))

        # API verisini çek
        threading.Thread(target=self.fetch_market_data, daemon=True).start()

    def fetch_market_data(self):
        target_symbols = ["NVDA", "AAPL", "TSLA", "GOOG", "AMZN", "META", "MSFT", "NFLX", "MRT", "BTC", "ETH", "SOL"]
        symbols_str = ",".join(target_symbols)

        # EOD verisi: en günceli seçmek için tarihe göre filtre + DESC sort
        date_from = (date.today() - timedelta(days=14)).strftime("%Y-%m-%d")
        url = (
            f"{MARKET_BASE_URL}"
            f"?access_key={MARKET_API_KEY}"
            f"&symbols={symbols_str}"
            f"&date_from={date_from}"
            f"&sort=DESC"
            f"&limit=200"
        )

        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()

            # API "data" listesi: her sembol için birden fazla gün gelebilir
            series = {}
            as_of = None
            if isinstance(payload.get("data"), list):
                for item in payload["data"]:
                    sym = item.get("symbol")
                    close = item.get("close")
                    dt = item.get("date")
                    if not sym or close is None or not dt:
                        continue
                    # ISO string -> YYYY-MM-DD ile sıralama
                    day = str(dt)[:10]
                    try:
                        close_val = float(close)
                    except Exception:
                        continue
                    series.setdefault(sym, []).append((day, close_val, item.get("open")))
                    if as_of is None or day > as_of:
                        as_of = day

            fallback_map = {
                "NVDA": ("$450.0", "-1.2%", False),
                "AAPL": ("$173.5", "+1.2%", True),
                "TSLA": ("$240.1", "-0.8%", False),
                "GOOG": ("$138.9", "+0.5%", True),
                "AMZN": ("$127.4", "+2.1%", True),
                "META": ("$332.0", "+0.9%", True),
                "MSFT": ("$410.2", "+0.4%", True),
                "NFLX": ("$492.8", "-0.6%", False),
                "MRT": ("$2,050", "+0.2%", True),
                "BTC": ("$27K", "+0.1%", True),
                "ETH": ("$1.6K", "-0.4%", False),
                "SOL": ("$23.1", "+5.6%", True),
            }

            final_data = []
            for sym in target_symbols:
                name = MARKET_SYMBOL_NAMES.get(sym, sym)
                rows = series.get(sym, [])
                if rows:
                    rows_sorted = sorted(rows, key=lambda r: r[0], reverse=True)
                    latest_day, latest_close, latest_open = rows_sorted[0]

                    prev_close = None
                    for d, c, _o in rows_sorted[1:]:
                        if d != latest_day:
                            prev_close = c
                            break

                    # % değişim: önceki kapanış yoksa open->close kullan
                    pct = 0.0
                    if prev_close is not None and prev_close != 0:
                        pct = (latest_close - prev_close) / prev_close * 100.0
                    elif latest_open not in (None, 0, 0.0):
                        try:
                            open_val = float(latest_open)
                            if open_val != 0:
                                pct = (latest_close - open_val) / open_val * 100.0
                        except Exception:
                            pct = 0.0

                    change_text = f"{pct:+.1f}%"
                    is_positive = pct >= 0
                    price_text = f"${latest_close:,.2f}"
                    final_data.append((sym, name, price_text, change_text, is_positive))
                else:
                    if sym in fallback_map:
                        p, ch, pos = fallback_map[sym]
                        final_data.append((sym, name, p, ch, pos))
                    else:
                        final_data.append((sym, name, "N/A", "0.0%", True))

            self.after(0, self.update_market_ui, final_data, as_of)

        except Exception as e:
            print("Market API Error:", e)
            # Hata durumunda da fallback verileri kullanılabilir ama şimdilik boş kalmasın diye logluyoruz.

    def update_market_ui(self, data, as_of=None):
        # Önce temizle
        for child in self.market_scroll.winfo_children():
            child.destroy()

        for stock in data:
            tick = MarketTicker(self.market_scroll, *stock)
            tick.pack(side="left", padx=8)

        if getattr(self, "market_status_lbl", None) is not None:
            if as_of:
                self.market_status_lbl.configure(text=f"EOD: {as_of}")
            else:
                self.market_status_lbl.configure(text="EOD")

    def create_daily_read(self, parent, row=4):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"], corner_radius=20, height=170)
        frame.grid(row=row, column=0, sticky="nsew")
        frame.grid_propagate(False)

        # İçerik - Fotoğraf kaldırıldı, sadece metin kısmı
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Use grid for text (left) and image (right)
        content.grid_columnconfigure(0, weight=3)  # Text column (wider)
        content.grid_columnconfigure(1, weight=1)  # Image column
        content.grid_rowconfigure(0, weight=1)

        text_container = ctk.CTkFrame(content, fg_color="transparent")
        text_container.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        # Daily Read etiketi
        self.daily_read_label = ctk.CTkLabel(text_container, text="Today's Featured Article (Wikipedia)", font=("Inter", 12, "bold"), 
                                             text_color="#F43F5E", anchor="w")
        self.daily_read_label.pack(fill="x", padx=0, pady=(0, 6))

        # Başlık (dinamik olarak doldurulacak)
        self.daily_read_title = ctk.CTkLabel(text_container, text="Loading...", font=("Outfit", 20, "bold"),
                                             text_color=COLORS["text_dark"], anchor="w", wraplength=750, justify="left")
        self.daily_read_title.pack(fill="x", padx=0, pady=(0, 6))

        # Metin (dinamik olarak doldurulacak)
        self.daily_read_text = ctk.CTkLabel(text_container, text="", font=("Inter", 11),
                                            text_color=COLORS["text_gray"], anchor="w", wraplength=750, justify="left")
        self.daily_read_text.pack(fill="x", padx=0)

        # Buton (dinamik link ile)
        self.daily_read_btn = ctk.CTkButton(text_container, text="Read Article", fg_color="#F1F5F9", 
                                            text_color=COLORS["text_dark"], hover_color="#E2E8F0", command=self.open_daily_read_article)
        self.daily_read_btn.pack(anchor="w", padx=0, pady=(10, 0))
        
        # Image container (right side)
        self.daily_read_img_container = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=12, width=150, height=120)
        self.daily_read_img_container.grid(row=0, column=1, sticky="ne", pady=5)
        self.daily_read_img_container.grid_propagate(False)
        
        self.daily_read_img_label = ctk.CTkLabel(self.daily_read_img_container, text="📰", font=("Arial", 30), text_color=COLORS["text_gray"])
        self.daily_read_img_label.place(relx=0.5, rely=0.5, anchor="center")
        self._daily_read_ctk_image = None  # Prevent GC
        
        # Article URL'ini saklamak için
        self.daily_read_url = None

        # Wikipedia API'den veri çek
        threading.Thread(target=self.fetch_wikipedia_article, daemon=True).start()

    def fetch_wikipedia_article(self):
        """Wikipedia API'den featured article'ı çeker"""
        try:
            # Bugünün tarihini al
            today = date.today()
            api_url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/featured/{today.year}/{today.month:02d}/{today.day:02d}"
            
            # Wikipedia API User-Agent header'ı gerektirir
            headers = {
                'User-Agent': 'DailyDashboard/1.0 (https://github.com/yourusername/dailydashboard; contact@example.com)'
            }
            
            resp = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            
            # TFA (Today's Featured Article) verisini al
            if "tfa" in data:
                tfa = data["tfa"]
                title = tfa.get("title", "Article")
                # Alt çizgileri boşluklara çevir
                title = title.replace("_", " ")
                extract = tfa.get("extract", "")
                article_url = tfa.get("content_urls", {}).get("desktop", {}).get("page", "")
                
                # Get image URL from originalimage.source
                img_url = tfa.get("originalimage", {}).get("source", "")
                if not img_url:
                    # Try thumbnail as fallback
                    img_url = tfa.get("thumbnail", {}).get("source", "")
                
                # HTML etiketlerini temizle (basit)
                extract = re.sub(r'<[^>]+>', '', extract)
                
                # Metni kısalt (yaklaşık 350 karakter)
                if len(extract) > 350:
                    extract = extract[:350].rsplit(' ', 1)[0] + "..."
                
                # UI'yi güncelle
                self.after(0, self.update_daily_read_ui, title, extract, article_url, img_url)
            else:
                # Fallback
                self.after(0, self.update_daily_read_ui, "Featured Article", 
                          "No featured article available today.", "", "")
                
        except Exception as e:
            print(f"Wikipedia API Error: {e}")
            # Fallback
            self.after(0, self.update_daily_read_ui, "Featured Article", 
                      "Unable to load featured article.", "", "")

    def update_daily_read_ui(self, title, text, url, img_url=""):
        """Daily Read UI'sini günceller"""
        self.daily_read_title.configure(text=title)
        self.daily_read_text.configure(text=text)
        self.daily_read_url = url
        
        # Load image if available
        if img_url:
            threading.Thread(target=self._load_daily_read_image, args=(img_url,), daemon=True).start()
    
    def _load_daily_read_image(self, img_url):
        """Loads Wikipedia article image in background"""
        try:
            pil_image = fetch_pil_image(img_url, mode="RGBA")
            if pil_image is None:
                return
            
            # Resize to fit container (150x120)
            pil_image = fit_pil_image(pil_image, (150, 120))
            pil_image = add_rounded_corners_aa(pil_image, radius=12, corners=(True, True, True, True), scale=4)
            
            # Apply to UI on main thread
            self.after(0, self._apply_daily_read_image, pil_image)
        except Exception as e:
            print(f"Error loading Wikipedia image: {e}")
    
    def _apply_daily_read_image(self, pil_image):
        """Applies loaded image to daily read widget"""
        self._daily_read_ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(150, 120))
        self.daily_read_img_label.configure(image=self._daily_read_ctk_image, text="")

    def open_daily_read_article(self):
        """Makaleyi tarayıcıda açar"""
        if self.daily_read_url:
            webbrowser.open(self.daily_read_url)

    def create_weather_widget(self, parent, row=0):
        # Mavi Gradient efektini simüle eden düz renk
        frame = ctk.CTkFrame(parent, fg_color=COLORS["weather_grad"], corner_radius=20, height=170)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
        frame.pack_propagate(False)

        # İçerik
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=12)

        self.weather_loc_lbl = ctk.CTkLabel(top, text="Istanbul, TR", text_color="white", font=("Outfit", 14, "bold"))
        self.weather_loc_lbl.pack(anchor="w")
        ctk.CTkLabel(top, text="Today, 12 Oct", text_color="#E0E7FF", font=("Inter", 11)).pack(anchor="w")

        # Güneş ikonu (Metin olarak)
        ctk.CTkLabel(top, text="☀", text_color="#FDE047", font=("Arial", 30)).place(relx=1.0, y=0, anchor="ne")

        # Derece
        mid = ctk.CTkFrame(frame, fg_color="transparent")
        mid.pack(fill="x", padx=18)
        self.weather_temp_lbl = ctk.CTkLabel(mid, text="--°C", text_color="white", font=("Outfit", 34, "bold"))
        self.weather_temp_lbl.pack(anchor="w")
        self.weather_desc_lbl = ctk.CTkLabel(mid, text="Loading...", text_color="#E0E7FF", font=("Inter", 12))
        self.weather_desc_lbl.pack(anchor="w")

        # Alt detay
        bot = ctk.CTkFrame(frame, fg_color="transparent")
        bot.pack(fill="x", padx=18, pady=(6, 0))
        self.weather_detail_lbl = ctk.CTkLabel(bot, text="...", text_color="#E0E7FF", font=("Inter", 11))
        self.weather_detail_lbl.pack(anchor="w")

        # API'den veri çek
        threading.Thread(target=self.fetch_weather_data, daemon=True).start()

    def fetch_weather_data(self):
        try:
            resp = requests.get(WEATHER_API_URL, timeout=10)
            data = resp.json()
            if "current" in data:
                curr = data["current"]
                loc = data.get("location", {})

                temp = curr.get("temperature", "--")
                desc = curr.get("weather_descriptions", ["N/A"])[0]
                wind = curr.get("wind_speed", 0)
                humi = curr.get("humidity", 0)
                city = loc.get("name", "Unknown")
                country = loc.get("country", "")

                # UI Update (Main Thread)
                self.after(0, self.update_weather_ui, temp, desc, wind, humi, city, country)
        except Exception as e:
            print("Weather API Error:", e)

    def update_weather_ui(self, temp, desc, wind, humi, city, country):
        self.weather_temp_lbl.configure(text=f"{temp}°C")
        self.weather_desc_lbl.configure(text=desc)
        self.weather_detail_lbl.configure(text=f"💧 {humi}%   💨 {wind}km/h")
        if city != "Unknown":
            self.weather_loc_lbl.configure(text=f"{city}, {country}")

    def create_planner_widget(self, parent, row=1):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"], corner_radius=20, height=170)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
        frame.pack_propagate(False)

        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(head, text="Planner", font=("Outfit", 18, "bold"), text_color=COLORS["text_dark"]).pack(
            side="left")
        
        # Clickable "+" button
        add_btn = ctk.CTkLabel(head, text="+", font=("Arial", 20), text_color=COLORS["primary"], cursor="hand2")
        add_btn.pack(side="right")
        add_btn.bind("<Button-1>", lambda e: self.open_add_planner_popup())

        # Scroll: sığmayan etkinlikleri panel içinde kaydır
        self.planner_box = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.planner_box.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Load planner data from database
        self.load_planner_data()

    def open_add_planner_popup(self):
        """Opens popup to add a new planner entry"""
        popup = ctk.CTkToplevel(self)
        popup.title("Add Reminder")
        popup.geometry("350x260")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)
        popup.configure(fg_color=COLORS["card_bg"])
        
        # Center the popup
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 175
        y = self.winfo_y() + (self.winfo_height() // 2) - 130
        popup.geometry(f"+{x}+{y}")
        
        # Title
        ctk.CTkLabel(popup, text="Add New Reminder", font=("Outfit", 18, "bold"),
                     text_color=COLORS["text_dark"]).pack(anchor="w", padx=20, pady=(20, 15))
        
        # Date input
        ctk.CTkLabel(popup, text="Date", font=("Inter", 12, "bold"),
                     text_color=COLORS["text_dark"]).pack(anchor="w", padx=20)
        date_entry = ctk.CTkEntry(popup, placeholder_text="YYYY-MM-DD", height=38,
                                   fg_color=COLORS["input_bg"], border_width=1, 
                                   border_color="#E2E8F0", corner_radius=8)
        date_entry.pack(fill="x", padx=20, pady=(5, 12))
        
        # Set default date to today
        from datetime import date as dt_date
        date_entry.insert(0, dt_date.today().strftime("%Y-%m-%d"))
        
        # Text input
        ctk.CTkLabel(popup, text="Reminder (max 96 chars)", font=("Inter", 12, "bold"),
                     text_color=COLORS["text_dark"]).pack(anchor="w", padx=20)
        text_entry = ctk.CTkEntry(popup, placeholder_text="Enter your reminder...", height=38,
                                   fg_color=COLORS["input_bg"], border_width=1,
                                   border_color="#E2E8F0", corner_radius=8)
        text_entry.pack(fill="x", padx=20, pady=(5, 15))
        
        # Character limit enforcement
        def limit_chars(*args):
            current = text_entry.get()
            if len(current) > 96:
                text_entry.delete(96, "end")
        text_entry.bind("<KeyRelease>", limit_chars)
        
        # Save button
        def on_save():
            date_val = date_entry.get().strip()
            text_val = text_entry.get().strip()[:96]  # Enforce max 96 chars
            
            if not date_val or not text_val:
                return
            
            # Validate date format
            try:
                from datetime import datetime
                datetime.strptime(date_val, "%Y-%m-%d")
            except ValueError:
                return
            
            self.save_planner_entry(date_val, text_val)
            popup.destroy()
        
        save_btn = ctk.CTkButton(popup, text="Save", font=("Inter", 14, "bold"),
                                  fg_color=COLORS["primary"], hover_color=COLORS["primary_dark"],
                                  height=42, width=150, corner_radius=10, command=on_save)
        save_btn.pack(pady=(0, 20))

    def save_planner_entry(self, date_val, text_val):
        """Saves planner entry to database"""
        try:
            connection = mysql.connector.connect(
                host="fedora",
                user="root",
                password="qAzWsX!1928",  
                database="dailydashboard"
            )
            cursor = connection.cursor()
            
            insert_query = "INSERT INTO planner (username, date, text) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (self.username, date_val, text_val))
            connection.commit()
            
            cursor.close()
            connection.close()
            
            # Refresh planner display
            self.refresh_planner()
            
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
        except Exception as e:
            print(f"Error: {e}")

    def load_planner_data(self):
        """Loads planner entries from database for current user"""
        try:
            connection = mysql.connector.connect(
                host="fedora",
                user="root",
                password="qAzWsX!1928",  
                database="dailydashboard"
            )
            cursor = connection.cursor()
            
            # Get entries ordered by date
            query = "SELECT date, text FROM planner WHERE username = %s ORDER BY date ASC"
            cursor.execute(query, (self.username,))
            results = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            # Clear existing items
            for widget in self.planner_box.winfo_children():
                widget.destroy()
            
            if results:
                from datetime import date as dt_date
                today = dt_date.today()
                
                for entry_date, entry_text in results:
                    # Format date for display
                    if isinstance(entry_date, str):
                        from datetime import datetime
                        entry_date = datetime.strptime(entry_date, "%Y-%m-%d").date()
                    
                    date_str = entry_date.strftime("%b %d")
                    full_date_str = entry_date.strftime("%Y-%m-%d")
                    day_num = entry_date.strftime("%d")
                    is_today = entry_date == today
                    
                    PlannerItem(self.planner_box, date_str, entry_text, 
                               circle_text=day_num, is_active=is_today,
                               full_text=entry_text, full_date=full_date_str,
                               app_ref=self).pack(fill="x", pady=2)
            else:
                # Show empty state
                empty_lbl = ctk.CTkLabel(self.planner_box, text="No reminders yet", 
                                         text_color=COLORS["text_gray"], font=("Inter", 12))
                empty_lbl.pack(pady=20)
            
            # Free Slot indicator
            free = ctk.CTkFrame(self.planner_box, fg_color="transparent", border_width=1, 
                               border_color="#CBD5E1", corner_radius=12)
            free.pack(fill="x", pady=4)
            ctk.CTkLabel(free, text="Click + to add reminder", text_color="#94A3B8").pack(pady=6)
                
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
        except Exception as e:
            print(f"Error: {e}")

    def refresh_planner(self):
        """Refreshes planner display"""
        self.load_planner_data()


    def create_notes_widget(self, parent, row=2):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"], corner_radius=20, height=170)
        frame.grid(row=row, column=0, sticky="nsew")
        frame.pack_propagate(False)

        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(10, 6))
        ctk.CTkLabel(head, text="Quick Notes", font=("Outfit", 18, "bold"), text_color=COLORS["text_dark"]).pack(
            side="left")

        # Input + Save
        input_row = ctk.CTkFrame(frame, fg_color="transparent")
        input_row.pack(fill="x", padx=20)
        input_row.grid_columnconfigure(0, weight=1)

        txt = ctk.CTkTextbox(input_row, height=45, fg_color=COLORS["input_bg"], text_color=COLORS["text_dark"],
                             corner_radius=12)
        txt.grid(row=0, column=0, sticky="ew")
        txt.insert("0.0", "")

        # Saved notes list (scroll) - instance variable olarak sakla
        self.notes_list = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.notes_list.pack(fill="both", expand=True, padx=20, pady=(8, 8))

        foot = ctk.CTkFrame(frame, fg_color="transparent")
        foot.pack(fill="x", padx=20, pady=(0, 8))
        self.last_saved_lbl = ctk.CTkLabel(foot, text="No notes saved yet", text_color=COLORS["text_gray"], font=("Inter", 10))
        self.last_saved_lbl.pack(side="left")

        def on_save():
            note = txt.get("0.0", "end").strip()
            if not note or note == "":
                return
            
            # Veritabanına kaydet
            try:
                connection = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="",
                    database="dailydashboard"
                )
                cursor = connection.cursor()
                
                insert_query = "INSERT INTO notes (username, text) VALUES (%s, %s)"
                cursor.execute(insert_query, (self.username, note))
                connection.commit()
                
                cursor.close()
                connection.close()
                
                # UI'ya ekle
                txt.delete("0.0", "end")
                self.add_note_to_ui(note)
                self.last_saved_lbl.configure(text="Saved just now")
                
            except mysql.connector.Error as err:
                print(f"Database error: {err}")
            except Exception as e:
                print(f"Error: {e}")

        save_btn = ctk.CTkButton(input_row, text="Save", width=70, fg_color=COLORS["primary"],
                                 hover_color=COLORS["primary_dark"], command=on_save)
        save_btn.grid(row=0, column=1, padx=(10, 0), sticky="e")

        # Kullanıcının notlarını yükle
        self.load_user_notes()

    def add_note_to_ui(self, note_text):
        """Notu UI'ya ekler"""
        card = ctk.CTkFrame(self.notes_list, fg_color=COLORS["input_bg"], corner_radius=12)
        card.pack(fill="x", padx=2, pady=4)
        ctk.CTkLabel(card, text=note_text, text_color=COLORS["text_dark"], font=("Inter", 11),
                     wraplength=260, justify="left", anchor="w").pack(fill="x", padx=10, pady=8)

    def load_user_notes(self):
        """Kullanıcının notlarını veritabanından yükler"""
        try:
            connection = mysql.connector.connect(
                host="fedora",
                user="root",
                password="qAzWsX!1928",  
                database="dailydashboard"
            )
            cursor = connection.cursor()
            
            query = "SELECT text FROM notes WHERE username = %s ORDER BY id DESC"
            cursor.execute(query, (self.username,))
            results = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            # Notları UI'ya ekle
            if results:
                for (note_text,) in results:
                    self.add_note_to_ui(note_text)
                self.last_saved_lbl.configure(text=f"{len(results)} notes loaded")
            else:
                self.last_saved_lbl.configure(text="No notes saved yet")
                
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            self.last_saved_lbl.configure(text="Error loading notes")
        except Exception as e:
            print(f"Error: {e}")
            self.last_saved_lbl.configure(text="Error loading notes")


if __name__ == "__main__":
    app = App()
    app.mainloop()
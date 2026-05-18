import customtkinter as ctk
import subprocess
import sys
import mysql.connector
from tkinter import messagebox

# Renk Paleti
COLORS = {
    "bg": "#f3f4f6",  # Arka plan (Gray-100)
    "card_bg": "#ffffff",  # Kart rengi (White)
    "primary": "#6366f1",  # Buton rengi (Indigo-500)
    "primary_hover": "#4f46e5",  # Buton hover (Indigo-600)
    "text_main": "#1f2937",  # Ana metin (Gray-800)
    "text_sub": "#6b7280",  # Alt metin (Gray-500)
    "input_bg": "#f9fafb",  # Input arka planı (Gray-50)
    "input_border": "#e5e7eb",  # Input kenarlığı (Gray-200)
    "icon_bg": "#e0e7ff",  # Logo arka planı (Indigo-100)
    "icon_text": "#4338ca",  # Logo ikonu (Indigo-700)
    "link_text": "#4f46e5"  # Linkler için renk (Yeni eklendi)
}


class SignUpApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Pencere Ayarları
        self.title("Daily Dashboard - Kayıt Ol")
        self.geometry("900x800")
        self.configure(fg_color=COLORS["bg"])

        # Entry widget'ları saklamak için
        self.name_entry = None
        self.username_entry = None
        self.password_entry = None

        # Ana Kartı Oluştur
        self.create_main_card()

    def create_main_card(self):
        # Kart Çerçevesi
        self.card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            corner_radius=25,
            width=500,
            height=640  # Footer eklendiği için yüksekliği biraz artırdım
        )
        self.card.place(relx=0.5, rely=0.5, anchor="center")

        # İçerik konteyner'ı
        self.content_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.content_frame.pack(padx=50, pady=50, fill="both", expand=True)

        # --- HEADER ---
        self.create_header()

        # --- BAŞLIKLAR ---
        title_label = ctk.CTkLabel(
            self.content_frame,
            text="Hesap Oluştur",
            font=("Inter", 26, "bold"),
            text_color=COLORS["text_main"]
        )
        title_label.pack(pady=(0, 5))

        # --- FORM ALANLARI ---

        # İsim Alanı
        self.name_entry = self.create_input_field("İsim", "İsminizi Giriniz", "👤")

        # Kullanıcı Adı Alanı
        self.username_entry = self.create_input_field("Kullanıcı Adı", "Kullanıcı Adı Giriniz", "✉️")

        # Şifre Alanı
        self.password_entry = self.create_input_field("Şifre", "••••••••", "🔒", is_password=True)

        # --- KAYIT OL BUTONU ---
        self.signup_button = ctk.CTkButton(
            self.content_frame,
            text="Kayıt Ol",
            font=("Inter", 16, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="white",
            height=50,
            corner_radius=12,
            cursor="hand2",
            command=self.handle_signup
        )
        self.signup_button.pack(fill="x", pady=(20, 0))

        # --- HESABIN VAR MI? (Yeni) ---
        self.create_footer_link()

    def create_header(self):
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(pady=(0, 20))

        # Logo kutusu
        logo_box = ctk.CTkFrame(
            header_frame,
            fg_color=COLORS["icon_bg"],
            width=40,
            height=40,
            corner_radius=8
        )
        logo_box.pack(side="left", padx=(0, 10))
        logo_box.pack_propagate(False)

        logo_icon = ctk.CTkLabel(
            logo_box,
            text="⊞",
            text_color=COLORS["icon_text"],
            font=("Arial", 24)
        )
        logo_icon.place(relx=0.5, rely=0.5, anchor="center")

        app_name = ctk.CTkLabel(
            header_frame,
            text="Daily Dashboard",
            font=("Inter", 18, "bold"),
            text_color=COLORS["text_main"]
        )
        app_name.pack(side="left")

    def create_input_field(self, label_text, placeholder, icon_char, is_password=False):
        # 1. Label
        lbl = ctk.CTkLabel(
            self.content_frame,
            text=label_text,
            font=("Inter", 13, "bold"),
            text_color=COLORS["text_main"],
            anchor="w"
        )
        lbl.pack(fill="x", pady=(10, 5))

        # 2. Input Konteyner
        input_container = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS["input_bg"],
            border_width=1,
            border_color=COLORS["input_border"],
            corner_radius=10,
            height=50
        )
        input_container.pack(fill="x", pady=(0, 5))
        input_container.pack_propagate(False)

        # 3. İkon
        icon_lbl = ctk.CTkLabel(
            input_container,
            text=icon_char,
            text_color=COLORS["text_sub"],
            font=("Arial", 18),
            width=40
        )
        icon_lbl.pack(side="left", padx=(5, 0))

        # 4. Entry
        entry = ctk.CTkEntry(
            input_container,
            placeholder_text=placeholder,
            placeholder_text_color="#9ca3af",
            fg_color="transparent",
            border_width=0,
            text_color=COLORS["text_main"],
            font=("Inter", 14),
            show="•" if is_password else ""
        )
        entry.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        return entry

    def handle_signup(self):
        """Kayıt işlemini gerçekleştirir"""
        # ÖNEMLİ: name_entry -> name sütununa, username_entry -> username sütununa
        name = self.name_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        # Validasyon
        if not name or not username or not password:
            messagebox.showwarning("Uyarı", "Lütfen tüm alanları doldurunuz!")
            return

        if len(password) < 6:
            messagebox.showwarning("Uyarı", "Şifre en az 6 karakter olmalıdır!")
            return

        try:
            # MySQL bağlantısı
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="dailydashboard"
            )
            cursor = connection.cursor()

            # Kullanıcı adı kontrolü (zaten var mı?)
            check_query = "SELECT username FROM users WHERE username = %s"
            cursor.execute(check_query, (username,))
            if cursor.fetchone():
                messagebox.showerror("Hata", "Bu kullanıcı adı zaten kullanılıyor!")
                cursor.close()
                connection.close()
                return

            # Kullanıcıyı veritabanına ekle
            # ÖNEMLİ: name_entry'den alınan -> name sütununa, username_entry'den alınan -> username sütununa
            # INSERT sorgusu: (name, username, password) sırasıyla
            insert_query = "INSERT INTO users (name, username, password) VALUES (%s, %s, %s)"
            # Değerler: (name_entry'den gelen, username_entry'den gelen, password)
            cursor.execute(insert_query, (name, username, password))
            connection.commit()
        
            cursor.close()
            connection.close()

            # Başarılı kayıt
            messagebox.showinfo("Başarılı", "Kayıt başarıyla oluşturuldu! Giriş sayfasına yönlendiriliyorsunuz...")
            
            # Signin sayfasına yönlendir
            self.open_signin()

        except mysql.connector.Error as err:
            messagebox.showerror("Veritabanı Hatası", f"Bağlantı hatası: {err}")
        except Exception as e:
            messagebox.showerror("Hata", f"Bir hata oluştu: {e}")

    def open_signin(self):
        """Giriş sayfasını açar ve signup penceresini kapatır"""
        self.withdraw()  # Signup penceresini gizle
        
        # signin.py'yi çalıştır
        subprocess.Popen([sys.executable, "signin.py"])
        
        # Signup penceresini tamamen kapat
        self.after(500, self.destroy)

    def create_footer_link(self):
        # Alt kısımda "Giriş Yap" yönlendirmesi için frame
        footer_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer_frame.pack(side="bottom", pady=(15, 0))  # Biraz daha boşluk

        text_label = ctk.CTkLabel(
            footer_frame,
            text="Hesabın var mı?",
            font=("Inter", 13),
            text_color=COLORS["text_sub"]
        )
        text_label.pack(side="left", padx=(0, 5))

        login_btn = ctk.CTkButton(
            footer_frame,
            text="Giriş Yap",
            font=("Inter", 13, "bold"),
            fg_color="transparent",
            text_color=COLORS["link_text"],
            hover_color=COLORS["bg"],
            width=50,
            cursor="hand2",
            command=self.open_signin
        )
        login_btn.pack(side="left")


if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    app = SignUpApp()
    app.mainloop()
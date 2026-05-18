import customtkinter as ctk
import mysql.connector
from tkinter import messagebox
import subprocess
import sys

# Renk Paleti (Aynı renkler korundu)
COLORS = {
    "bg": "#f3f4f6",  # Arka plan
    "card_bg": "#ffffff",  # Kart rengi
    "primary": "#6366f1",  # Buton rengi
    "primary_hover": "#4f46e5",  # Buton hover
    "text_main": "#1f2937",  # Ana metin
    "text_sub": "#6b7280",  # Alt metin
    "input_bg": "#f9fafb",  # Input arka planı
    "input_border": "#e5e7eb",  # Input kenarlığı
    "icon_bg": "#e0e7ff",  # Logo arka planı
    "icon_text": "#4338ca",  # Logo ikonu
    "link_text": "#4f46e5"  # Linkler için renk (Yeni eklendi)
}


class SignInApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Pencere Ayarları
        self.title("Daily Dashboard - Giriş Yap")
        self.geometry("900x800")
        self.configure(fg_color=COLORS["bg"])

        # Entry widget'ları saklamak için
        self.username_entry = None
        self.password_entry = None

        # Ana Kartı Oluştur
        self.create_main_card()

    def create_main_card(self):
        # Kart Çerçevesi (Yükseklik biraz düşürüldü çünkü alan azaldı)
        self.card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            corner_radius=25,
            width=500,
            height=550
        )
        self.card.place(relx=0.5, rely=0.5, anchor="center")

        # İçerik konteyner'ı
        self.content_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.content_frame.pack(padx=50, pady=50, fill="both", expand=True)

        # --- HEADER ---
        self.create_header()

        # --- BAŞLIK ---
        title_label = ctk.CTkLabel(
            self.content_frame,
            text="Tekrar Hoşgeldiniz",
            font=("Inter", 26, "bold"),
            text_color=COLORS["text_main"]
        )
        title_label.pack(pady=(0, 5))

        subtitle_label = ctk.CTkLabel(
            self.content_frame,
            text="Devam etmek için giriş yapın",
            font=("Inter", 14),
            text_color=COLORS["text_sub"]
        )
        subtitle_label.pack(pady=(0, 20))

        # --- FORM ALANLARI ---

        # Email / Kullanıcı Adı
        self.username_entry = self.create_input_field("Kullanıcı Adı", "Kullanıcı Adınızı Giriniz", "✉️")

        # Şifre
        self.password_entry = self.create_input_field("Şifre", "••••••••", "🔒", is_password=True)



        # --- GİRİŞ YAP BUTONU ---
        self.login_button = ctk.CTkButton(
            self.content_frame,
            text="Giriş Yap",
            font=("Inter", 16, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="white",
            height=50,
            corner_radius=12,
            cursor="hand2",
            command=self.handle_login
        )
        self.login_button.pack(fill="x", pady=(0, 20))

        # --- HESABIN YOK MU? (Yeni) ---
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
        # Label
        lbl = ctk.CTkLabel(
            self.content_frame,
            text=label_text,
            font=("Inter", 13, "bold"),
            text_color=COLORS["text_main"],
            anchor="w"
        )
        lbl.pack(fill="x", pady=(10, 5))

        # Input Konteyner
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

        # İkon
        icon_lbl = ctk.CTkLabel(
            input_container,
            text=icon_char,
            text_color=COLORS["text_sub"],
            font=("Arial", 18),
            width=40
        )
        icon_lbl.pack(side="left", padx=(5, 0))

        # Entry
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

    def handle_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Uyarı", "Lütfen kullanıcı adı ve şifre giriniz!")
            return

        try:
            # MySQL bağlantısı
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",  # root için şifre yoksa boş bırak
                database="dailydashboard"
            )
            cursor = connection.cursor()

            # Kullanıcı sorgula (name ve password sütunlarını al)
            query = "SELECT name, password FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()

            cursor.close()
            connection.close()

            if result and len(result) == 2:
                user_name, stored_password = result
                
                # Şifreyi string'e çevir (MySQL bazen bytes döndürebilir)
                if isinstance(stored_password, bytes):
                    stored_password = stored_password.decode('utf-8')
                elif stored_password:
                    stored_password = str(stored_password).strip()
                
                # Şifre kontrolü
                if not stored_password:
                    messagebox.showerror("Hata", "Kullanıcı bilgileri hatalı!")
                    return
                
                # Şifreyi direkt karşılaştır
                if password == stored_password:
                    # Giriş başarılı
                    messagebox.showinfo("Başarılı", "Giriş başarılı! Dashboard açılıyor...")
                    self.withdraw()  # Signin penceresini gizle
                    
                    # main.py'yi kullanıcı adı ve username ile birlikte çalıştır
                    subprocess.Popen([sys.executable, "main.py", user_name, username])
                    
                    # Signin penceresini tamamen kapat
                    self.after(500, self.destroy)
                else:
                    # Şifre yanlış
                    messagebox.showerror("Hata", "Kullanıcı adı veya şifre yanlış!")
            else:
                # Kullanıcı bulunamadı
                messagebox.showerror("Hata", "Kullanıcı adı veya şifre yanlış!")

        except mysql.connector.Error as err:
            messagebox.showerror("Veritabanı Hatası", f"Bağlantı hatası: {err}")
        except Exception as e:
            messagebox.showerror("Hata", f"Bir hata oluştu: {e}")

    def open_signup(self):
        """Kayıt sayfasını açar ve signin penceresini kapatır"""
        self.withdraw()  # Signin penceresini gizle
        
        # signup.py'yi çalıştır
        subprocess.Popen([sys.executable, "signup.py"])
        
        # Signin penceresini tamamen kapat
        self.after(500, self.destroy)

    def create_footer_link(self):
        # Alt kısımda "Kayıt Ol" yönlendirmesi için frame
        footer_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer_frame.pack(side="bottom", pady=(10, 0))

        text_label = ctk.CTkLabel(
            footer_frame,
            text="Hesabın yok mu?",
            font=("Inter", 13),
            text_color=COLORS["text_sub"]
        )
        text_label.pack(side="left", padx=(0, 5))

        register_btn = ctk.CTkButton(
            footer_frame,
            text="Kayıt Ol",
            font=("Inter", 13, "bold"),
            fg_color="transparent",
            text_color=COLORS["link_text"],
            hover_color=COLORS["bg"],
            width=50,
            cursor="hand2",
            command=self.open_signup
        )
        register_btn.pack(side="left")


if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    app = SignInApp()
    app.mainloop()
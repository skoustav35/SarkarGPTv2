import yfinance as yf
import mplfinance as mpf
import pandas as pd
import sys, os, json, io, base64, threading, traceback
from datetime import datetime
from functools import partial

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from PIL import Image, ImageQt, ImageEnhance, ImageFilter

import requests
from deep_translator import GoogleTranslator

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_JUSTIFY
    from reportlab.lib import colors
    from reportlab.lib.units import cm, inch
except ImportError:
    SimpleDocTemplate = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QStackedWidget, QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QFileDialog, QMessageBox,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QFormLayout, QTabWidget, QSlider, QFrame,
    QSplitter, QInputDialog, QDialogButtonBox, QSizePolicy, QScrollArea, QRadioButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QIcon, QPixmap, QAction, QColor, QFont, QPalette, QBrush, QPen, QImage, QMovie
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QSize, QEvent, QRect, QPoint,
    QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup
)


APP_DATA_DIR = "SarkarGPT_Data"
if not os.path.exists(APP_DATA_DIR):
    os.makedirs(APP_DATA_DIR)

DEFAULT_KEYS = {
    "openai": "sk-your-default-openai-key",
    "gemini": "your-default-gemini-key",
    "gemini_image": "your-default-gemini-image-key",
    "anthropic": "your-default-anthropic-key",
    "perplexity": "your-default-perplexity-key",
    "grok": "your-default-grok-key"
}

API_KEY_FILE = os.path.join(APP_DATA_DIR, "api_keys.json")
PREF_FILE = os.path.join(APP_DATA_DIR, "preferences.json")
TEMPLATES_FILE = os.path.join(APP_DATA_DIR, "templates.json")
CHAT_MEMORY_FILE = os.path.join(APP_DATA_DIR, "chat_memory.json")


ICONS_DIR = "icons"
if not os.path.exists(ICONS_DIR):
    os.makedirs(ICONS_DIR)


def ensure_file(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)

DEFAULT_THEME_NAME = "Azure Sky"
DEFAULT_PREFS = {
    "theme": DEFAULT_THEME_NAME,
    "use_default_keys": True,
    "active_template": "No Template",
    "remember_messages": True,
    "ai_mindset_preset": "Neutral",
    "ai_mindset_custom": ""
}

ensure_file(API_KEY_FILE, {})
ensure_file(PREF_FILE, DEFAULT_PREFS)
ensure_file(TEMPLATES_FILE, {"No Template": ""})
ensure_file(CHAT_MEMORY_FILE, [])


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class Signals(QObject):
    chat_reply = pyqtSignal(str, str)
    translate_done = pyqtSignal(str)
    image_gen_done = pyqtSignal(object)
    image_to_graph_done = pyqtSignal(str)
    book_gen_done = pyqtSignal(str)
    stock_overview_done = pyqtSignal(str)
    stock_analytics_done = pyqtSignal(str)
    stock_graph_done = pyqtSignal(object)
    business_assist_done = pyqtSignal(str)


signals = Signals()


THEME_SETS = {
    "Crimson Night": {
        "bg": "#2B0000",
        "card_bg": "#4F0000",
        "accent": "#FF4136",
        "text": "#FFD1D1",
        "user_text": "#FFD1D1",
        "ai_text": "#FF4136",
        "border_dark": "rgba(255, 65, 54, 0.4)",
        "shadow_dark": "rgba(0,0,0,0.6)",
        "glass": "rgba(255, 65, 54, 0.1)",
        "glow": "rgba(255, 65, 54, 0.4)",
        "sidebar_bg": "rgba(10, 0, 0, 0.7)",
        "is_dark": True
    },
    "Emerald Forest": {
        "bg": "#EFFFF4",
        "card_bg": "#FFFFFF",
        "accent": "#008A3D",
        "text": "#003311",
        "user_text": "#003311",
        "ai_text": "#008A3D",
        "border_light": "rgba(0,0,0,0.15)",
        "shadow_light": "rgba(0, 50, 10, 0.15)",
        "glass": "rgba(0, 138, 61, 0.08)",
        "glow": "rgba(0, 138, 61, 0.35)",
        "sidebar_bg": "#E6F5EC",
        "is_dark": False
    },
    "Azure Sky": {
        "bg": "#F0F8FF",
        "card_bg": "#FFFFFF",
        "accent": "#007BFF",
        "text": "#223344",
        "user_text": "#223344",
        "ai_text": "#0056B3",
        "border_light": "rgba(0,0,0,0.15)",
        "shadow_light": "rgba(0, 50, 100, 0.15)",
        "glass": "rgba(0, 123, 255, 0.08)",
        "glow": "rgba(0, 123, 255, 0.35)",
        "sidebar_bg": "#E6F2FF",
        "is_dark": False
    },
    "Royal Purple": {
        "bg": "#1A0033",
        "card_bg": "#2E005C",
        "accent": "#9D4EDD",
        "text": "#F0E6FF",
        "user_text": "#F0E6FF",
        "ai_text": "#C77DFF",
        "border_dark": "rgba(157, 78, 221, 0.4)",
        "shadow_dark": "rgba(0,0,0,0.5)",
        "glass": "rgba(157, 78, 221, 0.1)",
        "glow": "rgba(157, 78, 221, 0.4)",
        "sidebar_bg": "rgba(10, 0, 20, 0.7)",
        "is_dark": True
    },
    "Slate & Orange": {
        "bg": "#30415D",
        "card_bg": "#4A5568",
        "accent": "#F56565",
        "text": "#E2E8F0",
        "user_text": "#E2E8F0",
        "ai_text": "#F56565",
        "border_dark": "rgba(245, 101, 101, 0.4)",
        "shadow_dark": "rgba(0,0,0,0.5)",
        "glass": "rgba(245, 101, 101, 0.1)",
        "glow": "rgba(245, 101, 101, 0.4)",
        "sidebar_bg": "rgba(20, 30, 45, 0.7)",
        "is_dark": True
    },
    "Warm Ivory": {
        "bg": "#FFFBF0",
        "card_bg": "#FFFFFF",
        "accent": "#D2691E",
        "text": "#4A3B2A",
        "user_text": "#4A3B2A",
        "ai_text": "#B85B1A",
        "border_light": "rgba(0,0,0,0.15)",
        "shadow_light": "rgba(100, 50, 0, 0.15)",
        "glass": "rgba(210, 105, 30, 0.08)",
        "glow": "rgba(210, 105, 30, 0.35)",
        "sidebar_bg": "#FFF8E8",
        "is_dark": False
    }
}


def english_number(n):
    try:
        s = f"{float(n):,.2f}"
    except Exception:
        try:
            s = f"{int(n):,d}"
        except Exception:
            s = str(n)
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹০১২৩৪۵۶৭۸৯", "01234s6789012345678901234s6789")
    return s.translate(trans)

def pil_to_qpixmap(pil_image, maxsize=None):
    if pil_image is None:
        return QPixmap()
    img = pil_image.copy()
    if maxsize:
        img.thumbnail(maxsize, Image.Resampling.LANCZOS)
    qim = ImageQt.ImageQt(img.convert("RGBA"))
    pix = QPixmap.fromImage(qim)
    return pix

def cv2_to_qpixmap(cv_image, maxsize=None):
    if cv_image is None:
        return QPixmap()
    try:
        h, w, ch = cv_image.shape
        bytes_per_line = ch * w
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        if maxsize:
            pixmap = pixmap.scaled(maxsize[0], maxsize[1], Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return pixmap
    except Exception as e:
        return QPixmap()

def pil_to_base64(pil_image, format="PNG"):
    buf = io.BytesIO()
    pil_image.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def base64_to_pil(b64_string):
    img_data = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(img_data))

def get_icon_path(icon_name):
    path = os.path.join(ICONS_DIR, f"{icon_name}.png")
    if not os.path.exists(path):
        path = os.path.join(ICONS_DIR, "default_icon.png")
        if not os.path.exists(path):
            try:
                img = Image.new('RGBA', (32, 32), (0,0,0,0))
                img.save(path)
            except Exception:
                return ""
    return path


class SarkarGPTPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SarkarGPT Pro v3")
        self.resize(1600, 900)

        self.saved_keys = load_json(API_KEY_FILE, {})
        self.prefs = load_json(PREF_FILE, DEFAULT_PREFS)
        self.templates = load_json(TEMPLATES_FILE, {"No Template": ""})
        self.chat_memory = load_json(CHAT_MEMORY_FILE, [])

        self.use_defaults = self.prefs.get("use_default_keys", True)
        self.active_template = self.prefs.get("active_template", "No Template")
        self.remember_messages = self.prefs.get("remember_messages", True)
        self.current_theme = self.prefs.get("theme", DEFAULT_THEME_NAME)
        self.ai_mindset_preset = self.prefs.get("ai_mindset_preset", "Neutral")
        self.ai_mindset_custom = self.prefs.get("ai_mindset_custom", "")

        if self.current_theme not in THEME_SETS:
            self.current_theme = DEFAULT_THEME_NAME
            self.prefs['theme'] = DEFAULT_THEME_NAME
            save_json(PREF_FILE, self.prefs)

        self.current_theme_colors = THEME_SETS[self.current_theme]

        self.img2g_pil_image = None
        self._bill_items = []
        self.book_chapters = []

        self.streaming_timer = None
        self.current_stock_ticker = None
        self.model_queue = []
        
        self.chat_image_paths = []
        self.current_chat_images = []

        self._build_ui()

        signals.chat_reply.connect(self._on_chat_reply)
        signals.translate_done.connect(self._on_translate_done)
        signals.image_gen_done.connect(self._on_generate_image_done)
        signals.image_to_graph_done.connect(self._on_image_to_graph_done)
        signals.book_gen_done.connect(self._on_book_gen_done)
        signals.stock_overview_done.connect(self._on_stock_overview_done)
        signals.stock_analytics_done.connect(self._on_stock_analytics_done)
        signals.stock_graph_done.connect(self._on_stock_graph_done)
        signals.business_assist_done.connect(self._on_business_assist_done)

        self.apply_theme(self.current_theme)


    def _update_nav_selection(self, active_name):
        for name, btn in self.nav_buttons.items():
            if name == active_name:
                btn.setProperty("active", True)
            else:
                btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setSpacing(8)
        s_layout.setContentsMargins(10, 10, 10, 10)

        app_logo_label = QLabel()
        app_logo_pixmap = QPixmap(":/icons/app_logo.png")
        app_logo_label.setText("SGPT")
        app_logo_label.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        app_logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        title_layout = QHBoxLayout()
        title_layout.addWidget(app_logo_label)
        title_text = QLabel("SarkarGPT Pro")
        title_text.setObjectName("AppTitleText")
        title_text.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title_layout.addWidget(title_text)
        title_layout.addStretch()
        s_layout.addLayout(title_layout)

        network_selector = QHBoxLayout()
        network_label = QLabel("Select Network")
        network_label.setObjectName("NetworkLabel")
        network_selector.addWidget(network_label)
        network_selector.addStretch()
        s_layout.addLayout(network_selector)

        network_buttons_layout = QHBoxLayout()
        for i, icon_name in enumerate(["coin_eth", "coin_bnb", "coin_sol", "coin_avax"]):
            btn = QPushButton()
            btn.setObjectName(f"NetworkBtn_{i}")
            btn.setFixedSize(36,36)
            btn.setIcon(QIcon(get_icon_path(icon_name)))
            btn.setIconSize(QSize(24, 24))
            network_buttons_layout.addWidget(btn)
        network_buttons_layout.addStretch()
        s_layout.addLayout(network_buttons_layout)
        s_layout.addSpacing(10)


        self.nav_buttons = {}
        nav_items = [
            ("Dashboard","🏠"),
            ("Language Converter","🌍"),
            ("Invoicing","🧾"),
            ("Market Analyst", "💹"),
            ("Visual Creator","✨"),
            ("Publication Creator", "📖"),
            ("Corporate Helper", "💼"),
            ("Data Visualizer","📈"),
            ("Blueprints","🧩")
        ]
        
        for name, emoji in nav_items:
            btn = QPushButton(f"{emoji}    {name}")
            btn.setFixedHeight(40)
            s_layout.addWidget(btn)
            self.nav_buttons[name] = btn

        s_layout.addSpacing(20)
        s_layout.addStretch()

        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("font-size:9pt; color:gray; padding-left: 5px;")
        s_layout.addWidget(self.status_label)

        self.stack = QStackedWidget()
        self.stack.setContentsMargins(8, 8, 8, 8)

        self.page_chat = self._page_chat()
        self.page_trading = self._page_trading()
        self.page_business = self._page_business()
        self.page_book_maker = self._page_book_maker()
        self.page_translator = self._page_translator()
        self.page_image = self._page_image()
        self.page_image_to_graph = self._page_image_to_graph()
        self.page_billing = self._page_billing()
        self.page_templates = self._page_templates()
        self.page_settings = self._page_settings()

        self.stack.addWidget(self.page_chat)
        self.stack.addWidget(self.page_translator)
        self.stack.addWidget(self.page_billing)
        self.stack.addWidget(self.page_trading)
        self.stack.addWidget(self.page_image)
        self.stack.addWidget(self.page_book_maker)
        self.stack.addWidget(self.page_business)
        self.stack.addWidget(self.page_image_to_graph)
        self.stack.addWidget(self.page_templates)
        self.stack.addWidget(self.page_settings)

        self.nav_buttons["Dashboard"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_chat), self._update_nav_selection("Dashboard")))
        self.nav_buttons["Language Converter"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_translator), self._update_nav_selection("Language Converter")))
        self.nav_buttons["Invoicing"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_billing), self._update_nav_selection("Invoicing")))
        self.nav_buttons["Market Analyst"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_trading), self._update_nav_selection("Market Analyst")))
        self.nav_buttons["Visual Creator"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_image), self._update_nav_selection("Visual Creator")))
        self.nav_buttons["Publication Creator"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_book_maker), self._update_nav_selection("Publication Creator")))
        self.nav_buttons["Corporate Helper"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_business), self._update_nav_selection("Corporate Helper")))
        self.nav_buttons["Data Visualizer"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_image_to_graph), self._update_nav_selection("Data Visualizer")))
        self.nav_buttons["Blueprints"].clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_templates), self._update_nav_selection("Blueprints")))

        settings_btn = QPushButton("⚙️ Configuration")
        settings_btn.setFixedHeight(40)
        s_layout.addWidget(settings_btn)
        settings_btn.clicked.connect(lambda: (self.stack.setCurrentWidget(self.page_settings), self._update_nav_selection("Configuration")))
        self.nav_buttons["Configuration"] = settings_btn

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, 1)

        self._update_nav_selection("Dashboard")

    def _page_chat(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0,0,0,0)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.addWidget(QLabel("Chat / Dashboard"))
        header_layout.addStretch()
        header_layout.addWidget(self._create_floating_card("Model", "Multi-Model", "#1e88e5"))
        header_layout.addWidget(self._create_floating_card("Status", "Ready", "#00bcd4"))
        layout.addLayout(header_layout)
        layout.addSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setContentsMargins(8, 0, 8, 0)

        left_area = QWidget(); left_layout = QVBoxLayout(left_area); left_layout.setContentsMargins(0,0,0,0)

        mindset_group = QGroupBox("AI Mindset Customization")
        mindset_group.setObjectName("AImindsetGroup")
        mindset_layout = QFormLayout(mindset_group)

        self.ai_mindset_preset_combo = QComboBox()
        self.ai_mindset_preset_combo.addItems(["Neutral", "Creative", "Formal", "Technical", "Sarcastic", "Philosophical", "Humorous"])
        self.ai_mindset_preset_combo.setCurrentText(self.ai_mindset_preset)
        self.ai_mindset_preset_combo.currentTextChanged.connect(self._on_mindset_preset_changed)
        mindset_layout.addRow("Preset:", self.ai_mindset_preset_combo)

        self.ai_mindset_custom_input = QLineEdit()
        self.ai_mindset_custom_input.setPlaceholderText("e.g., Act like a pirate, Be a helpful coding assistant")
        self.ai_mindset_custom_input.setText(self.ai_mindset_custom)
        self.ai_mindset_custom_input.textChanged.connect(self._on_mindset_custom_changed)
        mindset_layout.addRow("Custom:", self.ai_mindset_custom_input)

        self.always_remember_checkbox = QCheckBox("Always Remember History")
        self.always_remember_checkbox.setChecked(self.remember_messages)
        self.always_remember_checkbox.toggled.connect(self._toggle_remember_default)
        mindset_layout.addRow(self.always_remember_checkbox)

        left_layout.addWidget(mindset_group)
        left_layout.addSpacing(10)

        self.chat_output = QTextEdit(); self.chat_output.setReadOnly(True)
        self.chat_output.setObjectName("ChatOutput")
        left_layout.addWidget(self.chat_output)

        self.thinking_label = QLabel("")
        self.thinking_label.setStyleSheet("font-style: italic; color: #e6b800; padding: 4px 10px;")
        self.thinking_label.hide()
        left_layout.addWidget(self.thinking_label)

        self.chat_input = QTextEdit(); self.chat_input.setFixedHeight(110)
        self.chat_input.setObjectName("ChatInput")
        self.chat_input.setPlaceholderText("Type your message here...")
        left_layout.addWidget(self.chat_input)

        self.chat_image_list = QListWidget()
        self.chat_image_list.setObjectName("ChatImageList")
        self.chat_image_list.setFixedHeight(60)
        self.chat_image_list.setFlow(QListWidget.Flow.LeftToRight)
        self.chat_image_list.hide()
        left_layout.addWidget(self.chat_image_list)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 4, 0, 0)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._send_chat)
        controls.addWidget(self.send_button)
        
        self.btn_attach_img = QPushButton("Attach (Max 20)")
        self.btn_attach_img.clicked.connect(self._attach_chat_images)
        controls.addWidget(self.btn_attach_img)

        self.btn_clear_img = QPushButton("Clear Images")
        self.btn_clear_img.clicked.connect(self._clear_chat_images)
        controls.addWidget(self.btn_clear_img)

        self.regen_button = QPushButton("Regenerate Last")
        self.regen_button.clicked.connect(self._regenerate_last)
        controls.addWidget(self.regen_button)
        self.clear_memory_button = QPushButton("Clear Memory")
        self.clear_memory_button.clicked.connect(self._clear_memory)
        controls.addWidget(self.clear_memory_button)
        controls.addStretch()
        left_layout.addLayout(controls)

        right_area = QWidget(); right_layout = QVBoxLayout(right_area); right_layout.setContentsMargins(0,0,0,0)

        model_selection_group = QGroupBox("Model Selection")
        model_selection_layout = QFormLayout(model_selection_group)
        
        self.model_combos = {}
        
        self.model_groups_new = {
            "OpenAI": [
                "OpenAI GPT-4o", "OpenAI GPT-4o-mini", "OpenAI GPT-4 Turbo", "OpenAI GPT-3.5 Turbo"
            ],
            "Gemini": [
                "Gemini 2.5 Pro", "Gemini 2.5 Flash", "Gemini 2.5 Flash Lite", "Gemini 2.0 Flash",
                "Gemini 1.5 Pro", "Gemini 1.5 Flash", "Gemini 1.0 Pro"
            ],
            "Anthropic": [
                "Claude Opus 4.1", "Claude Sonnet 4", "Claude Haiku 3.5",
                "Claude 3 Opus", "Claude 3 Sonnet", "Claude 3 Haiku"
            ],
            "Perplexity": [
                "Sonar Huge 128k (Online)", "Sonar Large 128k (Online)", "Sonar Small 128k (Online)",
                "Sonar Deep Research", "Sonar Reasoning Pro", "Sonar Reasoning", "Sonar Pro",
                "Sonar Large Chat", "Sonar Small Chat"
            ],
            "Grok": [
                "Grok 4", "Grok 3", "Grok 3 Mini"
            ],
            "Open Source (via PPLX)": [
                "Llama 3.1 405B", "Llama 3.1 70B", "Llama 3.1 8B",
                "Mixtral 8x7B Instruct", "Mistral 7B Instruct", "Code Llama 34B"
            ]
        }

        for group_name, models in self.model_groups_new.items():
            combo = QComboBox()
            combo.addItems(["--- Select Model ---"] + models)
            combo.setObjectName(f"ModelCombo_{group_name}")
            self.model_combos[group_name] = combo
            model_selection_layout.addRow(f"{group_name}:", combo)

        right_layout.addWidget(model_selection_group)
        right_layout.addSpacing(10)

        template_group = QGroupBox("Active Blueprints (multi-select)")
        template_layout = QVBoxLayout(template_group)
        self.template_quick_list = QListWidget()
        self.template_quick_list.setObjectName("TemplateQuickList")
        self.template_quick_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._refresh_templates_quick()
        template_layout.addWidget(self.template_quick_list)
        right_layout.addWidget(template_group)

        memory_group = QGroupBox("Conversation Memory (recent)")
        memory_layout = QVBoxLayout(memory_group)
        self.memory_list = QListWidget()
        self.memory_list.setObjectName("MemoryList")
        self._refresh_memory_list()
        memory_layout.addWidget(self.memory_list)
        self.load_memory_button = QPushButton("Load Selected into Input")
        self.load_memory_button.clicked.connect(self._load_selected_memory)
        memory_layout.addWidget(self.load_memory_button)
        right_layout.addWidget(memory_group)

        splitter.addWidget(right_area)
        splitter.addWidget(left_area)
        
        splitter.setSizes([300, 900])
        layout.addWidget(splitter)
        return w

    def _attach_chat_images(self):
        max_images = 20
        remaining_slots = max_images - len(self.chat_image_paths)
        if remaining_slots <= 0:
            QMessageBox.warning(self, "Image Limit", f"You have already attached the maximum of {max_images} images.")
            return

        paths, _ = QFileDialog.getOpenFileNames(self, "Open images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not paths:
            return

        added_count = 0
        for path in paths:
            if len(self.chat_image_paths) >= max_images:
                QMessageBox.warning(self, "Image Limit", f"Reached {max_images} image limit. Some images were not added.")
                break
            if path not in self.chat_image_paths:
                self.chat_image_paths.append(path)
                added_count += 1
        
        if added_count > 0:
            self._refresh_chat_image_list()

    def _clear_chat_images(self):
        self.chat_image_paths.clear()
        self._refresh_chat_image_list()

    def _refresh_chat_image_list(self):
        self.chat_image_list.clear()
        if not self.chat_image_paths:
            self.chat_image_list.hide()
            return
        
        for path in self.chat_image_paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            self.chat_image_list.addItem(item)
        
        self.chat_image_list.show()

    def _create_floating_card(self, title, value, color):
        card = QFrame()
        card.setFixedSize(160, 80)
        card.setObjectName("FloatingInfoCard")

        card.setStyleSheet(f"""
            QFrame#FloatingInfoCard {{
                padding: 8px;
            }}
            QFrame#FloatingInfoCard QLabel#CardTitle {{
                font-size: 9pt;
                color: #bbbbbb;
                min-height: 1.2em;
                background: transparent;
                border: none;
                box-shadow: none;
            }}
            QFrame#FloatingInfoCard QLabel#CardValue {{
                font-size: 14pt;
                font-weight: bold;
                color: {color};
                min-height: 1.2em;
                background: transparent;
                border: none;
                box-shadow: none;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        card_layout.addWidget(title_label)

        self.card_value_labels = {}
        value_label = QLabel(value)
        value_label.setObjectName("CardValue")
        card_layout.addWidget(value_label)
        self.card_value_labels[title] = value_label

        card_layout.addStretch()
        return card

    def _update_floating_card(self, title, value):
        if title in self.card_value_labels:
            self.card_value_labels[title].setText(value)

    def _on_mindset_preset_changed(self, text):
        self.prefs['ai_mindset_preset'] = text
        self.ai_mindset_preset = text
        save_json(PREF_FILE, self.prefs)

    def _on_mindset_custom_changed(self, text):
        self.prefs['ai_mindset_custom'] = text
        self.ai_mindset_custom = text
        save_json(PREF_FILE, self.prefs)

    def _page_business(self):
        w = QWidget()
        l = QVBoxLayout(w)
        h = QLabel("Professional Corporate Helper");
        h.setObjectName("PageTitle")
        h.setFont(QFont("Inter", 16, QFont.Weight.Bold)); l.addWidget(h)

        controls = QFormLayout()
        self.biz_combo_task = QComboBox()
        self.biz_combo_task.addItems([
            "Write Professional Email",
            "Summarize Text",
            "Draft Business Plan Section",
            "Marketing Slogan Ideas",
            "SWOT Analysis"
        ])
        controls.addRow("Select Task:", self.biz_combo_task)
        l.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.biz_text_in = QTextEdit()
        self.biz_text_in.setPlaceholderText("Enter your points, text to summarize, or topic...")
        splitter.addWidget(self.biz_text_in)

        self.biz_text_out = QTextEdit()
        self.biz_text_out.setReadOnly(True)
        self.biz_text_out.setPlaceholderText("Generated content will appear here...")
        splitter.addWidget(self.biz_text_out)

        l.addWidget(splitter, 1)

        self.biz_thinking = QLabel("Generating response...")
        self.biz_thinking.setStyleSheet("font-style: italic; color: #e6b800;")
        self.biz_thinking.hide()
        l.addWidget(self.biz_thinking)

        self.biz_btn_generate = QPushButton("Generate")
        self.biz_btn_generate.clicked.connect(self._generate_business_assist)
        l.addWidget(self.biz_btn_generate)

        return w


    def _page_trading(self):
        w = QWidget()
        main_layout = QHBoxLayout(w)
        main_layout.setContentsMargins(0, 0, 0, 0)

        left_frame = QFrame()
        left_frame.setObjectName("TradingSidebar")
        left_frame.setFixedWidth(240)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)

        search_group = QGroupBox("Stock Search")
        search_layout = QVBoxLayout(search_group)
        self.stock_search_input = QLineEdit()
        self.stock_search_input.setPlaceholderText("Enter stock ticker (e.g., AAPL)")
        search_layout.addWidget(self.stock_search_input)

        self.period_combo = QComboBox()
        self.period_combo.addItems(["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"])
        self.period_combo.setCurrentText("6mo")
        search_layout.addWidget(self.period_combo)

        self.stock_search_btn = QPushButton("Search")
        self.stock_search_btn.clicked.connect(self._search_stock)
        search_layout.addWidget(self.stock_search_btn)
        left_layout.addWidget(search_group)

        list_group = QGroupBox("Search History")
        list_layout = QVBoxLayout(list_group)
        self.stock_list = QListWidget()
        self.stock_list.setObjectName("StockList")
        self.stock_list.itemClicked.connect(self._on_stock_list_selected)
        list_layout.addWidget(self.stock_list)
        left_layout.addWidget(list_group, 1)

        main_layout.addWidget(left_frame)

        self.trading_tabs = QTabWidget()
        self.trading_tabs.setObjectName("TradingTabs")

        self.tab1_market = self._create_trading_tab1()

        self.trading_tabs.addTab(self.tab1_market, "📈 Market View")

        main_layout.addWidget(self.trading_tabs, 1)

        return w

    def _create_trading_tab1(self):
        w = QWidget()
        middle_layout = QVBoxLayout(w)
        middle_layout.setContentsMargins(12, 12, 12, 12)

        self.stock_graph_label = QLabel("Search for a stock to see its graph.")
        self.stock_graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stock_graph_label.setObjectName("VideoPlaceholder")
        self.stock_graph_label.setMinimumHeight(300)
        middle_layout.addWidget(self.stock_graph_label, 2)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        overview_group = QGroupBox("Factual Overview")
        overview_layout = QVBoxLayout(overview_group)
        self.stock_overview_display = QTextEdit()
        self.stock_overview_display.setReadOnly(True)
        self.stock_overview_display.setPlaceholderText("Factual company overview will appear here...")
        overview_layout.addWidget(self.stock_overview_display)
        splitter.addWidget(overview_group)

        analytics_group = QGroupBox("AI Analytics")
        analytics_layout = QVBoxLayout(analytics_group)
        self.stock_analytics_display = QTextEdit()
        self.stock_analytics_display.setReadOnly(True)
        self.stock_analytics_display.setPlaceholderText("AI analysis will appear here after search.")
        analytics_layout.addWidget(self.stock_analytics_display)
        splitter.addWidget(analytics_group)

        middle_layout.addWidget(splitter, 1)
        return w

    def _page_book_maker(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self._create_floating_card("Book Title", "My AI Book", "#1e88e5"))
        header_layout.addWidget(self._create_floating_card("Author", "SarkarGPT Pro", "#00bcd4"))
        self.book_chapter_count_card = self._create_floating_card("Chapters", "0", "#2ECC71")
        header_layout.addWidget(self.book_chapter_count_card)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        layout.addSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setObjectName("BookScrollArea")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)

        info_group = QGroupBox("Book Information")
        info_layout = QFormLayout(info_group)
        self.book_title_input = QLineEdit("My AI Book")
        self.book_title_input.textChanged.connect(lambda t: self._update_floating_card("Book Title", t or "..."))
        self.book_author_input = QLineEdit("SarkarGPT Pro")
        self.book_author_input.textChanged.connect(lambda t: self._update_floating_card("Author", t or "..."))
        info_layout.addRow("Title:", self.book_title_input)
        info_layout.addRow("Author:", self.book_author_input)
        scroll_layout.addWidget(info_group)

        content_group = QGroupBox("Book Content")
        content_layout = QFormLayout(content_group)
        self.book_preface_input = QTextEdit()
        self.book_preface_input.setPlaceholderText("Enter preface (optional)...")
        self.book_preface_input.setFixedHeight(100)
        self.book_intro_input = QTextEdit()
        self.book_intro_input.setPlaceholderText("Enter main introduction (optional)...")
        self.book_intro_input.setFixedHeight(150)
        self.book_conclusion_input = QTextEdit()
        self.book_conclusion_input.setPlaceholderText("Enter conclusion (optional)...")
        self.book_conclusion_input.setFixedHeight(150)
        content_layout.addRow("Preface:", self.book_preface_input)
        content_layout.addRow("Introduction:", self.book_intro_input)
        content_layout.addRow("Conclusion:", self.book_conclusion_input)
        scroll_layout.addWidget(content_group)

        chapter_group = QGroupBox("Chapters (Add in order)")
        chapter_layout = QVBoxLayout(chapter_group)
        self.book_chapter_list = QListWidget()
        self.book_chapter_list.setFixedHeight(150)
        chapter_layout.addWidget(self.book_chapter_list)

        chapter_add_layout = QHBoxLayout()
        self.book_chapter_input = QLineEdit()
        self.book_chapter_input.setPlaceholderText("Enter chapter title...")
        chapter_add_layout.addWidget(self.book_chapter_input)
        self.book_chapter_add_btn = QPushButton("Add")
        self.book_chapter_add_btn.clicked.connect(self._book_add_chapter)
        chapter_add_layout.addWidget(self.book_chapter_add_btn)
        chapter_layout.addLayout(chapter_add_layout)

        self.book_chapter_remove_btn = QPushButton("Remove Selected")
        self.book_chapter_remove_btn.clicked.connect(self._book_remove_chapter)
        chapter_layout.addWidget(self.book_chapter_remove_btn)
        scroll_layout.addWidget(chapter_group)

        ai_group = QGroupBox("AI Generation")
        ai_layout = QFormLayout(ai_group)
        self.book_difficulty_combo = QComboBox()
        self.book_difficulty_combo.addItems(["Childish (Simple)", "Beginner (Easy)", "Intermediate (Detailed)", "Advanced (Complex)", "Expert (Academic)"])
        self.book_difficulty_combo.setCurrentIndex(2)
        self.book_style_combo = QComboBox()
        self.book_style_combo.addItems(["Standard Textbook", "Modern Minimalist", "Classic Novel"])
        ai_layout.addRow("Difficulty:", self.book_difficulty_combo)
        ai_layout.addRow("Style:", self.book_style_combo)

        self.book_custom_instructions = QTextEdit()
        self.book_custom_instructions.setPlaceholderText("Enter any other custom instructions for the AI author (e.g., 'write in the first person', 'focus on practical examples')...")
        self.book_custom_instructions.setFixedHeight(100)
        ai_layout.addRow("Custom Instructions:", self.book_custom_instructions)

        scroll_layout.addWidget(ai_group)

        scroll_area.setWidget(scroll_content)
        controls_layout.addWidget(scroll_area)
        splitter.addWidget(controls_widget)

        editor_widget = QFrame()
        editor_layout = QVBoxLayout(editor_widget)

        editor_header = QHBoxLayout()
        editor_header.addWidget(QLabel("Generated Book Content (Editable)"))
        editor_header.addStretch()
        self.book_gen_status = QLabel("Ready")
        self.book_gen_status.setStyleSheet("color: #888;")
        editor_header.addWidget(self.book_gen_status)
        editor_layout.addLayout(editor_header)

        self.book_content_editor = QTextEdit()
        self.book_content_editor.setObjectName("BookContentEditor")
        self.book_content_editor.setPlaceholderText("Generated book content will appear here...")
        editor_layout.addWidget(self.book_content_editor)

        editor_actions = QHBoxLayout()
        self.book_generate_btn = QPushButton("Generate Book (AI)")
        self.book_generate_btn.clicked.connect(self._book_generate_ai)
        editor_actions.addWidget(self.book_generate_btn)
        self.book_save_pdf_btn = QPushButton("Save Book as PDF")
        self.book_save_pdf_btn.clicked.connect(self._save_book_pdf)
        editor_actions.addWidget(self.book_save_pdf_btn)
        editor_layout.addLayout(editor_actions)

        splitter.addWidget(editor_widget)

        layout.addWidget(splitter)
        return w

    def _page_translator(self):
        w = QWidget(); l = QVBoxLayout(w)
        title = QLabel("Language Converter");
        title.setObjectName("PageTitle")
        title.setFont(QFont("Inter", 16, QFont.Weight.Bold)); l.addWidget(title)
        grid = QGridLayout()
        grid.addWidget(QLabel("From:"), 0, 0)
        self.from_lang = QComboBox()
        langs = ["auto","english","hindi","french","german","spanish","chinese (simplified)","japanese","russian","bengali","arabic","portuguese","italian","korean"]
        self.from_lang.addItems(langs)
        grid.addWidget(self.from_lang, 0, 1)
        grid.addWidget(QLabel("To:"), 0, 2)
        self.to_lang = QComboBox()
        self.to_lang.addItems(langs[1:])
        self.to_lang.setCurrentText("english")
        grid.addWidget(self.to_lang, 0, 3)
        l.addLayout(grid)
        mid = QVBoxLayout()
        self.trans_in = QTextEdit(); self.trans_in.setObjectName("TranslatorInput")
        self.trans_in.setMinimumHeight(200)
        mid.addWidget(self.trans_in)
        self.trans_out = QTextEdit(); self.trans_out.setReadOnly(True); self.trans_out.setObjectName("TranslatorOutput")
        self.trans_out.setMinimumHeight(200)
        mid.addWidget(self.trans_out)
        l.addLayout(mid, 1)
        btns = QHBoxLayout()
        self.btn_translate = QPushButton("Translate"); self.btn_translate.clicked.connect(self._translate)
        btns.addWidget(self.btn_translate); btns.addStretch()
        l.addLayout(btns)
        return w

    def _page_image(self):
        w = QWidget(); l = QVBoxLayout(w)
        h = QLabel("Visual Creator (DALL-E 3 via OpenAI)");
        h.setObjectName("PageTitle")
        h.setFont(QFont("Inter", 16, QFont.Weight.Bold)); l.addWidget(h)

        top = QFormLayout()

        self.img_prompt = QTextEdit()
        self.img_prompt.setFixedHeight(80)
        top.addRow("Prompt:", self.img_prompt)

        self.img_style = QComboBox()
        self.img_style.addItems(["Photorealistic","Cinematic","Anime","Digital Art","Abstract"])
        top.addRow("Style:", self.img_style)

        self.btn_gen = QPushButton("Generate")
        self.btn_gen.clicked.connect(self._generate_image)
        top.addRow(self.btn_gen)

        l.addLayout(top)

        self.img_gen_thinking = QLabel("Generating...")
        self.img_gen_thinking.setStyleSheet("font-style: italic; color: #e6b800;")
        self.img_gen_thinking.hide()
        l.addWidget(self.img_gen_thinking)

        self.gallery = QListWidget()
        self.gallery.setIconSize(QSize(220,220))
        self.gallery.setFlow(QListWidget.Flow.LeftToRight)
        self.gallery.setWrapping(True);
        self.gallery.setObjectName("ImageGallery")
        l.addWidget(self.gallery, 1)
        self.gallery.itemClicked.connect(self._on_gallery_item_clicked)

        return w

    def _page_image_to_graph(self):
        w = QWidget(); l = QVBoxLayout(w)

        header_layout = QHBoxLayout()
        self.img2g_status_card = self._create_floating_card("Image Status", "No Image", "#E74C3C")
        header_layout.addWidget(self.img2g_status_card)
        self.img2g_analysis_card = self._create_floating_card("Analysis", "Ready", "#00bcd4")
        header_layout.addWidget(self.img2g_analysis_card)
        header_layout.addStretch()
        l.addLayout(header_layout)
        l.addSpacing(10)

        main_splitter = QSplitter(Qt.Orientation.Vertical)

        top = QFrame(); top_l = QVBoxLayout(top)
        self.img2g_btn_open = QPushButton("Open Image"); self.img2g_btn_open.clicked.connect(self._img2g_open); top_l.addWidget(self.img2g_btn_open)
        self.img2g_preview = QLabel("Open an image to analyze...")
        self.img2g_preview.setMinimumSize(400, 300)
        self.img2g_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img2g_preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.img2g_preview.setObjectName("ImageToGraphPreview")
        top_l.addWidget(self.img2g_preview, 1)
        main_splitter.addWidget(top)

        bottom = QFrame(); bottom_l = QVBoxLayout(bottom)
        self.img2g_btn_gen = QPushButton("Generate Equations"); self.img2g_btn_gen.clicked.connect(self._img2g_generate); bottom_l.addWidget(self.img2g_btn_gen)
        self.img2g_thinking = QLabel("Analyzing image...")
        self.img2g_thinking.setStyleSheet("font-style: italic; color: #e6b800;")
        self.img2g_thinking.hide()
        bottom_l.addWidget(self.img2g_thinking)
        self.img2g_output = QTextEdit()
        self.img2g_output.setReadOnly(True)
        self.img2g_output.setPlaceholderText("Generated mathematical equations will appear here...")
        self.img2g_output.setObjectName("ImageToGraphOutput")
        bottom_l.addWidget(self.img2g_output, 1)
        main_splitter.addWidget(bottom)

        l.addWidget(main_splitter)
        return w

    def _page_billing(self):
        w = QWidget(); l = QVBoxLayout(w)
        h = QLabel("Invoicing / Billing");
        h.setObjectName("PageTitle")
        h.setFont(QFont("Inter", 16, QFont.Weight.Bold)); l.addWidget(h)
        form = QFormLayout()
        self.bill_client = QLineEdit(); form.addRow("Client:", self.bill_client)
        self.bill_address = QTextEdit(); self.bill_address.setFixedHeight(80); form.addRow("Address:", self.bill_address)
        self.bill_tax = QSpinBox(); self.bill_tax.setRange(0,100); self.bill_tax.setValue(18); self.bill_tax.setSuffix(" %"); form.addRow("Tax:", self.bill_tax)
        l.addLayout(form)

        items_header = QHBoxLayout()
        items_header.addWidget(QLabel("Item Name"), 3); items_header.addWidget(QLabel("Rate"), 1); items_header.addWidget(QLabel("Qty"), 1); items_header.addWidget(QLabel(""), 1)
        l.addLayout(items_header)

        items_box = QHBoxLayout()
        self.item_name = QLineEdit(); self.item_rate = QLineEdit(); self.item_qty = QSpinBox(); self.item_qty.setValue(1); self.item_qty.setMinimum(1)
        items_box.addWidget(self.item_name, 3); items_box.addWidget(self.item_rate, 1); items_box.addWidget(self.item_qty, 1)
        self.btn_add_item = QPushButton("Add"); self.btn_add_item.clicked.connect(self._add_bill_item); items_box.addWidget(self.btn_add_item, 1)
        l.addLayout(items_box)
        self.bill_list = QListWidget(); self.bill_list.setObjectName("BillList")
        l.addWidget(self.bill_list)
        self.btn_gen_invoice = QPushButton("Generate PDF Invoice"); self.btn_gen_invoice.clicked.connect(self._generate_invoice); l.addWidget(self.btn_gen_invoice)
        self._bill_items = []
        return w

    def _page_templates(self):
        w = QWidget(); l = QVBoxLayout(w)
        h = QLabel("Blueprints Manager");
        h.setObjectName("PageTitle")
        h.setFont(QFont("Inter", 16, QFont.Weight.Bold)); l.addWidget(h)

        l.addWidget(QLabel("Tip: To group blueprints, use a prefix, e.g., 'Email - Sales' and 'Email - Support'."))

        mid = QHBoxLayout()
        self.template_list = QListWidget()
        self.template_list.setObjectName("TemplateList")
        self._refresh_template_list_safe()
        mid.addWidget(self.template_list, 2)
        right = QVBoxLayout()

        active_group = QGroupBox("Active Blueprint")
        active_layout = QVBoxLayout(active_group)
        self.active_template_display = QLineEdit()
        self.active_template_display.setReadOnly(True)
        active_layout.addWidget(self.active_template_display)
        right.addWidget(active_group)

        right.addWidget(QLabel("Blueprint Content Editor"))
        self.template_editor = QTextEdit();
        self.template_editor.setObjectName("TemplateEditor")
        right.addWidget(self.template_editor)
        row = QHBoxLayout()
        self.btn_new_template = QPushButton("New"); self.btn_new_template.clicked.connect(self._new_template); row.addWidget(self.btn_new_template)
        self.btn_save_template = QPushButton("Save"); self.btn_save_template.clicked.connect(self._save_template); row.addWidget(self.btn_save_template)
        self.btn_delete_template = QPushButton("Delete"); self.btn_delete_template.clicked.connect(self._delete_template); row.addWidget(self.btn_delete_template)
        self.btn_set_active_template = QPushButton("Set Active"); self.btn_set_active_template.clicked.connect(self._set_active_template); row.addWidget(self.btn_set_active_template)
        right.addLayout(row)
        mid.addLayout(right,3)
        l.addLayout(mid)
        self.template_list.itemSelectionChanged.connect(self._on_template_selected)
        self._update_active_template_display()
        return w

    def _page_settings(self):
        w = QWidget(); l = QVBoxLayout(w)
        h = QLabel("Configuration");
        h.setObjectName("PageTitle")
        h.setFont(QFont("Inter", 16, QFont.Weight.Bold)); l.addWidget(h)

        theme_group = QGroupBox("Theme (live preview)")
        t_layout = QHBoxLayout(theme_group)
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("ThemeSelectorCombo")
        self.theme_combo.addItems(list(THEME_SETS.keys())); self.theme_combo.setCurrentText(self.current_theme)
        self.theme_combo.currentTextChanged.connect(self._live_preview_theme)
        t_layout.addWidget(self.theme_combo)
        self.btn_apply_theme = QPushButton("Apply and Save"); self.btn_apply_theme.clicked.connect(self._apply_theme_confirm)
        t_layout.addWidget(self.btn_apply_theme)
        l.addWidget(theme_group)

        keys_group = QGroupBox("API Keys")
        g_layout = QFormLayout(keys_group)

        self.key_openai = QLineEdit(self._get_api_key("openai", use_default=False) or "");
        g_layout.addRow(QLabel("OpenAI (Paid API):"), self.key_openai)

        self.key_gemini = QLineEdit(self._get_api_key("gemini", use_default=False) or "");
        g_layout.addRow(QLabel("Gemini (Paid API):"), self.key_gemini)

        self.key_gemini_image = QLineEdit(self._get_api_key("gemini_image", use_default=False) or "");
        g_layout.addRow(QLabel("Gemini Image (Paid API):"), self.key_gemini_image)

        self.key_anthropic = QLineEdit(self._get_api_key("anthropic", use_default=False) or "");
        g_layout.addRow(QLabel("Anthropic (Paid API):"), self.key_anthropic)

        self.key_perplexity = QLineEdit(self._get_api_key("perplexity", use_default=False) or "");
        g_layout.addRow(QLabel("Perplexity (Paid API):"), self.key_perplexity)
        
        self.key_grok = QLineEdit(self._get_api_key("grok", use_default=False) or "");
        g_layout.addRow(QLabel("Grok (Paid API):"), self.key_grok)

        g_layout.addRow(QLabel("<i>Note: All APIs are generally paid. Some may offer a limited free tier for new users.</i>"))

        btn_save_keys = QPushButton("Save Keys"); btn_save_keys.clicked.connect(self._save_keys)
        g_layout.addRow(btn_save_keys)
        l.addWidget(keys_group)

        l.addStretch()
        return w

    def _refresh_template_list_safe(self):
        if hasattr(self, "template_list") and self.template_list is not None:
            self.template_list.clear()
            for name in self.templates.keys():
                self.template_list.addItem(name)

    def _refresh_templates_quick(self):
        items = list(self.templates.keys())
        if not items:
            items = ["No Template"]
            self.templates["No Template"] = ""
            save_json(TEMPLATES_FILE, self.templates)

        if hasattr(self, "template_quick_list") and self.template_quick_list is not None:
            self.template_quick_list.blockSignals(True)
            self.template_quick_list.clear()
            for item_text in items:
                item = QListWidgetItem(item_text)
                self.template_quick_list.addItem(item)

            active = self.prefs.get("active_template", "No Template")
            if active in items:
                for i in range(self.template_quick_list.count()):
                    if self.template_quick_list.item(i).text() == active:
                        self.template_quick_list.item(i).setSelected(True)
                        break

            self.template_quick_list.blockSignals(False)

        self._refresh_template_list_safe()

    def _update_active_template_display(self):
        if hasattr(self, 'active_template_display'):
            self.active_template_display.setText(self.prefs.get("active_template", "No Template"))

    def _new_template(self):
        name, ok = QInputDialog.getText(self, "Blueprint name", "Enter blueprint name:")
        if not ok or not name.strip(): return
        if name in self.templates:
            QMessageBox.warning(self, "Exists", "Blueprint with that name exists.")
            return
        self.templates[name] = ""
        save_json(TEMPLATES_FILE, self.templates)
        self._refresh_templates_quick()
        QMessageBox.information(self, "Created", f"Blueprint '{name}' created. Edit content on the right and Save.")

    def _save_template(self):
        sel = self.template_list.currentItem()
        if not sel:
            QMessageBox.warning(self, "Select", "Select blueprint to save.")
            return
        name = sel.text()
        content = self.template_editor.toPlainText()
        self.templates[name] = content
        save_json(TEMPLATES_FILE, self.templates)
        QMessageBox.information(self, "Saved", f"Blueprint '{name}' saved.")
        self._refresh_templates_quick()

    def _delete_template(self):
        sel = self.template_list.currentItem()
        if not sel:
            QMessageBox.warning(self, "Select", "Select blueprint to delete.")
            return
        name = sel.text()
        if name == "No Template":
            QMessageBox.warning(self, "Protected", "Cannot delete 'No Template'.")
            return
        ok = QMessageBox.question(self, "Confirm", f"Delete blueprint '{name}'? This cannot be undone.")
        if ok == QMessageBox.StandardButton.Yes:
            self.templates.pop(name, None)

            if self.prefs['active_template'] == name:
                self.prefs['active_template'] = 'No Template'
                save_json(PREF_FILE, self.prefs)

            save_json(TEMPLATES_FILE, self.templates)
            self._refresh_templates_quick()
            self.template_editor.clear()
            self._update_active_template_display()
            QMessageBox.information(self, "Deleted", f"Blueprint '{name}' deleted.")

    def _set_active_template(self):
        sel = self.template_list.currentItem()
        if not sel:
            QMessageBox.warning(self, "Select", "Select blueprint to set active.")
            return
        name = sel.text()
        self.prefs['active_template'] = name
        save_json(PREF_FILE, self.prefs)
        if hasattr(self, 'template_quick_list'):
            self.template_quick_list.blockSignals(True)
            for i in range(self.template_quick_list.count()):
                item = self.template_quick_list.item(i)
                item.setSelected(item.text() == name)
            self.template_quick_list.blockSignals(False)
        self._update_active_template_display()
        QMessageBox.information(self, "Active Blueprint", f"'{name}' set as active.")

    def _on_template_selected(self):
        sel = self.template_list.currentItem()
        if sel:
            name = sel.text()
            self.template_editor.setPlainText(self.templates.get(name, ""))

    def _get_api_key(self, name, use_default=True):
        saved_key = self.saved_keys.get(name, "")

        if use_default and not saved_key:
            if self.prefs.get("use_default_keys", True):
                return DEFAULT_KEYS.get(name, "")
            else:
                return ""

        if use_default and self.prefs.get("use_default_keys", True):
            return saved_key or DEFAULT_KEYS.get(name, "")
        else:
            return saved_key

    def _save_keys(self):
        data = {
            "openai": self.key_openai.text().strip(),
            "gemini": self.key_gemini.text().strip(),
            "gemini_image": self.key_gemini_image.text().strip(),
            "anthropic": self.key_anthropic.text().strip(),
            "perplexity": self.key_perplexity.text().strip(),
            "grok": self.key_grok.text().strip()
        }
        save_json(API_KEY_FILE, data)
        self.saved_keys = data
        QMessageBox.information(self, "Saved", "API keys saved locally.")

    def _toggle_remember_default(self, state):
        val = bool(state)
        self.remember_messages = val
        self.prefs['remember_messages'] = val
        save_json(PREF_FILE, self.prefs)

        if hasattr(self, 'always_remember_checkbox') and self.always_remember_checkbox.isChecked() != val:
            self.always_remember_checkbox.setChecked(val)

    def _live_preview_theme(self, name):
        self.apply_theme(name)

    def _apply_theme_confirm(self):
        name = self.theme_combo.currentText()
        self.prefs['theme'] = name
        save_json(PREF_FILE, self.prefs)
        self.current_theme = name
        self.current_theme_colors = THEME_SETS[name]
        QMessageBox.information(self, "Saved", f"Theme '{name}' saved.")

    def apply_theme(self, name):
        theme = THEME_SETS.get(name, THEME_SETS[DEFAULT_THEME_NAME])
        bg = theme["bg"]
        card_bg = theme["card_bg"]
        accent = theme["accent"]
        text = theme["text"]
        glass = theme["glass"]
        glow = theme["glow"]
        sidebar_bg = theme.get("sidebar_bg", card_bg)
        is_dark_theme = theme["is_dark"]

        if is_dark_theme:
            floating_border = "rgba(255, 255, 255, 0.2)"
            floating_shadow = "0 8px 25px rgba(0, 0, 0, 0.2)"
            text_on_card = text
        else:
            floating_border = "rgba(0, 0, 0, 0.15)"
            floating_shadow = "0 8px 25px rgba(0, 0, 0, 0.1)"
            text_on_card = "#222222"

        try:
            r, g, b = QColor(accent).red(), QColor(accent).green(), QColor(accent).blue()
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            accent_text = "#000000" if brightness > 128 else "#ffffff"
        except Exception:
            accent_text = "#ffffff"

        qss = f"""
        QMainWindow {{ background: {bg}; }}
        QWidget {{
            color: {text};
            font-family: Inter, Arial;
            font-size: 10pt;
        }}

        QFrame#Sidebar {{
            background: {sidebar_bg};
            border-radius: 14px;
            border: 1px solid {floating_border};
            box-shadow: {floating_shadow};
            padding-top: 10px;
        }}
        QLabel#AppTitleText {{
            color: {text};
            font: 700 16pt "Inter";
            background: transparent;
            padding-top: 0px;
            padding-left: 5px;
        }}
        QLabel#NetworkLabel {{
            font-size: 9pt;
            color: #aaaaaa;
            padding: 10px 0 5px 0;
            background: transparent;
        }}
        QPushButton[objectName^="NetworkBtn_"] {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            margin: 0 4px;
            padding: 4px;
        }}
        QPushButton[objectName^="NetworkBtn_"]:hover {{
            background: rgba(255,255,255,0.1);
        }}

        QFrame#Sidebar QPushButton {{
            background: transparent;
            border: none;
            border-radius: 12px;
            text-align: left;
            padding: 12px 16px;
            font-weight: 500;
            color: {text};
            font-size: 11pt;
            margin: 2px 0;
        }}
        QFrame#Sidebar QPushButton:hover {{
            background: {glass};
            color: {accent};
            box-shadow: none;
        }}
        QFrame#Sidebar QPushButton[active="true"] {{
            background: {accent};
            color: {accent_text};
            font-weight: 600;
        }}

        QLabel[objectName="PageTitle"] {{
            font: 700 16pt "Inter";
            color: {text};
            padding-bottom: 4px;
            background: transparent;
            margin: 8px;
        }}

        QFrame {{
            background: transparent;
            border-radius: 14px;
        }}
        QFrame#TradingSidebar {{
            background: {sidebar_bg};
            border-radius: 14px;
            border: 1px solid {floating_border};
            box-shadow: {floating_shadow};
            margin: 8px;
        }}
        QSplitter::handle {{
            background: {glass};
            border-radius: 3px;
        }}
        QSplitter::handle:horizontal {{ width: 6px; margin: 4px 0; }}
        QSplitter::handle:vertical {{ height: 6px; margin: 0 4px; }}

        QPushButton {{
            background: {card_bg};
            border: 1px solid {floating_border};
            padding: 10px 14px;
            border-radius: 12px;
            color: {text_on_card};
            font-weight: 600;
            box-shadow: {floating_shadow};
            margin: 2px;
        }}
        QPushButton:hover {{
            box-shadow: 0 0 16px {glow};
            border-color: {accent};
        }}
        QPushButton:focus {{
            outline: none;
            border: 1px solid {accent};
            box-shadow: 0 0 20px {glow};
        }}

        QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget, QTableWidget,
        QLabel#ImageToGraphPreview, QGroupBox, QFrame#FloatingInfoCard {{
            background: {card_bg};
            padding: 10px;
            border-radius: 14px;
            color: {text_on_card};
            border: 1px solid {floating_border};
            box-shadow: {floating_shadow};
            margin: 4px;
        }}

        QListWidget#ChatImageList {{
            padding: 5px;
        }}
        QListWidget#ChatImageList::item {{
            padding: 4px 8px;
            border-radius: 6px;
            color: {text_on_card};
            background-color: {glass};
            margin-right: 5px;
        }}

        QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QListWidget:focus, QTextEdit:focus, QTableWidget:focus {{
            color: {text_on_card};
            border: 1px solid {accent};
            box-shadow: 0 0 20px {glow};
        }}

        QListWidget::item {{
            padding: 8px 10px;
            border-radius: 8px;
            color: {text_on_card};
            background-color: transparent;
        }}
        QListWidget::item:hover {{ background: {glass}; }}
        QListWidget::item:selected {{
            background: {accent};
            color: {accent_text};
        }}

        QComboBox::drop-down {{
            border: none;
            margin-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background: {card_bg};
            border: 1px solid {floating_border};
            color: {text_on_card};
            selection-background-color: {accent};
            selection-color: {accent_text};
            outline: none;
            padding: 4px;
            border-radius: 10px;
            box-shadow: 0 4px 10px {floating_shadow};
        }}
        QComboBox QAbstractItemView::item {{
            padding: 8px 12px;
            border-radius: 8px;
            color: {text_on_card};
            background-color: transparent;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {accent};
            color: {accent_text};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {glass};
            color: {text_on_card};
        }}
        QComboBox QAbstractItemView::item:selected:hover {{
            background-color: {accent};
            color: {accent_text};
        }}

        QGroupBox {{
            margin-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            margin-left: 10px;
            color: {text_on_card};
            font-weight: bold;
            background-color: transparent;
        }}

        QScrollBar:vertical {{
            background: {glass};
            border-radius: 6px;
            width: 12px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {accent};
            border-radius: 6px;
            min-height: 25px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            background: none; border: none; height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            background: {glass};
            border-radius: 6px;
            height: 12px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {accent};
            border-radius: 6px;
            min-width: 25px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            background: none; border: none; width: 0;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        QMessageBox {{
            background-color: {bg};
        }}
        QMessageBox QLabel {{
            color: {text};
            font-size: 11pt;
            padding: 10px;
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            background-color: {card_bg};
            color: {text_on_card};
            border: 1px solid {floating_border};
            border-radius: 12px;
            padding: 8px 16px;
            min-width: 80px;
            box-shadow: {floating_shadow};
        }}
        QMessageBox QPushButton:hover {{
            border-color: {accent};
            box-shadow: 0 0 12px {glow};
        }}

        QCheckBox, QRadioButton {{
            color: {text};
            background-color: transparent;
            spacing: 5px;
            margin: 4px;
        }}
        QGroupBox QCheckBox, QGroupBox QRadioButton, QFrame#FloatingInfoCard QCheckBox {{
            color: {text_on_card};
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}
        QRadioButton::indicator::unchecked {{
            border: 2px solid {floating_border};
            border-radius: 8px;
            background-color: {card_bg};
        }}
        QRadioButton::indicator::checked {{
            border: 2px solid {accent};
            border-radius: 8px;
            background-color: {accent};
        }}
        QCheckBox::indicator::unchecked {{
            border: 2px solid {floating_border};
            border-radius: 4px;
            background-color: {card_bg};
        }}
        QCheckBox::indicator::checked {{
            border: 2px solid {accent};
            border-radius: 4px;
            background-color: {accent};
            image: none;
        }}

        QSlider::groove:horizontal {{
            border: 1px solid {floating_border};
            height: 8px;
            background: {glass};
            margin: 2px 0;
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {accent};
            border: 1px solid {accent};
            width: 16px;
            margin: -4px 0;
            border-radius: 8px;
        }}

        QTabWidget#TradingTabs::pane {{
            border: none;
            background-color: transparent;
            padding: 0;
            margin: 0;
        }}
        QTabWidget#TradingTabs QWidget {{
            background-color: transparent;
        }}
        QTabBar::tab {{
            background: {glass};
            color: {text_on_card};
            padding: 12px 18px;
            font-weight: bold;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            border: 1px solid {floating_border};
            border-bottom: none;
            margin-right: 4px;
            margin-top: 8px;
        }}
        QTabBar::tab:selected {{
            background: {card_bg};
            color: {accent};
            border-bottom: 1px solid {card_bg};
        }}
        QTabBar::tab:!selected {{
            color: #aaaaaa;
            background: {glass};
            margin-top: 10px;
        }}

        QLabel#VideoPlaceholder {{
            background-color: {card_bg};
            color: #777777;
            border: 2px dashed {floating_border};
            border-radius: 14px;
            font-size: 16px;
            box-shadow: {floating_shadow};
        }}

        QScrollArea#BookScrollArea {{
            background-color: transparent;
            border: none;
            box-shadow: none;
        }}
        QScrollArea#BookScrollArea > QWidget > QWidget {{
            background-color: transparent;
        }}

        QTableWidget {{
            gridline-color: {glass};
            background-color: {card_bg};
            color: {text_on_card};
            border: 1px solid {floating_border};
        }}
        QHeaderView::section {{
            background-color: {glass};
            color: {text_on_card};
            padding: 6px;
            border: 1px solid {floating_border};
            font-weight: bold;
        }}
        QTableWidget::item {{
            padding: 6px;
            color: {text_on_card};
        }}
        QTableWidget::item:selected {{
            background-color: {accent};
            color: {accent_text};
        }}
        """

        self.current_theme_colors = theme
        self.setStyleSheet(qss)
        self.current_theme = name


    def _send_chat(self):
        if self.streaming_timer and self.streaming_timer.isActive():
            self.streaming_timer.stop()
            if hasattr(self, "streaming_cursor"):
                self.streaming_cursor.insertHtml("<br></p><br>")

        text = self.chat_input.toPlainText().strip()
        if not text and not self.chat_image_paths:
            QMessageBox.warning(self, "Input Required", "Please type a message or attach images.")
            return

        self.model_queue = []
        for group_name, combo in self.model_combos.items():
            model_name = combo.currentText()
            if model_name != "--- Select Model ---":
                self.model_queue.append(model_name)

        if not self.model_queue:
            QMessageBox.warning(self, "Model Required", "Please select at least one model.")
            return

        selected_templates_content = []
        if hasattr(self, "template_quick_list"):
            for i in range(self.template_quick_list.count()):
                item = self.template_quick_list.item(i)
                if item.isSelected() and item.text() != "No Template":
                    template_content = self.templates.get(item.text(), "")
                    if template_content:
                        selected_templates_content.append(template_content)

        self.template_text = "\n\n".join(selected_templates_content)
        self.display_prompt = text
        self.full_prompt = text
        if self.template_text:
            self.full_prompt += f"\n\n--- INSTRUCTIONS FROM BLUEPRINTS ---\n{self.template_text}"
        
        if not self.full_prompt and self.chat_image_paths:
            self.full_prompt = "Analyze these images."
            self.display_prompt = "(Image analysis)"

        self.current_chat_images = list(self.chat_image_paths)
        self.chat_image_paths.clear()
        self._refresh_chat_image_list()

        self.send_button.setEnabled(False)
        self.chat_input.setEnabled(False)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        user_color = self.current_theme_colors.get("user_text", "#e0e0e0")
        escaped_text = self.display_prompt.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        
        image_notification = ""
        if self.current_chat_images:
            image_notification = f"<br><i>(Attached {len(self.current_chat_images)} image(s))</i>"

        self.chat_output.insertHtml(f"<br><p style='color:{user_color};'><b>You ({ts}):</b><br>{escaped_text}{image_notification}</p><br>")
        self.chat_output.verticalScrollBar().setValue(self.chat_output.verticalScrollBar().maximum())

        self.chat_input.clear()
        self._set_thinking(True, self.thinking_label, f"Starting queue... {len(self.model_queue)} model(s).")
        self._run_next_model_from_queue()

    def _run_next_model_from_queue(self):
        if not self.model_queue:
            self._set_thinking(False, self.thinking_label)
            self.send_button.setEnabled(True)
            self.chat_input.setEnabled(True)
            self.current_chat_images = []
            return

        model = self.model_queue.pop(0)
        self._set_thinking(True, self.thinking_label, f"Querying {model}...")

        messages = []
        image_paths = self.current_chat_images

        mindset_instruction = ""
        preset = self.ai_mindset_preset_combo.currentText()
        custom = self.ai_mindset_custom_input.text().strip()

        if custom:
            mindset_instruction = custom
        elif preset != "Neutral":
            mindset_instruction = f"Your persona for this response must be: {preset}."

        mindset_instruction += "\n\n[System Note: Please respond in English unless otherwise specified in the prompt.]"

        messages.append({"role": "system", "content": mindset_instruction})

        history_limit = 10
        if self.always_remember_checkbox.isChecked():
            relevant_history = [e for e in self.chat_memory if e.get("type") == "model_reply"]
            relevant_history = relevant_history[-(history_limit):]
            
            user_prompts = {e["timestamp"]: e for e in self.chat_memory if e.get("type") == "user_prompt"}
            
            for entry in relevant_history:
                prompt_to_use = entry.get("full_prompt", entry.get("prompt"))
                messages.append({"role": "user", "content": prompt_to_use})
                messages.append({"role": "model", "content": entry["response"]})
        
        messages.append({"role": "user", "content": self.full_prompt})

        remember = self.always_remember_checkbox.isChecked()

        if remember:
            self._save_memory_entry(
                type="user_prompt",
                model_list=self.model_queue, 
                display_prompt=self.display_prompt, 
                full_prompt=self.full_prompt,
                image_paths=image_paths
            )

        threading.Thread(target=self._call_model_api, args=(model, messages, self.display_prompt, self.full_prompt, remember, image_paths), daemon=True).start()


    def _call_model_api(self, model, messages, display_prompt, full_prompt, remember, image_paths):
        try:
            text = ""
            model_id = ""
            api_to_use = ""

            if model == "OpenAI GPT-4o": model_id = "gpt-4o"; api_to_use = "openai"
            elif model == "OpenAI GPT-4o-mini": model_id = "gpt-4o-mini"; api_to_use = "openai"
            elif model == "OpenAI GPT-4 Turbo": model_id = "gpt-4-turbo-preview"; api_to_use = "openai"
            elif model == "OpenAI GPT-3.5 Turbo": model_id = "gpt-3.5-turbo"; api_to_use = "openai"

            elif model == "Gemini 2.5 Pro": model_id = "gemini-2.5-pro-preview-09-2025"; api_to_use = "gemini"
            elif model == "Gemini 2.5 Flash": model_id = "gemini-2.5-flash-preview-09-2025"; api_to_use = "gemini"
            elif model == "Gemini 2.5 Flash Lite": model_id = "gemini-2.5-flash-lite-preview-09-2025"; api_to_use = "gemini"
            elif model == "Gemini 2.0 Flash": model_id = "gemini-2.0-flash-preview-09-2025"; api_to_use = "gemini"
            elif model == "Gemini 1.5 Pro": model_id = "gemini-1.5-pro-latest"; api_to_use = "gemini"
            elif model == "Gemini 1.5 Flash": model_id = "gemini-1.5-flash-latest"; api_to_use = "gemini"
            elif model == "Gemini 1.0 Pro": model_id = "gemini-1.0-pro"; api_to_use = "gemini"

            elif model == "Claude Opus 4.1": model_id = "claude-3-opus-20240229"; api_to_use = "anthropic"
            elif model == "Claude Sonnet 4": model_id = "claude-3-sonnet-20240229"; api_to_use = "anthropic"
            elif model == "Claude Haiku 3.5": model_id = "claude-3-haiku-20240307"; api_to_use = "anthropic"
            elif model == "Claude 3 Opus": model_id = "claude-3-opus-20240229"; api_to_use = "anthropic"
            elif model == "Claude 3 Sonnet": model_id = "claude-3-sonnet-20240229"; api_to_use = "anthropic"
            elif model == "Claude 3 Haiku": model_id = "claude-3-haiku-20240307"; api_to_use = "anthropic"

            elif model == "Sonar Huge 128k (Online)": model_id = "llama-3.1-sonar-huge-128k-online"; api_to_use = "perplexity"
            elif model == "Sonar Large 128k (Online)": model_id = "llama-3.1-sonar-large-128k-online"; api_to_use = "perplexity"
            elif model == "Sonar Small 128k (Online)": model_id = "llama-3.1-sonar-small-128k-online"; api_to_use = "perplexity"
            elif model == "Sonar Deep Research": model_id = "sonar-deep-research"; api_to_use = "perplexity"
            elif model == "Sonar Reasoning Pro": model_id = "sonar-reasoning-pro"; api_to_use = "perplexity"
            elif model == "Sonar Reasoning": model_id = "sonar-reasoning"; api_to_use = "perplexity"
            elif model == "Sonar Pro": model_id = "sonar-pro"; api_to_use = "perplexity"
            elif model == "Sonar Large Chat": model_id = "llama-3.1-sonar-large-128k-chat"; api_to_use = "perplexity"
            elif model == "Sonar Small Chat": model_id = "llama-3.1-sonar-small-128k-chat"; api_to_use = "perplexity"

            elif model == "Llama 3.1 405B": model_id = "llama-3.1-405b-instruct"; api_to_use = "perplexity"
            elif model == "Llama 3.1 70B": model_id = "llama-3.1-70b-instruct"; api_to_use = "perplexity"
            elif model == "Llama 3.1 8B": model_id = "llama-3.1-8b-instruct"; api_to_use = "perplexity"
            elif model == "Mixtral 8x7B Instruct": model_id = "mixtral-8x7b-instruct"; api_to_use = "perplexity"
            elif model == "Mistral 7B Instruct": model_id = "mistral-7b-instruct"; api_to_use = "perplexity"
            elif model == "Code Llama 34B": model_id = "codellama-34b-instruct"; api_to_use = "perplexity"
            
            elif model == "Grok 4": model_id = "grok-4"; api_to_use = "grok"
            elif model == "Grok 3": model_id = "grok-3"; api_to_use = "grok"
            elif model == "Grok 3 Mini": model_id = "grok-3-mini"; api_to_use = "grok"
            
            else:
                text = f"[{model} mock reply] Echo: {display_prompt[:400]}"
                api_to_use = "mock"


            openai_messages = []
            for msg in messages:
                role = msg["role"]
                if role == "model":
                    role = "assistant"
                openai_messages.append({"role": role, "content": msg["content"]})
            
            if (api_to_use == "openai") and image_paths:
                last_msg_content = openai_messages[-1]["content"]
                if isinstance(last_msg_content, str):
                    new_content_parts = [{"type": "text", "text": last_msg_content}]
                    for img_path in image_paths:
                        try:
                            pil_img = Image.open(img_path)
                            buf = io.BytesIO()
                            pil_img.convert("RGB").save(buf, format="JPEG")
                            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
                            new_content_parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_data}"}})
                        except Exception as e:
                            print(f"Could not process image {img_path} for OpenAI: {e}")
                    openai_messages[-1]["content"] = new_content_parts

            gemini_contents = []
            system_instruction = None
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = {"parts": [{"text": msg["content"]}]}
                    continue
                gemini_contents.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [{"text": msg["content"]}]
                })

            if (api_to_use == "gemini") and image_paths:
                user_parts = gemini_contents[-1]["parts"]
                for img_path in image_paths:
                    try:
                        pil_img = Image.open(img_path)
                        buf = io.BytesIO()
                        pil_img.convert("RGB").save(buf, format="JPEG")
                        b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
                        user_parts.append({"inlineData": {"mimeType": "image/jpeg", "data": b64_data}})
                    except Exception as e:
                        print(f"Could not process image {img_path} for Gemini: {e}")

            claude_messages = []
            claude_system_prompt = None
            for msg in messages:
                if msg["role"] == "system":
                    claude_system_prompt = msg["content"]
                    continue
                claude_messages.append({
                    "role": "user" if msg["role"] == "user" else "assistant",
                    "content": msg["content"]
                })

            if api_to_use == "openai":
                key = self._get_api_key("openai")
                if not key or "your-default" in key:
                    text = "[OpenAI key missing. Please set it in Configuration.]"
                else:
                    try:
                        client = OpenAI(api_key=key)
                        resp = client.chat.completions.create(model=model_id, messages=openai_messages)
                        text = getattr(resp.choices[0].message, "content", None) or str(resp)
                    except Exception as e:
                        text = f"[OpenAI call error: {e}]"

            elif api_to_use == "gemini":
                key = self._get_api_key("gemini")
                if not key or "your-default" in key:
                    text = "[Gemini key missing. Please set it in Configuration.]"
                else:
                    try:
                        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}"
                        payload = {"contents": gemini_contents}
                        if system_instruction:
                            payload["systemInstruction"] = system_instruction

                        headers = {"Content-Type": "application/json"}
                        resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
                        if resp.status_code != 200:
                            raise Exception(f"API Error {resp.status_code}: {resp.text}")
                        result = resp.json()
                        text = result["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception as e:
                        text = f"[Gemini call error: {e}]"

            elif api_to_use == "anthropic":
                key = self._get_api_key("anthropic")
                if not key or "your-default" in key:
                    text = "[Anthropic key missing. Please set it in Configuration.]"
                else:
                    try:
                        api_url = "https://api.anthropic.com/v1/messages"
                        payload = {
                            "model": model_id,
                            "max_tokens": 4096,
                            "messages": claude_messages
                        }
                        if claude_system_prompt:
                            payload["system"] = claude_system_prompt

                        headers = {
                            "x-api-key": key,
                            "content-type": "application/json",
                            "anthropic-version": "2023-06-01"
                        }
                        resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
                        if resp.status_code != 200:
                            raise Exception(f"API Error {resp.status_code}: {resp.text}")
                        result = resp.json()
                        text = result["content"][0]["text"]
                    except Exception as e:
                        text = f"[Claude call error: {e}]"

            elif api_to_use == "perplexity":
                key = self._get_api_key("perplexity")
                if not key or "your-default" in key:
                    text = "[Perplexity key missing. Please set it in Configuration.]"
                else:
                    try:
                        api_url = "https://api.perplexity.ai/chat/completions"
                        payload = {
                            "model": model_id,
                            "messages": openai_messages
                        }
                        headers = {
                            "Authorization": f"Bearer {key}",
                            "content-type": "application/json"
                        }
                        resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
                        if resp.status_code != 200:
                            raise Exception(f"API Error {resp.status_code}: {resp.text}")
                        result = resp.json()
                        text = result["choices"][0]["message"]["content"]
                    except Exception as e:
                        text = f"[Perplexity call error: {e}]"

            elif api_to_use == "grok":
                key = self._get_api_key("grok")
                if not key or "your-default" in key:
                    text = "[Grok key missing. Please set it in Configuration.]"
                else:
                    try:
                        client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
                        resp = client.chat.completions.create(model=model_id, messages=openai_messages)
                        text = getattr(resp.choices[0].message, "content", None) or str(resp)
                    except Exception as e:
                        text = f"[Grok call error: {e}]"

            elif api_to_use == "mock":
                pass

            if remember:
                self._save_memory_entry(
                    type="model_reply",
                    model=model,
                    display_prompt=display_prompt,
                    full_prompt=full_prompt,
                    response=text
                )

            signals.chat_reply.emit(model, text)
        except Exception as e:
            signals.chat_reply.emit(model, f"[API error: {e}]\n{traceback.format_exc()}")

    def _get_color_for_model(self, model_name):
        try:
            hash_val = sum(ord(c) for c in model_name)
            base_color_name = self.current_theme_colors.get("ai_text", "#00bcd4")
            base_color = QColor(base_color_name)
            
            if base_color.saturation() < 20:
                colors = ["#00bcd4", "#8e78ff", "#ff78c0", "#30e0a0", "#ffc107", "#00e5ff"]
                return colors[hash_val % len(colors)]

            hue = (base_color.hue() + (hash_val % 10) * 30) % 360
            sat = min(255, base_color.saturation() + 20)
            val = max(150, base_color.value())
            new_color = QColor.fromHsv(hue, sat, val)
            return new_color.name()
        except Exception:
            return self.current_theme_colors.get("ai_text", "#00bcd4")

    def _on_chat_reply(self, model_name, text):
        self._set_thinking(False, self.thinking_label)

        self.streaming_words = text.split()
        if not self.streaming_words:
            self._run_next_model_from_queue()
            return

        ai_color = self._get_color_for_model(model_name)
        self.chat_output.insertHtml(f"<p style='color:{ai_color};'><b>{model_name}:</b><br>")
        self.streaming_cursor = self.chat_output.textCursor()

        self.streaming_timer = QTimer(self)
        self.streaming_timer.setInterval(35)
        self.streaming_timer.timeout.connect(self._stream_word)
        self.streaming_timer.start()

    def _stream_word(self):
        if not hasattr(self, "streaming_words") or not self.streaming_words:
            if self.streaming_timer:
                self.streaming_timer.stop()
            if hasattr(self, "streaming_cursor") and self.streaming_cursor:
                self.streaming_cursor.insertHtml("<br></p><br>")
                self.chat_output.verticalScrollBar().setValue(self.chat_output.verticalScrollBar().maximum())
            self._run_next_model_from_queue()
            return

        try:
            word = self.streaming_words.pop(0)
            escaped_word = word.replace('<', '&lt;').replace('>', '&gt;')
            self.streaming_cursor.insertText(escaped_word + " ")
            self.chat_output.verticalScrollBar().setValue(self.chat_output.verticalScrollBar().maximum())
        except Exception:
            if self.streaming_timer:
                self.streaming_timer.stop()

    def _save_memory_entry(self, **kwargs):
        entry = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        entry.update(kwargs)
        
        self.chat_memory.append(entry)
        while len(self.chat_memory) > 500:
            self.chat_memory.pop(0)
        save_json(CHAT_MEMORY_FILE, self.chat_memory)

        self._refresh_memory_list()

    def _refresh_memory_list(self):
        if hasattr(self, "memory_list"):
            self.memory_list.clear()
            
            relevant_history = self.chat_memory[-100:] 
            
            for e in relevant_history: 
                entry_type = e.get("type", "unknown")
                timestamp = e.get("timestamp", "")
                
                if entry_type == "user_prompt":
                    prompt_to_show = e.get("display_prompt", e.get("prompt", ""))[:60].replace("\n", " ")
                    text = f"[USER] {prompt_to_show}..."
                    it = QListWidgetItem(f"{timestamp} — {text}")
                    it.setData(Qt.ItemDataRole.UserRole, (timestamp, "user_prompt"))
                    self.memory_list.addItem(it)
                
                elif entry_type == "model_reply":
                    model = e.get("model", "AI")
                    response_to_show = e.get("response", "")[:60].replace("\n", " ")
                    text = f"[{model}] {response_to_show}..."
                    it = QListWidgetItem(f"{timestamp} — {text}")
                    it.setData(Qt.ItemDataRole.UserRole, (timestamp, "model_reply"))
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsSelectable) 
                    self.memory_list.addItem(it)

    def _regenerate_last(self):
        if not self.always_remember_checkbox.isChecked():
            QMessageBox.warning(self, "Memory Off", "Cannot regenerate when 'Always Remember History' is off.")
            return

        user_prompts = [e for e in self.chat_memory if e.get("type") == "user_prompt"]
        if not user_prompts:
            QMessageBox.information(self, "No memory", "No previous message to regenerate.")
            return

        last_prompt_entry = user_prompts[-1]
        
        self.display_prompt = last_prompt_entry.get("display_prompt")
        self.full_prompt = last_prompt_entry.get("full_prompt")
        image_paths_for_regen = last_prompt_entry.get("image_paths", [])
        
        self.model_queue = []
        for group_name, combo in self.model_combos.items():
            model_name = combo.currentText()
            if model_name != "--- Select Model ---":
                self.model_queue.append(model_name)

        if not self.model_queue:
            QMessageBox.warning(self, "Model Required", "Please select at least one model to run the regeneration.")
            return
        
        self.current_chat_images = image_paths_for_regen
        self.chat_image_paths = list(image_paths_for_regen)
        self._refresh_chat_image_list()
            
        self._set_thinking(True, self.thinking_label)
        self.send_button.setEnabled(False)
        self.chat_input.setEnabled(False)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_color = self.current_theme_colors.get("user_text", "#e0e0e0")
        escaped_text = self.display_prompt.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        
        image_notification = ""
        if self.current_chat_images:
            image_notification = f"<br><i>(Attached {len(self.current_chat_images)} image(s))</i>"

        self.chat_output.insertHtml(f"<br><p style='color:{user_color};'><b>You (Regen) ({ts}):</b><br>{escaped_text}{image_notification}</p><br>")
        self.chat_output.verticalScrollBar().setValue(self.chat_output.verticalScrollBar().maximum())

        self._set_thinking(True, self.thinking_label, f"Starting queue... {len(self.model_queue)} model(s).")
        self._run_next_model_from_queue()


    def _clear_memory(self):
        ok = QMessageBox.question(self, "Confirm", "Clear all saved conversation memory?")
        if ok == QMessageBox.StandardButton.Yes:
            self.chat_memory = []
            save_json(CHAT_MEMORY_FILE, self.chat_memory)
            self._refresh_memory_list()
            self.chat_output.clear()
            self.current_chat_images = []
            self.chat_image_paths.clear()
            self._refresh_chat_image_list()
            QMessageBox.information(self, "Cleared", "Chat memory cleared.")

    def _load_selected_memory(self):
        selected_items = self.memory_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Select", "Select a USER prompt entry first.")
            return

        data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        if not isinstance(data, tuple) or len(data) != 2:
            QMessageBox.warning(self, "Error", "Old memory format. Please clear memory.")
            return

        timestamp, entry_type = data

        if entry_type != "user_prompt":
             QMessageBox.warning(self, "Select", "Please select a USER prompt to load.")
             return
        
        found_entry = None
        for entry in reversed(self.chat_memory):
            if entry.get("type") == "user_prompt" and entry["timestamp"] == timestamp:
                found_entry = entry
                break

        if found_entry:
            prompt_to_load = found_entry.get("display_prompt", "")
            self.chat_input.setPlainText(prompt_to_load)
            
            image_paths_to_load = found_entry.get("image_paths", [])
            self.chat_image_paths = list(image_paths_to_load)
            self._refresh_chat_image_list()
        else:
            QMessageBox.warning(self, "Error", "Could not find selected memory entry.")

    def _set_thinking(self, thinking, label, base_text=None):
        if thinking:
            self._start_thinking_animation(label, base_text)
        else:
            self._stop_thinking_animation(label)

    def _start_thinking_animation(self, label, base_text=None):
        self._thinking_state = 0
        if not hasattr(self, "thinking_timer"):
            self.thinking_timer = QTimer()
            self.thinking_timer.setInterval(400)
            self.thinking_timer.timeout.connect(self._update_thinking_text)

        self._animated_label = label
        
        if base_text:
            self._base_thinking_text = base_text
        elif label == self.thinking_label: self._base_thinking_text = "🤔 SarkarGPT Pro is thinking"
        elif label == self.biz_thinking: self._base_thinking_text = "Generating response..."
        else: self._base_thinking_text = "Processing..."

        self.thinking_timer.start()
        label.setText(self._base_thinking_text)
        label.show()

    def _update_thinking_text(self):
        dots = "." * (self._thinking_state % 4)
        if hasattr(self, '_animated_label') and self._animated_label:
            self._animated_label.setText(f"{self._base_thinking_text}{dots}")

        self._thinking_state += 1

    def _stop_thinking_animation(self, label):
        if hasattr(self, "thinking_timer") and self.thinking_timer.isActive():
            self.thinking_timer.stop()
        if label:
            label.setText("")
            label.hide()
        if hasattr(self, '_animated_label'):
            self._animated_label = None
        if hasattr(self, '_base_thinking_text'):
            self._base_thinking_text = None

    def _translate(self):
        txt = self.trans_in.toPlainText().strip()
        if not txt:
            QMessageBox.warning(self, "Input", "Please type text to translate.")
            return
        src = self.from_lang.currentText()
        dest = self.to_lang.currentText()
        src_code = "auto" if src.lower()=="auto" else self._lang_to_code(src)
        dest_code = self._lang_to_code(dest)
        self.trans_out.setPlainText("Translating...")
        threading.Thread(target=self._translate_thread, args=(txt, src_code, dest_code), daemon=True).start()

    def _translate_thread(self, text, src, dest):
        try:
            t = GoogleTranslator(source=src, target=dest).translate(text)
            signals.translate_done.emit(t)
        except Exception as e:
            signals.translate_done.emit(f"[Translate error: {e}]")

    def _on_translate_done(self, text):
        self.trans_out.setPlainText(text)

    def _lang_to_code(self, name):
        mapping = {
            "english":"en","hindi":"hi","french":"fr","german":"de","spanish":"es",
            "chinese (simplified)":"zh-CN","japanese":"ja","russian":"ru","bengali":"bn",
            "arabic":"ar","portuguese":"pt","italian":"it","korean":"ko","auto":"auto"
        }
        return mapping.get(name.lower(), "en")

    def _generate_image(self):
        prompt = self.img_prompt.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Prompt required", "Please enter a prompt.")
            return

        style = self.img_style.currentText()
        final_prompt = f"A {style.lower()} of: {prompt}"

        self.btn_gen.setEnabled(False); self.btn_gen.setText("Generating...")
        self._set_thinking(True, self.img_gen_thinking)
        threading.Thread(target=self._generate_image_thread_openai, args=(final_prompt,), daemon=True).start()

    def _generate_image_thread_openai(self, prompt):
        try:
            key = self._get_api_key("openai")
            if not key or "your-default" in key:
                raise Exception("OpenAI API key is missing. Please set it in Configuration.")

            client = OpenAI(api_key=key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url
            img_data = requests.get(image_url).content
            img = Image.open(io.BytesIO(img_data))

            qim = ImageQt.ImageQt(img.convert("RGBA"))
            pix = QPixmap.fromImage(qim)

            signals.image_gen_done.emit(pix)

        except Exception as e:
            signals.image_gen_done.emit(("error", str(e)))

    def _on_generate_image_done(self, payload):
        self.btn_gen.setEnabled(True); self.btn_gen.setText("Generate")
        self._set_thinking(False, self.img_gen_thinking)

        if isinstance(payload, tuple) and payload[0] == "error":
            QMessageBox.critical(self, "Image Generation Error", payload[1])
            return

        if isinstance(payload, QPixmap):
            prompt = self.img_prompt.toPlainText().strip()[:60]
            item = QListWidgetItem(prompt)
            icon_pix = payload.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            item.setIcon(QIcon(icon_pix))
            item.setData(Qt.ItemDataRole.UserRole, payload)
            self.gallery.addItem(item)
        else:
            QMessageBox.critical(self, "Error", "Received unknown data from generation thread.")

    def _on_gallery_item_clicked(self, item):
        pixmap = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(pixmap, QPixmap):
            return

        ret = QMessageBox.question(self, "Save Image", "Do you want to save this image?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if ret == QMessageBox.StandardButton.Yes:
            path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Image (*.png)")
            if path:
                if not pixmap.save(path, "PNG"):
                    QMessageBox.critical(self, "Save Error", "Failed to save image.")
                else:
                    QMessageBox.information(self, "Saved", f"Image saved to {path}")

    def _img2g_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path: return
        try:
            pil = Image.open(path).convert("RGBA")
            self.img2g_pil_image = pil
            pix = pil_to_qpixmap(pil, maxsize=(self.img2g_preview.width(), self.img2g_preview.height()))
            self.img2g_preview.setPixmap(pix)
            self.img2g_output.clear()
            self._update_floating_card("Image Status", "Loaded")
            self._update_floating_card("Analysis", "Ready")
        except Exception as e:
            QMessageBox.critical(self, "Open Error", str(e))
            self.img2g_pil_image = None
            self._update_floating_card("Image Status", "Error")

    def _img2g_generate(self):
        if self.img2g_pil_image is None:
            QMessageBox.warning(self, "No Image", "Please open an image first.")
            return

        key = self._get_api_key("gemini")
        if not key or "your-default" in key:
            QMessageBox.warning(self, "API Key Missing", "Gemini API key is missing. Please set it in Configuration.")
            return

        self._set_thinking(True, self.img2g_thinking)
        self.img2g_btn_gen.setEnabled(False)
        self.img2g_btn_open.setEnabled(False)
        self._update_floating_card("Analysis", "Running...")

        try:
            buf = io.BytesIO()
            self.img2g_pil_image.convert("RGB").save(buf, format="JPEG")
            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Image Error", f"Failed to process image: {e}")
            self._set_thinking(False, self.img2g_thinking)
            self.img2g_btn_gen.setEnabled(True)
            self.img2g_btn_open.setEnabled(True)
            self._update_floating_card("Analysis", "Error")
            return

        threading.Thread(target=self._image_to_graph_thread, args=(key, b64_data), daemon=True).start()

    def _image_to_graph_thread(self, key, b64_image):
        try:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={key}"

            prompt_text = """
            Analyze this image and provide a set of mathematical equations (such as parametric equations,
            polar coordinates, or Cartesian functions) that could be used to draw the main subject of this image on a graph.
            Focus on the core outline and shape. Provide only the equations, formatted clearly and ready for use.
            *** IMPORTANT: Respond only in English. ***
            """

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt_text},
                            {"inlineData": {"mimeType": "image/jpeg", "data": b64_image}}
                        ]
                    }
                ]
            }

            resp = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=90)

            if resp.status_code != 200:
                raise Exception(f"API Error {resp.status_code}: {resp.text}")

            result = resp.json()

            if not result.get("candidates"):
                raise Exception(f"Invalid API response: {resp.text}")

            text = result["candidates"][0]["content"]["parts"][0]["text"]
            signals.image_to_graph_done.emit(text)

        except Exception as e:
            signals.image_to_graph_done.emit(f"[ERROR] {e}")

    def _on_image_to_graph_done(self, text):
        self._set_thinking(False, self.img2g_thinking)
        self.img2g_btn_gen.setEnabled(True)
        self.img2g_btn_open.setEnabled(True)

        if text.startswith("[ERROR]"):
            QMessageBox.critical(self, "Analysis Error", text)
            self.img2g_output.setPlainText("")
            self._update_floating_card("Analysis", "Error")
        else:
            self.img2g_output.setPlainText(text)
            self._update_floating_card("Analysis", "Complete")

    def _add_bill_item(self):
        name = self.item_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Item", "Enter item name."); return
        try:
            rate = float(self.item_rate.text().strip())
        except Exception:
            QMessageBox.warning(self, "Rate", "Enter numeric rate."); return
        qty = int(self.item_qty.value())
        total = rate * qty
        self._bill_items.append({"name":name,"rate":rate,"qty":qty,"total":total})
        self._refresh_bill_list()
        self.item_name.clear(); self.item_rate.clear(); self.item_qty.setValue(1)

    def _refresh_bill_list(self):
        self.bill_list.clear()
        for it in self._bill_items:
            line = f"{it['name']}  —  {it['qty']} x {english_number(it['rate'])} = {english_number(it['total'])}"
            self.bill_list.addItem(line)

    def _generate_invoice(self):
        if SimpleDocTemplate is None:
            QMessageBox.critical(self, "Error", "ReportLab library not found. Cannot generate PDF.")
            return

        client = self.bill_client.text().strip()
        if not client:
            QMessageBox.warning(self, "Client", "Enter client name."); return
        if not self._bill_items:
            QMessageBox.warning(self, "Items", "Add items first."); return
        path, _ = QFileDialog.getSaveFileName(self, "Save Invoice", f"Invoice_{client}.pdf", "PDF Files (*.pdf)")
        if not path: return
        try:
            doc = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            story.append(Paragraph("SarkarGPT Pro Services", styles['Title']))
            story.append(Paragraph("Invoice", styles['Heading2']))
            story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", ParagraphStyle(name='right', parent=styles['Normal'], alignment=TA_RIGHT)))
            story.append(Spacer(1,0.2*inch))
            story.append(Paragraph(f"Bill To: {client}", styles['Normal']))
            story.append(Paragraph(self.bill_address.toPlainText().replace("\n","<br/>"), styles['Normal']))
            story.append(Spacer(1,0.2*inch))
            data = [["Item Description","Rate","Qty","Total"]]
            subtotal = 0.0
            for it in self._bill_items:
                data.append([it['name'], english_number(it['rate']), str(it['qty']), english_number(it['total'])])
                subtotal += it['total']
            tax_pct = float(self.bill_tax.value())
            tax_amt = subtotal * tax_pct / 100.0
            grand = subtotal + tax_amt
            data.append(["","","Subtotal", english_number(subtotal)])
            data.append(["","","Tax ("+str(int(tax_pct))+"%)", english_number(tax_amt)])
            data.append(["","","Total", english_number(grand)])
            table = Table(data, colWidths=[3*inch,1*inch,0.6*inch,1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0), colors.HexColor("#2C3E50")),
                ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
                ('GRID',(0,0),(-1,-1),0.5,colors.gray),
                ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor("#E0E5EC")),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#CADBEB")),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
            ]))
            story.append(table); story.append(Spacer(1,0.5*inch))
            story.append(Paragraph("Thank you for your business!", ParagraphStyle(name='center', parent=styles['Normal'], alignment=TA_CENTER)))
            doc.build(story)
            QMessageBox.information(self, "Saved", f"Invoice saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", str(e))

    def _book_add_chapter(self):
        title = self.book_chapter_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Input Error", "Please enter a chapter title.")
            return

        item = QListWidgetItem(title)
        self.book_chapter_list.addItem(item)
        self.book_chapters.append(title)
        self.book_chapter_input.clear()
        self._update_floating_card("Chapters", str(self.book_chapter_list.count()))

    def _book_remove_chapter(self):
        selected_items = self.book_chapter_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selection Error", "Please select a chapter to remove.")
            return

        for item in selected_items:
            row = self.book_chapter_list.row(item)
            self.book_chapter_list.takeItem(row)
            try:
                self.book_chapters.remove(item.text())
            except ValueError:
                pass
        self._update_floating_card("Chapters", str(self.book_chapter_list.count()))

    def _book_generate_ai(self):
        if OpenAI is None:
            QMessageBox.critical(self, "Error", "OpenAI library not found. Cannot generate book.")
            return

        key = self._get_api_key("openai")
        if not key or "your-default" in key:
            QMessageBox.warning(self, "API Key Missing", "OpenAI key is missing. Please set it in Configuration.")
            return

        self.book_gen_status.setText("Generating...")
        self.book_generate_btn.setEnabled(False)
        self.book_save_pdf_btn.setEnabled(False)

        book_data = {
            "title": self.book_title_input.text(),
            "author": self.book_author_input.text(),
            "preface": self.book_preface_input.toPlainText(),
            "intro": self.book_intro_input.toPlainText(),
            "chapters": [self.book_chapter_list.item(i).text() for i in range(self.book_chapter_list.count())],
            "conclusion": self.book_conclusion_input.toPlainText(),
            "difficulty": self.book_difficulty_combo.currentText(),
            "style": self.book_style_combo.currentText(),
            "custom_instructions": self.book_custom_instructions.toPlainText().strip()
        }

        threading.Thread(target=self._call_book_api, args=(key, book_data), daemon=True).start()

    def _call_book_api(self, key, data):
        try:
            if OpenAI is None:
                raise ImportError("OpenAI library is not installed or failed to import. Please run: pip install openai")

            client = OpenAI(api_key=key)

            prompt = f"""
            You are a professional author. Your task is to write a complete book based on the following specifications.
            The response MUST be in Markdown format, with '#' for the title, '##' for chapter headings, and '###' for sub-sections.
            Use '---' on its own line to indicate a new page break.

            *** IMPORTANT: The entire book must be written in English. ***

            SPECIFICATIONS:
            - Book Title: {data['title']}
            - Author: {data['author']}
            - Difficulty Level: {data['difficulty']}
            - Writing Style: {data['style']}
            """

            if data['custom_instructions']:
                prompt += f"\n- Custom Instructions: {data['custom_instructions']}\n"

            prompt += f"""
            STRUCTURE:
            1.  **Title Page**: Generate a professional title page with Title and Author.
            2.  **Preface**: Write a preface. If user provided one, use it as a base: "{data['preface']}"
            3.  **Introduction**: Write the introduction. If user provided one, use it as a base: "{data['intro']}"
            4.  **Chapters**: Write content for the following chapters.
                {chr(10).join([f"    - Chapter {i+1}: {title}" for i, title in enumerate(data['chapters'])])}
            5.  **Conclusion**: Write the conclusion. If user provided one, use it as a base: "{data['conclusion']}"

            INSTRUCTIONS:
            - Write comprehensive, high-quality content for each section.
            - Ensure the tone matches the requested difficulty, style, and custom instructions.
            - Format the entire output as a single, continuous Markdown document.
            - Use page breaks '---' appropriately (e.g., before each new chapter).

            BEGIN BOOK:
            # {data['title']}
            *By {data['author']}*

            ---
            ## Preface
            """

            if data['preface']:
                prompt += f"{data['preface']}\n\n"
            else:
                prompt += "Write a compelling preface for this book...\n\n"

            prompt += "---\n## Introduction\n"

            if data['intro']:
                prompt += f"{data['intro']}\n\n"
            else:
                prompt += "Write a detailed introduction for this book, outlining its purpose and scope...\n\n"

            if not data['chapters']:
                prompt += "No chapters were provided. Please generate 3-5 relevant chapters based on the title.\n\n"
            else:
                for i, title in enumerate(data['chapters']):
                    prompt += f"---\n## Chapter {i+1}: {title}\n"
                    prompt += f"Write the full content for this chapter, keeping in mind the book's difficulty ('{data['difficulty']}'), style ('{data['style']}'), and custom instructions. Use sub-sections (###) if needed.\n\n"

            prompt += "---\n## Conclusion\n"
            if data['conclusion']:
                prompt += f"{data['conclusion']}\n\n"
            else:
                prompt += "Write a strong concluding chapter, summarizing the key takeaways and looking to the future...\n\n"

            prompt += "---"

            resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
            text = getattr(resp.choices[0].message, "content", None) or str(resp)

            signals.book_gen_done.emit(text)

        except Exception as e:
            signals.book_gen_done.emit(f"[BOOK GENERATION ERROR: {e}]")

    def _on_book_gen_done(self, text):
        self.book_content_editor.setMarkdown(text)
        self.book_gen_status.setText("Generation Complete")
        self.book_generate_btn.setEnabled(True)
        self.book_save_pdf_btn.setEnabled(True)

    def _save_book_pdf(self):
        if SimpleDocTemplate is None:
            QMessageBox.critical(self, "Error", "ReportLab library not found. Cannot save PDF.")
            return

        text = self.book_content_editor.toPlainText()
        if not text:
            QMessageBox.warning(self, "Error", "No content to save.")
            return

        title = self.book_title_input.text()
        path, _ = QFileDialog.getSaveFileName(self, "Save Book as PDF", f"{title}.pdf", "PDF Files (*.pdf)")
        if not path:
            return

        try:
            doc = SimpleDocTemplate(path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
            story = []

            title_style = ParagraphStyle(name='TitleStyle', fontSize=32, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold', textColor=colors.HexColor("#1A2642"))
            author_style = ParagraphStyle(name='AuthorStyle', fontSize=16, alignment=TA_CENTER, spaceAfter=40, fontName='Helvetica-Oblique', textColor=colors.HexColor("#555555"))
            h1_style = ParagraphStyle(name='H1', fontSize=20, fontName='Helvetica-Bold', spaceBefore=20, spaceAfter=10, textColor=colors.HexColor("#1F1F32"), borderPadding=4, borderBottomWidth=1, borderBottomColor=colors.HexColor("#1F1F32"))
            h2_style = ParagraphStyle(name='H2', fontSize=16, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#20314e"))
            h3_style = ParagraphStyle(name='H3', fontSize=14, fontName='Helvetica-Bold', spaceBefore=5, textColor=colors.HexColor("#2C3E50"))
            body_style = ParagraphStyle(name='Body', fontSize=10, alignment=TA_JUSTIFY, spaceAfter=5, leading=14, fontName='Helvetica')

            lines = text.split('\n')

            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    story.append(Spacer(1, 0.2*cm))
                    continue

                if line_stripped.startswith("# "):
                    story.append(Paragraph(line_stripped[2:], title_style))
                elif line_stripped.startswith("## "):
                    story.append(Paragraph(line_stripped[3:], h1_style))
                elif line_stripped.startswith("### "):
                    story.append(Paragraph(line_stripped[4:], h2_style))
                elif line_stripped.startswith("#### "):
                    story.append(Paragraph(line_stripped[5:], h3_style))
                elif line_stripped.startswith("---"):
                    story.append(PageBreak())
                elif line_stripped.startswith("*By "):
                    story.append(Paragraph(line_stripped, author_style))
                else:
                    story.append(Paragraph(line, body_style))

            doc.build(story, onFirstPage=self._add_page_numbers, onLaterPages=self._add_page_numbers)
            QMessageBox.information(self, "Success", f"Book saved successfully to {path}")

        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Failed to generate PDF: {e}\n{traceback.format_exc()}")

    def _add_page_numbers(self, canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        if page_num > 1:
            canvas.setFont('Helvetica', 9)
            canvas.drawRightString(doc.width + doc.leftMargin, 1.5 * cm, f"Page {page_num - 1}")
        canvas.restoreState()


    def _on_stock_list_selected(self, item):
        ticker = item.text()
        self.stock_search_input.setText(ticker)
        self._search_stock()

    def _search_stock(self):
        ticker = self.stock_search_input.text().strip().upper()
        if not ticker:
            QMessageBox.warning(self, "Input Error", "Please enter a stock ticker.")
            return

        if OpenAI is None:
            QMessageBox.critical(self, "Error", "OpenAI library not found. Cannot analyze stock.")
            return

        key = self._get_api_key("openai")
        if not key or "your-default" in key:
            QMessageBox.warning(self, "API Key Missing", "OpenAI key is missing. Please set it in Configuration.")
            return

        self.current_stock_ticker = ticker

        self.stock_overview_display.setPlainText(f"Searching for {ticker} overview...")
        self.stock_analytics_display.setPlainText("Requesting AI analysis...")
        self.stock_graph_label.setText(f"Loading graph for {ticker}...")

        self.trading_tabs.setCurrentWidget(self.tab1_market)

        existing_items = [self.stock_list.item(i).text() for i in range(self.stock_list.count())]
        if ticker not in existing_items:
            self.stock_list.addItem(ticker)

        period = self.period_combo.currentText()

        threading.Thread(target=self._call_stock_overview_api, args=(key, ticker), daemon=True).start()
        threading.Thread(target=self._call_stock_analytics_api, args=(key, ticker), daemon=True).start()
        threading.Thread(target=self._load_stock_graph, args=(ticker, period), daemon=True).start()

    def _call_stock_overview_api(self, key, ticker):
        try:
            client = OpenAI(api_key=key)
            safe_prompt = f"""
            Provide a brief, factual overview of the company with the stock ticker '{ticker}'.
            What are its main products or services and a brief, neutral history?

            IMPORTANT: Do not provide any financial analysis, price targets, stock predictions, investment advice, or any opinion on whether to buy, sell, or hold the stock.
            Only provide factual, public-domain information.
            """
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": safe_prompt}]
            )
            text = getattr(resp.choices[0].message, "content", None) or str(resp)
            signals.stock_overview_done.emit(text)
        except Exception as e:
            signals.stock_overview_done.emit(f"[STOCK OVERVIEW ERROR: {e}]")

    def _call_stock_analytics_api(self, key, ticker):
        try:
            client = OpenAI(api_key=key)
            analytics_prompt = f"""
            Please rate the share '{ticker}' for buying and selling based on recent public sentiment and news analysis.

            IMPORTANT: Do not provide any financial advice, price targets, or direct recommendations to buy or sell.
            Your response will be prefixed with a disclaimer.
            Simply provide a neutral analysis of the sentiment (e.g., "Positive", "Negative", "Neutral") and summarize the key news driving this sentiment.
            """
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": analytics_prompt}]
            )
            text = getattr(resp.choices[0].message, "content", None) or str(resp)
            signals.stock_analytics_done.emit(text)
        except Exception as e:
            signals.stock_analytics_done.emit(f"[STOCK ANALYTICS ERROR: {e}]")

    def _load_stock_graph(self, ticker, period="6mo"):
        try:
            theme = self.current_theme_colors
            is_dark = theme.get("is_dark", True)
            bg = theme.get("card_bg", "#2a2a3e")
            if "gradient" in bg:
                bg = theme.get("card_bg").split("stop:1 ")[-1].strip(")") if is_dark else "#ffffff"
            text_color = theme.get("text", "#e0e0e0") if is_dark else theme.get("text", "#222222")
            up_color = theme.get("accent", "#2ECC71")
            down_color = "#E74C3C"

            mc = mpf.make_marketcolors(up=up_color, down=down_color,
                                       wick={'up':up_color, 'down':down_color},
                                       volume={'up':up_color, 'down':down_color},
                                       edge="inherit")

            mpf_style = mpf.make_mpf_style(base_mpf_style='nightclouds' if is_dark else 'default',
                                           marketcolors=mc,
                                           facecolor=bg,
                                           edgecolor=text_color,
                                           figcolor=bg,
                                           gridcolor=theme.get("glass", "#444444"),
                                           gridstyle="--",
                                           y_on_right=True,
                                           rc={'axes.labelcolor': text_color,
                                               'xtick.color': text_color,
                                               'ytick.color': text_color,
                                               'text.color': text_color,
                                               'figure.facecolor': bg,
                                               'axes.facecolor': bg})

            data = yf.download(ticker, period=period, interval="1d", auto_adjust=True)
            if data.empty:
                raise Exception(f"No data found for ticker {ticker} (period: {period})")

            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce')

            data = data.dropna()

            if data.empty:
                raise Exception(f"No valid numeric data after cleaning for {ticker}")

            buf = io.BytesIO()
            mpf.plot(data,
                     type='candle',
                     style=mpf_style,
                     title=f"\n{ticker} - {period} Chart",
                     volume=True,
                     panel_ratios=(3, 1),
                     figsize=(10, 6),
                     savefig=buf,
                     tight_layout=True)
            buf.seek(0)
            img = Image.open(buf)
            pix = pil_to_qpixmap(img)
            signals.stock_graph_done.emit(pix)
            buf.close()
        except Exception as e:
            print(f"Graph generation failed: {e}. Falling back to placeholder.")
            try:
                bg_color = self.current_theme_colors.get("card_bg", "#ffffff").lstrip("#")
                if "gradient" in bg_color: bg_color = "2a2a3e"
                text_color = self.current_theme_colors.get("text", "#000000").lstrip("#")
                url = f"https://placehold.co/600x400/{bg_color}/{text_color}?text=Error+Loading+Graph+for+{ticker}\n(e.g.,+invalid+ticker)"
                img_data = requests.get(url).content
                img = Image.open(io.BytesIO(img_data))
                pix = pil_to_qpixmap(img)
                signals.stock_graph_done.emit(pix)
            except Exception as e2:
                signals.stock_graph_done.emit(("error", str(e2)))

    def _on_stock_overview_done(self, text):
        if text.startswith("[STOCK OVERVIEW ERROR"):
            self.stock_overview_display.setPlainText(text)
        else:
            self.stock_overview_display.setPlainText(text)

    def _on_stock_analytics_done(self, text):
        disclaimer = "DISCLAIMER: AI analysis is for informational purposes only and is not financial advice. Do not trade based on this information. Consult a qualified human financial advisor.\n\n"

        if text.startswith("[STOCK ANALYTICS ERROR"):
            self.stock_analytics_display.setPlainText(disclaimer + text)
        else:
            self.stock_analytics_display.setPlainText(disclaimer + text)

    def _on_stock_graph_done(self, payload):
        if isinstance(payload, tuple) and payload[0] == "error":
            self.stock_graph_label.setText(f"Could not load graph: {payload[1]}")
        elif isinstance(payload, QPixmap):
            self.stock_graph_label.setPixmap(payload.scaled(self.stock_graph_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _generate_business_assist(self):
        key = self._get_api_key("openai")
        if not key or "your-default" in key:
            QMessageBox.warning(self, "API Key Missing", "OpenAI key is missing. Please set it in Configuration.")
            return

        task = self.biz_combo_task.currentText()
        user_input = self.biz_text_in.toPlainText().strip()
        if not user_input:
            QMessageBox.warning(self, "Input Error", "Please enter your text or topic.")
            return

        system_prompts = {
            "Write Professional Email": "You are a business assistant. Write a clear, concise, and professional email based on the following points. Include a subject line.",
            "Summarize Text": "You are a business analyst. Summarize the following text into key bullet points, focusing on the most important actions or conclusions.",
            "Draft Business Plan Section": "You are a business consultant. Draft a professional business plan section (e.g., 'Executive Summary', 'Marketing Strategy') for the following topic.",
            "Marketing Slogan Ideas": "You are a creative director. Generate 10 catchy marketing slogans for the following product or company.",
            "SWOT Analysis": "You are a business strategist. Provide a brief SWOT analysis (Strengths, Weaknesses, Opportunities, Threats) for the following company or idea."
        }

        system_prompt = system_prompts.get(task, "You are a helpful business assistant.")

        self._set_thinking(True, self.biz_thinking)
        self.biz_btn_generate.setEnabled(False)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        threading.Thread(target=self._call_business_api, args=(key, messages), daemon=True).start()

    def _call_business_api(self, key, messages):
        try:
            client = OpenAI(api_key=key)
            resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            text = getattr(resp.choices[0].message, "content", None) or str(resp)
            signals.business_assist_done.emit(text)
        except Exception as e:
            signals.business_assist_done.emit(f"[Business Assist Error: {e}]")

    def _on_business_assist_done(self, text):
        self.biz_text_out.setPlainText(text)
        self._set_thinking(False, self.biz_thinking)
        self.biz_btn_generate.setEnabled(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'img2g_preview') and self.img2g_pil_image:
             pix = pil_to_qpixmap(self.img2g_pil_image, maxsize=(self.img2g_preview.width(), self.img2g_preview.height()))
             self.img2g_preview.setPixmap(pix)
        if hasattr(self, 'stock_graph_label') and self.stock_graph_label.pixmap():
             self.stock_graph_label.setPixmap(self.stock_graph_label.pixmap().scaled(self.stock_graph_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


    def closeEvent(self, event):
        if self.streaming_timer and self.streaming_timer.isActive():
            self.streaming_timer.stop()

        event.accept()


class Runnable(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self, fn):
        super().__init__(Runnable.EVENT_TYPE)
        self.fn = fn
    def execute(self):
        try:
            self.fn()
        except Exception as e:
            pass

class CustomApplication(QApplication):
    def eventFilter(self, obj, event):
        if isinstance(event, Runnable):
            event.execute()
            return True
        return super().eventFilter(obj, event)


def main():
    app = CustomApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Inter", 10))
    app.installEventFilter(app)

    win = SarkarGPTPro()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

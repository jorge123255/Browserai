# ui.py
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QTextEdit, QPushButton, QLabel, QApplication, QSplitter,
                           QScrollArea, QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QPainterPath
from typing import List

# Dark theme colors with more vibrant accents
COLORS = {
    'bg': '#0f1117',  # Darker background
    'bg_light': '#1e2028',  # Slightly lighter panels
    'bg_input': '#2a2d37',  # Input background
    'primary': '#3b82f6',  # Bright blue
    'primary_hover': '#60a5fa',
    'secondary': '#10b981',  # Success green
    'accent': '#8b5cf6',  # Purple accent
    'text': '#f3f4f6',
    'text_secondary': '#9ca3af',
    'border': '#2e3039',
    'error': '#ef4444',
    'shadow': '#000000',
    'success_bg': '#065f46',
    'warning_bg': '#92400e',
    'info_bg': '#1e40af'
}

EXAMPLE_PROMPTS = [
    {
        "title": "🔍 Basic Google Search",
        "prompt": "Go to google.com, wait for the page to load completely, then search for 'best restaurants in San Francisco'"
    },
    {
        "title": "📝 Fill Contact Form",
        "prompt": "Fill out this contact form with:\n- Name: John Smith\n- Email: john@example.com\n- Message: Hello, I'd like to make a reservation"
    },
    {
        "title": "🛍️ Amazon Navigation",
        "prompt": "Go to amazon.com, click on the 'Today's Deals' link, and then filter by 'Electronics'"
    },
    {
        "title": "🍽️ Restaurant Booking",
        "prompt": "Go to OpenTable, search for Italian restaurants in New York, filter for 4+ stars, and find one with availability this Saturday at 7 PM"
    },
    {
        "title": "🍣 Restaurant Info",
        "prompt": "Go to yelp.com, find the top-rated sushi restaurant in Chicago, and tell me their hours and phone number"
    }
]

class RoundedWidget(QWidget):
    """Base widget with rounded corners and shadow"""
    def __init__(self, parent=None, radius=8, shadow=True):
        super().__init__(parent)
        self.radius = radius
        if shadow:
            self.shadow = QGraphicsDropShadowEffect(self)
            self.shadow.setBlurRadius(20)
            self.shadow.setColor(QColor(COLORS['shadow']))
            self.shadow.setOffset(0, 2)
            self.setGraphicsEffect(self.shadow)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.radius, self.radius)
        
        painter.fillPath(path, QColor(COLORS['bg_light']))

class ModernButton(QPushButton):
    """Enhanced modern button with animations"""
    def __init__(self, text, parent=None, primary=True):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.primary = primary
        
        # Setup hover animation
        self._animation = QPropertyAnimation(self, b"geometry", self)
        self._animation.setDuration(100)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        
        if primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: {COLORS['text']};
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['primary_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['primary']};
                    padding: 13px 23px 11px 25px;
                }}
                QPushButton:disabled {{
                    background-color: {COLORS['bg_input']};
                    color: {COLORS['text_secondary']};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 16px;
                    background-color: {COLORS['bg_input']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 10px;
                    font-size: 14px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['primary_hover']};
                    padding: 17px 15px 15px 17px;
                }}
            """)
    
    def enterEvent(self, event):
        if not self.primary:
            rect = self.geometry()
            self._animation.setStartValue(rect)
            self._animation.setEndValue(QRect(rect.x()-2, rect.y()-2, rect.width()+4, rect.height()+4))
            self._animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if not self.primary:
            rect = self.geometry()
            self._animation.setStartValue(rect)
            self._animation.setEndValue(QRect(rect.x()+2, rect.y()+2, rect.width()-4, rect.height()-4))
            self._animation.start()
        super().leaveEvent(event)

class ModernTextEdit(QTextEdit):
    """Enhanced text edit with animations"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
                selection-background-color: {COLORS['primary']};
                selection-color: {COLORS['text']};
            }}
            QTextEdit:focus {{
                border-color: {COLORS['primary']};
                background-color: {COLORS['bg_light']};
            }}
        """)

class BrowserWindow(QMainWindow):
    instruction_submitted = pyqtSignal(str)
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🤖 AI Browser Operator")
        self.setGeometry(100, 100, 1800, 1000)  # Made window larger
        
        # Set dark theme
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
            }}
            QLabel {{
                background-color: transparent;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QSplitter::handle {{
                background-color: {COLORS['border']};
                width: 2px;
            }}
        """)
        
        # Main layout with three panels
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left control panel (using RoundedWidget)
        control_panel = RoundedWidget(radius=12)
        control_layout = QVBoxLayout(control_panel)
        control_layout.setSpacing(15)
        control_layout.setContentsMargins(20, 20, 20, 20)
        
        # Instruction section
        instruction_header = QWidget()
        header_layout = QHBoxLayout(instruction_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        instruction_label = QLabel("🎯 Enter Instructions")
        instruction_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {COLORS['text']};
        """)
        header_layout.addWidget(instruction_label)
        
        # Status indicator
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"""
            color: {COLORS['secondary']};
            font-size: 14px;
            padding: 4px 12px;
            border-radius: 12px;
            background-color: {COLORS['bg_input']};
        """)
        header_layout.addWidget(self.status_label, alignment=Qt.AlignRight)
        
        control_layout.addWidget(instruction_header)
        
        # Instruction input
        self.instruction_input = ModernTextEdit()
        self.instruction_input.setPlaceholderText("Enter your automation instructions here...")
        self.instruction_input.setMinimumHeight(100)
        self.instruction_input.setMaximumHeight(150)
        control_layout.addWidget(self.instruction_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.submit_button = ModernButton("▶️ Execute", primary=True)
        self.stop_button = ModernButton("⏹️ Stop", primary=True)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.stop_button)
        control_layout.addLayout(button_layout)
        
        # Example prompts section
        examples_label = QLabel("📚 Example Tasks")
        examples_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            margin-top: 10px;
            color: {COLORS['text']};
        """)
        control_layout.addWidget(examples_label)
        
        # Scroll area for examples
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {COLORS['bg_input']};
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['primary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        # Example buttons container
        examples_container = QWidget()
        examples_layout = QVBoxLayout(examples_container)
        examples_layout.setSpacing(10)
        examples_layout.setContentsMargins(0, 0, 0, 0)
        
        for example in EXAMPLE_PROMPTS:
            btn = ModernButton(example["title"], primary=False)
            btn.clicked.connect(lambda checked, p=example["prompt"]: self._set_example_prompt(p))
            examples_layout.addWidget(btn)
        
        examples_layout.addStretch()
        scroll_area.setWidget(examples_container)
        control_layout.addWidget(scroll_area)
        
        # Log section
        log_header = QWidget()
        log_layout = QHBoxLayout(log_header)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        log_label = QLabel("📋 Execution Log")
        log_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {COLORS['text']};
        """)
        log_layout.addWidget(log_label)
        
        # Clear log button
        self.clear_log_button = ModernButton("Clear", primary=False)
        self.clear_log_button.clicked.connect(self._clear_log)
        self.clear_log_button.setMaximumWidth(80)
        log_layout.addWidget(self.clear_log_button, alignment=Qt.AlignRight)
        
        control_layout.addWidget(log_header)
        
        self.log_output = ModernTextEdit()
        self.log_output.setReadOnly(True)
        control_layout.addWidget(self.log_output)
        
        # Right side splitter for browser and agent feedback
        right_splitter = QSplitter(Qt.Vertical)
        
        # Browser container (using RoundedWidget)
        browser_container = RoundedWidget(radius=12)
        browser_layout = QVBoxLayout(browser_container)
        browser_layout.setContentsMargins(20, 20, 20, 20)
        browser_layout.setSpacing(15)
        
        # Browser header
        browser_header = QWidget()
        header_layout = QHBoxLayout(browser_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        browser_label = QLabel("🌐 Browser View")
        browser_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {COLORS['text']};
        """)
        header_layout.addWidget(browser_label)
        
        # URL display
        self.url_label = QLabel()
        self.url_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 14px;
            padding: 4px 12px;
            border-radius: 12px;
            background-color: {COLORS['bg_input']};
        """)
        header_layout.addWidget(self.url_label, alignment=Qt.AlignRight)
        
        browser_layout.addWidget(browser_header)
        
        # Browser view
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://www.google.com"))
        self.browser.urlChanged.connect(self._update_url)
        self.browser.setStyleSheet(f"""
            QWebEngineView {{
                border-radius: 10px;
                background-color: {COLORS['bg_input']};
            }}
        """)
        browser_layout.addWidget(self.browser)
        
        # Agent Reasoning Panel
        reasoning_container = RoundedWidget(radius=12)
        reasoning_layout = QVBoxLayout(reasoning_container)
        reasoning_layout.setContentsMargins(20, 20, 20, 20)
        reasoning_layout.setSpacing(15)
        
        # Reasoning header
        reasoning_header = QWidget()
        reasoning_header_layout = QHBoxLayout(reasoning_header)
        reasoning_header_layout.setContentsMargins(0, 0, 0, 0)
        
        reasoning_label = QLabel("🧠 Agent Reasoning")
        reasoning_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {COLORS['text']};
        """)
        reasoning_header_layout.addWidget(reasoning_label)
        
        # Clear reasoning button
        self.clear_reasoning_button = ModernButton("Clear", primary=False)
        self.clear_reasoning_button.clicked.connect(self._clear_reasoning)
        self.clear_reasoning_button.setMaximumWidth(80)
        reasoning_header_layout.addWidget(self.clear_reasoning_button, alignment=Qt.AlignRight)
        
        reasoning_layout.addWidget(reasoning_header)
        
        # Reasoning display
        self.reasoning_output = ModernTextEdit()
        self.reasoning_output.setReadOnly(True)
        self.reasoning_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                selection-background-color: {COLORS['primary']};
                selection-color: {COLORS['text']};
                line-height: 1.6;
            }}
        """)
        reasoning_layout.addWidget(self.reasoning_output)
        
        # Add panels to splitters
        main_splitter.addWidget(control_panel)
        right_splitter.addWidget(browser_container)
        right_splitter.addWidget(reasoning_container)
        main_splitter.addWidget(right_splitter)
        
        # Set splitter proportions
        main_splitter.setStretchFactor(0, 1)  # Control panel
        main_splitter.setStretchFactor(1, 2)  # Right side
        right_splitter.setStretchFactor(0, 2)  # Browser
        right_splitter.setStretchFactor(1, 1)  # Reasoning
        
        # Connect signals
        self.submit_button.clicked.connect(self._on_submit)
        self.stop_button.clicked.connect(self._on_stop)
        self.instruction_input.textChanged.connect(self._on_input_change)
        
    def _set_example_prompt(self, prompt: str):
        """Set the instruction input text to the selected example prompt."""
        self.instruction_input.setPlainText(prompt)
        self.instruction_input.setFocus()
        
    def _on_submit(self):
        instruction = self.instruction_input.toPlainText().strip()
        if instruction:
            self.instruction_submitted.emit(instruction)
            self.submit_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("Running")
            self.status_label.setStyleSheet(f"""
                color: {COLORS['text']};
                font-size: 14px;
                padding: 4px 12px;
                border-radius: 12px;
                background-color: {COLORS['primary']};
            """)
            self.log_message("▶️ Starting execution...")
            
    def _on_stop(self):
        self.stop_requested.emit()
        self.submit_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-size: 14px;
            padding: 4px 12px;
            border-radius: 12px;
            background-color: {COLORS['error']};
        """)
        self.log_message("⏹️ Execution stopped.")
        
    def _on_input_change(self):
        """Enable submit button only if there's text"""
        has_text = bool(self.instruction_input.toPlainText().strip())
        self.submit_button.setEnabled(has_text)
        
    def _update_url(self, url):
        """Update URL display"""
        self.url_label.setText(url.toString())
        
    def _clear_log(self):
        """Clear the log output"""
        self.log_output.clear()
        
    def log_message(self, message: str):
        """Add message to log with timestamp"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def enable_submit(self):
        self.submit_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet(f"""
            color: {COLORS['secondary']};
            font-size: 14px;
            padding: 4px 12px;
            border-radius: 12px;
            background-color: {COLORS['bg_input']};
        """)
        self.log_message("✅ Ready for next task.")

    def _clear_reasoning(self):
        """Clear the reasoning output"""
        self.reasoning_output.clear()
        
    def add_reasoning(self, title: str, message: str, details: List[str] = None):
        """Add reasoning information to the UI."""
        html = f"""
        <div class="reasoning-block">
            <div class="reasoning-header">
                <span class="title">{title}</span>
            </div>
            <div class="reasoning-content">
                <p class="message">{message}</p>
                {self._format_details(details) if details else ''}
            </div>
        </div>
        """
        self.reasoning_output.append(html)
        self._scroll_to_bottom(self.reasoning_output)
        
    def add_execution(self, message: str, status: str = "info"):
        """Add execution step to the UI."""
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "step": "👉",
            "action": "🔄"
        }
        
        colors = {
            "info": "#569CD6",    # Blue
            "success": "#4EC9B0", # Green
            "warning": "#CE9178", # Orange
            "error": "#F44747",   # Red
            "step": "#DCDCAA",    # Yellow
            "action": "#C586C0"   # Purple
        }
        
        html = f"""
        <div class="execution-step" style="color: {colors.get(status, colors['info'])}">
            <span class="icon">{icons.get(status, icons['info'])}</span>
            <span class="message">{message}</span>
        </div>
        """
        self.execution_output.append(html)
        self._scroll_to_bottom(self.execution_output)
        
    def _format_details(self, details: List[str]) -> str:
        """Format details list as HTML."""
        if not details:
            return ""
            
        items = "\n".join([f"<li>{detail}</li>" for detail in details])
        return f"""
        <ul class="details-list">
            {items}
        </ul>
        """
        
    def _scroll_to_bottom(self, widget: QWidget):
        """Scroll widget to bottom."""
        scrollbar = widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def _setup_styles(self):
        """Setup CSS styles for the UI components."""
        self.setStyleSheet("""
            .reasoning-block {
                background-color: #2D2D2D;
                border-radius: 4px;
                margin: 8px 0;
                padding: 12px;
            }
            
            .reasoning-header {
                color: #569CD6;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 8px;
            }
            
            .reasoning-content {
                color: #D4D4D4;
                margin-left: 8px;
            }
            
            .message {
                margin: 4px 0;
            }
            
            .details-list {
                margin: 4px 0 4px 20px;
                padding: 0;
            }
            
            .details-list li {
                margin: 2px 0;
                color: #9CDCFE;
            }
            
            .execution-step {
                background-color: #2D2D2D;
                border-left: 4px solid;
                margin: 4px 0;
                padding: 6px 10px;
                font-family: "Menlo", "Monaco", "Courier New", monospace;
            }
            
            .icon {
                margin-right: 8px;
            }
        """)

#A PyQt main window with:
#	•	A browser view (QWebEngineView).
#	•	A text box for instructions.
#	•	Run / Stop buttons.
#	•	A log area to display agent messages.
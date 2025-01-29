# main.py
import sys
import asyncio
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QPushButton, QLineEdit, QLabel,
                            QSplitter, QListWidget, QListWidgetItem)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl, QObject, pyqtSignal, pyqtSlot, Qt
from browser_tools import BrowserTools
from loguru import logger
import qasync
from qasync import QEventLoop
from datetime import datetime
import os
import json
import re

class BrowserWindow(QMainWindow):
    instruction_submitted = pyqtSignal(str)
    stop_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Browser Automation")
        self.setGeometry(100, 100, 2000, 1200)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1E1E1E;
                color: #D4D4D4;
            }
            QLabel {
                color: #D4D4D4;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                background-color: #252526;
                border-radius: 4px;
            }
            QLineEdit {
                background-color: #2D2D2D;
                color: #D4D4D4;
                border: 1px solid #3E3E3E;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                margin: 2px;
            }
            QPushButton {
                background-color: #2D2D2D;
                color: #D4D4D4;
                border: 1px solid #3E3E3E;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                text-align: left;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #3E3E3E;
                border-color: #569CD6;
            }
            QPushButton.task {
                background-color: #252526;
                border: 1px solid #2D2D2D;
                padding: 12px;
                margin: 4px 0;
            }
            QPushButton.task:hover {
                background-color: #2D2D2D;
                border-color: #569CD6;
            }
            QPushButton.action {
                background-color: #0E639C;
                color: white;
                border: none;
                font-weight: bold;
                text-align: center;
            }
            QPushButton.action:hover {
                background-color: #1177BB;
            }
            QPushButton.stop {
                background-color: #CE4646;
                color: white;
                border: none;
                font-weight: bold;
                text-align: center;
            }
            QPushButton.stop:hover {
                background-color: #D45555;
            }
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3E3E3E;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                margin: 2px;
            }
        """)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create left panel
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)  # Fixed width for left panel
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        
        # Instructions section
        instructions_group = QWidget()
        instructions_layout = QVBoxLayout(instructions_group)
        instructions_layout.setSpacing(8)
        
        instructions_label = QLabel("🤖 Enter Instructions")
        instructions_layout.addWidget(instructions_label)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter instructions or click an example below...")
        self.input.setMinimumHeight(36)
        instructions_layout.addWidget(self.input)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.submit_button = QPushButton("▶ Execute")
        self.submit_button.setMinimumHeight(36)
        self.submit_button.setProperty("class", "action")
        
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.setMinimumHeight(36)
        self.stop_button.setProperty("class", "stop")
        
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.stop_button)
        instructions_layout.addLayout(button_layout)
        
        left_layout.addWidget(instructions_group)
        
        # Example tasks section
        tasks_group = QWidget()
        tasks_layout = QVBoxLayout(tasks_group)
        tasks_layout.setSpacing(8)
        
        tasks_label = QLabel("📋 Quick Actions")
        tasks_layout.addWidget(tasks_label)
        
        # Example task buttons with descriptions
        examples = [
            ("🔍 Google Search", "Search on Google", "Go to google.com and search for 'Python programming'"),
            ("📝 Contact Form", "Fill out a form", "Fill out the contact form with name 'John Doe', email 'john@example.com'"),
            ("🛍️ Amazon Deals", "Browse Amazon deals", "Go to amazon.com, click on 'Today's Deals', and then filter by 'Electronics'"),
            ("🍽️ Book Restaurant", "Make a reservation", "Book a table for 2 people at 7 PM tonight"),
            ("🍴 Restaurant Info", "Get restaurant details", "Find the menu and opening hours for the restaurant")
        ]
        
        for icon_text, tooltip, instruction in examples:
            btn = QPushButton(f"{icon_text}")
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(45)
            btn.setProperty("class", "task")
            btn.clicked.connect(lambda checked, text=instruction: self._set_example(text))
            tasks_layout.addWidget(btn)
        
        left_layout.addWidget(tasks_group)
        
        # Execution log section
        log_group = QWidget()
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(8)
        
        log_header = QWidget()
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(0, 0, 0, 0)
        
        log_label = QLabel("📜 Execution Log")
        log_header_layout.addWidget(log_label)
        
        clear_log_button = QPushButton("Clear")
        clear_log_button.setProperty("class", "action")
        clear_log_button.setMaximumWidth(80)
        clear_log_button.clicked.connect(lambda: self.log.clear())
        log_header_layout.addWidget(clear_log_button)
        
        log_layout.addWidget(log_header)
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(200)
        log_layout.addWidget(self.log)
        
        left_layout.addWidget(log_group)
        
        # Create right panel with stacked layout for browser and recording view
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        
        # Browser section
        browser_group = QWidget()
        browser_layout = QVBoxLayout(browser_group)
        browser_layout.setSpacing(8)
        
        browser_header = QWidget()
        browser_header_layout = QHBoxLayout(browser_header)
        browser_header_layout.setContentsMargins(0, 0, 0, 0)
        
        browser_label = QLabel("🌐 Browser View")
        browser_header_layout.addWidget(browser_label)
        
        # Add recording indicator
        self.recording_label = QLabel("⚫ Not Recording")
        self.recording_label.setStyleSheet("""
            color: #CE4646;
            padding: 4px 12px;
            border-radius: 12px;
            background-color: #2D2D2D;
        """)
        browser_header_layout.addWidget(self.recording_label, alignment=Qt.AlignRight)
        
        browser_layout.addWidget(browser_header)
        
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://www.google.com"))
        browser_layout.addWidget(self.browser)
        
        right_layout.addWidget(browser_group, stretch=3)
        
        # Add recording viewer
        recording_group = QWidget()
        recording_layout = QVBoxLayout(recording_group)
        recording_layout.setSpacing(8)
        
        recording_header = QWidget()
        recording_header_layout = QHBoxLayout(recording_header)
        recording_header_layout.setContentsMargins(0, 0, 0, 0)
        
        recording_label = QLabel("📹 Recording History")
        recording_header_layout.addWidget(recording_label)
        
        # Add recording controls
        self.play_button = QPushButton("▶")
        self.play_button.setProperty("class", "action")
        self.play_button.setMaximumWidth(40)
        self.play_button.clicked.connect(self._toggle_playback)
        recording_header_layout.addWidget(self.play_button)
        
        recording_layout.addWidget(recording_header)
        
        # Add recording list
        self.recording_list = QListWidget()
        self.recording_list.setStyleSheet("""
            QListWidget {
                background-color: #2D2D2D;
                border: 1px solid #3E3E3E;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                color: #D4D4D4;
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #3E3E3E;
            }
            QListWidget::item:selected {
                background-color: #0E639C;
            }
        """)
        recording_layout.addWidget(self.recording_list)
        
        right_layout.addWidget(recording_group, stretch=1)
        
        # Agent reasoning section
        reasoning_group = QWidget()
        reasoning_layout = QVBoxLayout(reasoning_group)
        reasoning_layout.setSpacing(8)
        
        reasoning_header = QWidget()
        reasoning_header_layout = QHBoxLayout(reasoning_header)
        reasoning_header_layout.setContentsMargins(0, 0, 0, 0)
        
        reasoning_label = QLabel("🧠 Agent Reasoning")
        reasoning_header_layout.addWidget(reasoning_label)
        
        clear_button = QPushButton("Clear")
        clear_button.setProperty("class", "action")
        clear_button.setMaximumWidth(80)
        clear_button.clicked.connect(lambda: self.reasoning.clear())
        reasoning_header_layout.addWidget(clear_button)
        
        reasoning_layout.addWidget(reasoning_header)
        
        self.reasoning = QTextEdit()
        self.reasoning.setReadOnly(True)
        self.reasoning.setMinimumHeight(200)
        self.reasoning.setStyleSheet("""
            QTextEdit {
                font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3E3E3E;
                border-radius: 4px;
                padding: 10px;
                selection-background-color: #264F78;
            }
        """)
        reasoning_layout.addWidget(self.reasoning)
        
        right_layout.addWidget(reasoning_group, stretch=1)
        
        # Add panels to splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)  # Give more space to browser
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3E3E3E;
            }
        """)
        
        main_layout.addWidget(splitter)
        
        # Connect signals
        self.submit_button.clicked.connect(self._on_submit)
        self.stop_button.clicked.connect(self._on_stop)
        self.input.returnPressed.connect(self._on_submit)
        
        # Add initial welcome message
        welcome_message = """
        <div style='
            background-color: #252526;
            border: 1px solid #3E3E3E;
            margin: 8px 0;
            padding: 12px;
            border-radius: 4px;
        '>
            <div style='color: #569CD6; font-size: 16px; font-weight: bold; margin-bottom: 8px;'>
                👋 Welcome to Browser Automation!
            </div>
            <div style='color: #D4D4D4; margin-left: 8px; line-height: 1.4;'>
                I'm your automation assistant. Here's how to get started:
                <ul style='margin-top: 8px; margin-bottom: 8px;'>
                    <li>Click any Quick Action on the left</li>
                    <li>Or type your own instruction above</li>
                    <li>Watch this panel for real-time updates</li>
                </ul>
                Ready to help you automate your browsing tasks!
            </div>
        </div>
        """
        self.reasoning.append(welcome_message)
        
    def _set_example(self, text: str):
        """Set the input text to the example instruction"""
        self.input.setText(text)
        
    def _on_submit(self):
        instruction = self.input.text().strip()
        if instruction:
            self.submit_button.setEnabled(False)
            self.instruction_submitted.emit(instruction)
            
    def _on_stop(self):
        self.stop_requested.emit()
        
    def log_message(self, message: str, type: str = "info"):
        """Add a message to the execution log with formatting"""
        colors = {
            "info": "#569CD6",    # Blue
            "success": "#4EC9B0", # Green
            "warning": "#CE9178", # Orange
            "error": "#F44747",   # Red
            "step": "#DCDCAA",    # Yellow
            "action": "#C586C0"   # Purple
        }
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "step": "👉",
            "action": "🔄"
        }
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        formatted_message = f"""
        <div style='
            background-color: #2D2D2D;
            border-left: 4px solid {colors.get(type, colors["info"])};
            margin: 4px 0;
            padding: 6px 10px;
            border-radius: 4px;
            font-family: "Menlo", "Monaco", "Courier New", monospace;
        '>
            <span style='color: #858585;'>[{timestamp}]</span>
            <span style='color: {colors.get(type, colors["info"])}; margin-left: 8px;'>
                {icons.get(type, "")} {message}
            </span>
        </div>
        """
        self.log.append(formatted_message)
        # Scroll to bottom
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def add_reasoning(self, title: str, message: str, type: str = "info"):
        """Add a reasoning step with colored formatting"""
        colors = {
            "info": "#569CD6",    # Blue for general info
            "success": "#4EC9B0", # Green for success
            "warning": "#CE9178", # Orange for warnings
            "error": "#F44747",   # Red for errors
            "thinking": "#DCDCAA", # Yellow for processing
            "action": "#C586C0"   # Purple for actions
        }
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "thinking": "🤔",
            "action": "🔄"
        }
        color = colors.get(type, colors["info"])
        icon = icons.get(type, "")
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        formatted_message = f"""
        <div style='
            background-color: #2D2D2D;
            border-left: 4px solid {color};
            margin: 8px 0;
            padding: 8px 12px;
            border-radius: 4px;
        '>
            <div style='margin-bottom: 6px;'>
                <span style='color: #858585;'>[{timestamp}]</span>
                <span style='color: {color}; font-weight: bold; margin-left: 8px;'>
                    {icon} {title}
                </span>
            </div>
            <div style='color: #D4D4D4; margin-left: 24px; line-height: 1.4;'>
                {message}
            </div>
        </div>
        """
        self.reasoning.append(formatted_message)
        # Scroll to bottom
        scrollbar = self.reasoning.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def enable_submit(self):
        self.submit_button.setEnabled(True)

    def update_recording_status(self, is_recording: bool):
        """Update recording indicator"""
        if is_recording:
            self.recording_label.setText("🔴 Recording")
            self.recording_label.setStyleSheet("""
                color: #CE4646;
                padding: 4px 12px;
                border-radius: 12px;
                background-color: #2D2D2D;
            """)
        else:
            self.recording_label.setText("⚫ Not Recording")
            self.recording_label.setStyleSheet("""
                color: #858585;
                padding: 4px 12px;
                border-radius: 12px;
                background-color: #2D2D2D;
            """)
    
    def _toggle_playback(self):
        """Toggle playback of selected recording"""
        selected_items = self.recording_list.selectedItems()
        if not selected_items:
            return
            
        session_id = selected_items[0].data(Qt.UserRole)
        if self.play_button.text() == "▶":
            self.play_button.setText("⏸")
            self._play_recording(session_id)
        else:
            self.play_button.setText("▶")
            self._stop_playback()
    
    def _play_recording(self, session_id: str):
        """Play back a recorded session"""
        # Implementation will be added
        pass
    
    def _stop_playback(self):
        """Stop current playback"""
        # Implementation will be added
        pass
    
    def add_recording(self, session_id: str, metadata: dict):
        """Add a recording to the list"""
        item = QListWidgetItem()
        timestamp = datetime.fromisoformat(metadata["timestamp"])
        item.setText(f"{timestamp.strftime('%H:%M:%S')} - {metadata['screenshots']} frames")
        item.setData(Qt.UserRole, session_id)
        self.recording_list.addItem(item)
        self.recording_list.scrollToBottom()

class BrowserAutomation(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        # Create UI
        self.window = BrowserWindow()
        
        # Create browser tools with the browser's page
        self.tools = BrowserTools(self.window.browser)
        
        # Setup logging
        logger.add(
            "automation.log",
            rotation="500 MB",
            level="INFO"
        )
        
        # Connect signals
        self.window.instruction_submitted.connect(self._handle_instruction)
        self.window.stop_requested.connect(self._handle_stop)
        
        # Load existing recordings
        self._load_recordings()
        
    def _load_recordings(self):
        """Load existing recordings from disk"""
        try:
            recordings_dir = "recordings"
            if os.path.exists(recordings_dir):
                for session_id in os.listdir(recordings_dir):
                    session_dir = os.path.join(recordings_dir, session_id)
                    metadata_file = os.path.join(session_dir, "metadata.json")
                    if os.path.isfile(metadata_file):
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                            self.window.add_recording(session_id, metadata)
        except Exception as e:
            logger.error(f"Error loading recordings: {str(e)}")
        
    @pyqtSlot(str)
    def _handle_instruction(self, instruction: str):
        """Handle instruction from UI by scheduling it in the event loop"""
        self.loop.create_task(self._execute_instruction(instruction))
        
    async def _execute_instruction(self, instruction: str):
        """Execute an instruction using browser tools"""
        try:
            # Clear previous logs
            self.window.reasoning.clear()
            self.window.log.clear()
            
            # Initial task analysis
            self.window.add_reasoning(
                "Task Analysis",
                f"""Analyzing instruction: "{instruction}"
                
                Breaking down the task:
                1. Understanding the goal
                2. Planning required actions
                3. Preparing execution strategy""",
                "thinking"
            )
            
            # Update recording status
            self.window.update_recording_status(True)
            
            # Extract URL if present (handle multiple formats)
            url = None
            instruction_lower = instruction.lower()
            
            # Common URL indicators and their patterns
            url_patterns = {
                'go to': r'go to\s+([^\s,]+)',
                'navigate to': r'navigate to\s+([^\s,]+)',
                'open': r'open\s+([^\s,]+)',
                'visit': r'visit\s+([^\s,]+)'
            }
            
            for pattern in url_patterns.values():
                if match := re.search(pattern, instruction_lower):
                    url = match.group(1).strip('., ')
                    # Clean up common domains
                    if url == 'amazon':
                        url = 'amazon.com'
                    elif url == 'google':
                        url = 'google.com'
                    break
                    
            if not url and any(domain in instruction_lower for domain in ['amazon.com', 'google.com']):
                # Direct domain mention without indicator
                url = next(domain for domain in ['amazon.com', 'google.com'] if domain in instruction_lower)
            
            # Create task dictionary
            task = {
                "goal": instruction,
                "url": url if url else None
            }
            
            if url:
                self.window.add_reasoning(
                    "Navigation Planning",
                    f"""Detected navigation request:
                    • Target URL: {url}
                    • Will attempt to navigate and verify domain
                    • Will wait for page load completion""",
                    "info"
                )
                self.window.log_message(f"Planning navigation to: {url}", "step")
            
            # Execute the task
            self.window.log_message("Starting task execution", "info")
            success = await self.tools.execute_task(task)
            
            # Add recording to list if successful
            if success and self.tools.current_session:
                session_dir = os.path.join("recordings", self.tools.current_session)
                metadata_file = os.path.join(session_dir, "metadata.json")
                if os.path.isfile(metadata_file):
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                        self.window.add_recording(self.tools.current_session, metadata)
            
            if success:
                self.window.add_reasoning(
                    "Task Complete",
                    """Successfully executed all actions:
                    ✓ Navigation completed
                    ✓ Page interactions successful
                    ✓ Task goals achieved""",
                    "success"
                )
                self.window.log_message("Task completed successfully", "success")
            else:
                self.window.add_reasoning(
                    "Task Failed",
                    """Failed to complete the task:
                    ✗ One or more actions failed
                    ✗ See execution log for details
                    ✗ Consider refining the instruction""",
                    "error"
                )
                self.window.log_message("Task execution failed", "error")
                
        except Exception as e:
            self.window.add_reasoning(
                "Error",
                f"""An error occurred during execution:
                • Error type: {type(e).__name__}
                • Error message: {str(e)}
                • Consider checking network connection
                • Verify if the target site is accessible""",
                "error"
            )
            self.window.log_message(f"Error: {str(e)}", "error")
        finally:
            # Update recording status
            self.window.update_recording_status(False)
            self.window.enable_submit()
            
    @pyqtSlot()
    def _handle_stop(self):
        """Handle stop request from UI"""
        self.window.add_reasoning(
            "Stop Requested",
            "Attempting to stop current execution. Please wait...",
            "warning"
        )
        self.window.log_message("Stopping automation...", "warning")
        self.window.enable_submit()
        
    def run(self):
        """Start the application"""
        self.window.show()
        with self.loop:
            self.loop.run_forever()

def main():
    # Initialize Qt application
    app = QApplication(sys.argv)

    # Create and run the browser automation
    automation = BrowserAutomation(app)
    automation.run()

if __name__ == "__main__":
    main()
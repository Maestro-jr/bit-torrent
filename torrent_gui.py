#!/usr/bin/env python3

import argparse
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import asyncio
import hashlib
import json
import logging
import os
import sys
from contextlib import closing
from functools import partial, partialmethod
from math import floor
from pathlib import Path
from typing import Dict, List, Optional

# noinspection PyUnresolvedReferences
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect
# noinspection PyUnresolvedReferences
from PyQt5.QtGui import QIcon, QFont, QDropEvent, QPalette, QColor, QLinearGradient, QPainter, QPixmap
# noinspection PyUnresolvedReferences
from PyQt5.QtWidgets import QWidget, QListWidget, QAbstractItemView, QLabel, QVBoxLayout, QProgressBar, \
    QListWidgetItem, QMainWindow, QApplication, QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QTreeWidget, \
    QTreeWidgetItem, QHeaderView, QHBoxLayout, QPushButton, QLineEdit, QAction, QStackedWidget, \
    QGraphicsDropShadowEffect

from torrent_client.control.manager import ControlManager
from torrent_client.control.server import ControlServer
from torrent_client.control.client import ControlClient
from torrent_client.models import TorrentState, TorrentInfo, FileTreeNode, FileInfo
from torrent_client.utils import humanize_speed, humanize_time, humanize_size

logging.basicConfig(format='%(levelname)s %(asctime)s %(name)-23s %(message)s', datefmt='%H:%M:%S')

ICON_DIRECTORY = os.path.join(os.path.dirname(__file__), 'icons')
USERS_FILE = os.path.expanduser('~/.bizfiz_users.json')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "fonyuyjunior4@gmail.com"
SENDER_PASSWORD = "jlhn halo qszr qdpo"  # App password

def load_icon(name: str):
    return QIcon(os.path.join(ICON_DIRECTORY, name + '.svg'))


file_icon = load_icon('file')
directory_icon = load_icon('directory')


def get_directory(directory: Optional[str]):
    return directory if directory is not None else os.getcwd()


class OTPManager:
    """Manages OTP generation and email sending"""

    def __init__(self):
        self.otp_storage = {}  # {email: {'otp': code, 'expires': timestamp}}

    def generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return str(random.randint(100000, 999999))

    def send_otp_email(self, recipient_email: str, username: str) -> tuple:
        """
        Send OTP via email
        Returns (success: bool, message: str, otp: str)
        """
        try:
            # Generate OTP
            otp = self.generate_otp()

            # Store OTP with 5-minute expiration
            self.otp_storage[recipient_email] = {
                'otp': otp,
                'expires': datetime.now() + timedelta(minutes=5)
            }

            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = "BizFiz - Email Verification Code"
            message["From"] = SENDER_EMAIL
            message["To"] = recipient_email

            # HTML email body
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f7fa;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 15px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h1 style="color: #667eea; font-size: 36px; margin: 0;">🔥 BizFiz</h1>
                            <p style="color: #7f8c8d; font-size: 16px; margin-top: 10px;">BitTorrent Client</p>
                        </div>

                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; padding: 30px; text-align: center; margin-bottom: 30px;">
                            <h2 style="color: white; font-size: 24px; margin: 0 0 15px 0;">Email Verification</h2>
                            <p style="color: rgba(255,255,255,0.9); margin: 0 0 20px 0;">Hello <strong>{username}</strong>!</p>
                            <p style="color: rgba(255,255,255,0.9); margin: 0 0 20px 0;">Your verification code is:</p>
                            <div style="background: white; border-radius: 10px; padding: 20px; display: inline-block;">
                                <span style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px;">{otp}</span>
                            </div>
                        </div>

                        <div style="text-align: center; color: #7f8c8d; font-size: 14px; line-height: 1.6;">
                            <p>This code will expire in <strong>5 minutes</strong>.</p>
                            <p>If you didn't request this code, please ignore this email.</p>
                            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                            <p style="font-size: 12px; color: #95a5a6;">
                                © 2024 BizFiz - BitTorrent Client<br>
                                Created by Fonyuy Berka Dzekem JR.
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """

            # Attach HTML content
            html_part = MIMEText(html, "html")
            message.attach(html_part)

            # Send email
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(message)

            return True, "OTP sent successfully!", otp

        except smtplib.SMTPAuthenticationError:
            return False, "Email authentication failed. Please check credentials.", None
        except smtplib.SMTPException as e:
            return False, f"Failed to send email: {str(e)}", None
        except Exception as e:
            return False, f"Error: {str(e)}", None

    def verify_otp(self, email: str, entered_otp: str) -> tuple:
        """
        Verify OTP
        Returns (success: bool, message: str)
        """
        if email not in self.otp_storage:
            return False, "No OTP found. Please request a new one."

        stored_data = self.otp_storage[email]

        # Check if OTP expired
        if datetime.now() > stored_data['expires']:
            del self.otp_storage[email]
            return False, "OTP has expired. Please request a new one."

        # Verify OTP
        if stored_data['otp'] == entered_otp:
            del self.otp_storage[email]  # Remove OTP after successful verification
            return True, "Email verified successfully!"
        else:
            return False, "Invalid OTP. Please try again."


# Add this import at the top of your main GUI file
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout


class UserManager:
    """Manages user authentication without a database"""

    def __init__(self):
        self.users_file = USERS_FILE
        self._ensure_default_user()

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _load_users(self) -> dict:
        """Load users from JSON file"""
        if not os.path.exists(self.users_file):
            return {}
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_users(self, users: dict):
        """Save users to JSON file"""
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)

    def _ensure_default_user(self):
        """Ensure default user fonyuy:fonyuy exists"""
        users = self._load_users()
        if 'fonyuy' not in users:
            users['fonyuy'] = {
                'password': self._hash_password('fonyuy'),
                'full_name': 'Fonyuy Berka Dzekem JR.'
            }
            self._save_users(users)

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user"""
        users = self._load_users()
        if username not in users:
            return False
        return users[username]['password'] == self._hash_password(password)

    def register(self, username: str, password: str, full_name: str = '') -> tuple:
        """Register new user. Returns (success, message)"""
        users = self._load_users()

        if len(username) < 3:
            return False, 'Username must be at least 3 characters'

        if len(password) < 4:
            return False, 'Password must be at least 4 characters'

        if username in users:
            return False, 'Username already exists'

        users[username] = {
            'password': self._hash_password(password),
            'full_name': full_name
        }
        self._save_users(users)
        return True, 'Account created successfully!'

    def get_user_info(self, username: str) -> dict:
        """Get user information"""
        users = self._load_users()
        return users.get(username, {})


class OTPVerificationDialog(QDialog):
    """Dialog for OTP verification"""

    def __init__(self, parent, email: str, otp_manager: OTPManager):
        super().__init__(parent)
        self.email = email
        self.otp_manager = otp_manager
        self.verified = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Email Verification')
        self.setFixedSize(450, 350)
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Container with gradient
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 15px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)

        # Icon and title
        title_label = QLabel('📧 Email Verification')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: white;
                background: transparent;
            }
        """)
        container_layout.addWidget(title_label)

        # Instructions
        instruction_label = QLabel(f'Enter the 6-digit code sent to:\n{self.email}')
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                background: transparent;
                margin-bottom: 10px;
            }
        """)
        container_layout.addWidget(instruction_label)

        # OTP input field
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText('Enter 6-digit code')
        self.otp_input.setMaxLength(6)
        self.otp_input.setAlignment(Qt.AlignCenter)
        self.otp_input.setStyleSheet("""
            QLineEdit {
                padding: 15px 20px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 25px;
                background: rgba(255, 255, 255, 0.95);
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
                letter-spacing: 10px;
            }
            QLineEdit:focus {
                border: 2px solid white;
                background: white;
            }
        """)
        container_layout.addWidget(self.otp_input)

        # Error message
        self.error_label = QLabel('')
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #ff4444;
                background: rgba(255, 68, 68, 0.2);
                padding: 10px;
                border-radius: 10px;
                font-size: 13px;
            }
        """)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Verify button
        verify_btn = QPushButton('Verify')
        verify_btn.setStyleSheet("""
            QPushButton {
                padding: 15px 30px;
                border: none;
                border-radius: 25px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f093fb, stop:1 #f5576c);
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f5576c, stop:1 #f093fb);
            }
        """)
        verify_btn.clicked.connect(self._verify_otp)
        button_layout.addWidget(verify_btn)

        # Resend button
        resend_btn = QPushButton('Resend Code')
        resend_btn.setStyleSheet("""
            QPushButton {
                padding: 15px 30px;
                border: 2px solid white;
                border-radius: 25px;
                background: transparent;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        resend_btn.clicked.connect(self._resend_otp)
        button_layout.addWidget(resend_btn)

        container_layout.addLayout(button_layout)

        # Cancel button
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                border: none;
                background: transparent;
                color: white;
                font-size: 14px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #f093fb;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        container_layout.addWidget(cancel_btn)

        main_layout.addWidget(container)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        container.setGraphicsEffect(shadow)

        # Focus on input
        self.otp_input.setFocus()
        self.otp_input.returnPressed.connect(self._verify_otp)

    def _verify_otp(self):
        """Verify the entered OTP"""
        entered_otp = self.otp_input.text().strip()

        if len(entered_otp) != 6:
            self._show_error("Please enter a 6-digit code")
            return

        success, message = self.otp_manager.verify_otp(self.email, entered_otp)

        if success:
            self.verified = True
            self.accept()
        else:
            self._show_error(message)
            self.otp_input.clear()
            self.otp_input.setFocus()

    def _resend_otp(self):
        """Resend OTP"""
        self.error_label.hide()
        success, message, _ = self.otp_manager.send_otp_email(self.email, "User")

        if success:
            self._show_error("New code sent!", is_error=False)
            QTimer.singleShot(2000, self.error_label.hide)
        else:
            self._show_error(message)

    def _show_error(self, message: str, is_error: bool = True):
        """Show error or success message"""
        if is_error:
            self.error_label.setStyleSheet("""
                QLabel {
                    color: #ff4444;
                    background: rgba(255, 68, 68, 0.2);
                    padding: 10px;
                    border-radius: 10px;
                    font-size: 13px;
                }
            """)
        else:
            self.error_label.setStyleSheet("""
                QLabel {
                    color: #44ff44;
                    background: rgba(68, 255, 68, 0.2);
                    padding: 10px;
                    border-radius: 10px;
                    font-size: 13px;
                }
            """)
        self.error_label.setText(message)
        self.error_label.show()


class OTPSenderThread(QThread):
    """Worker thread to send OTP emails without blocking the UI"""
    finished = pyqtSignal(bool, str, object)

    def __init__(self, otp_manager, email, name):
        super().__init__()
        self.otp_manager = otp_manager
        self.email = email
        self.name = name

    def run(self):
        try:
            success, message, otp = self.otp_manager.send_otp_email(self.email, self.name)
            self.finished.emit(success, message, otp)
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}", None)



class LoginWindow(QDialog):
    """Beautiful modern login/signup window"""

    login_successful = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.otp_manager = OTPManager()
        self.user_manager = UserManager()
        self.current_user = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('BizFiz - BitTorrent Client')
        self.setFixedSize(450, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Container widget with gradient background
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 15px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)

        # Logo/Title section
        title_label = QLabel('🔥 BizFiz')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: white;
                background: transparent;
                margin-bottom: 10px;
            }
        """)
        container_layout.addWidget(title_label)

        subtitle_label = QLabel('BitTorrent Client')
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: rgba(255, 255, 255, 0.8);
                background: transparent;
                margin-bottom: 20px;
            }
        """)
        container_layout.addWidget(subtitle_label)

        # Stacked widget for login/signup forms
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent;")

        # Login page
        self.login_page = self._create_login_page()
        self.stacked_widget.addWidget(self.login_page)

        # Signup page
        self.signup_page = self._create_signup_page()
        self.stacked_widget.addWidget(self.signup_page)

        container_layout.addWidget(self.stacked_widget)

        # Add stretch at bottom
        container_layout.addStretch()

        main_layout.addWidget(container)

        # Apply shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        container.setGraphicsEffect(shadow)

    def _create_input_field(self, placeholder: str, is_password: bool = False) -> QLineEdit:
        """Create styled input field"""
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        if is_password:
            field.setEchoMode(QLineEdit.Password)
        field.setStyleSheet("""
            QLineEdit {
                padding: 15px 20px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 25px;
                background: rgba(255, 255, 255, 0.95);
                font-size: 14px;
                color: #333;
            }
            QLineEdit:focus {
                border: 2px solid white;
                background: white;
            }
            QLineEdit::placeholder {
                color: rgba(100, 100, 100, 0.7);
            }
        """)
        return field

    def _create_button(self, text: str, primary: bool = True) -> QPushButton:
        """Create styled button"""
        button = QPushButton(text)
        if primary:
            button.setStyleSheet("""
                QPushButton {
                    padding: 15px 30px;
                    border: none;
                    border-radius: 25px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #f093fb, stop:1 #f5576c);
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #f5576c, stop:1 #f093fb);
                }
                QPushButton:pressed {
                    padding: 16px 30px 14px 30px;
                }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border: none;
                    background: transparent;
                    color: white;
                    font-size: 14px;
                    text-decoration: underline;
                }
                QPushButton:hover {
                    color: #f093fb;
                }
            """)
        return button

    def _create_login_page(self) -> QWidget:
        """Create login form"""
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        # Form title
        form_title = QLabel('Sign In')
        form_title.setAlignment(Qt.AlignCenter)
        form_title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: white;
                background: transparent;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(form_title)

        # Username field
        self.login_username = self._create_input_field('Username')
        layout.addWidget(self.login_username)

        # Password field
        self.login_password = self._create_input_field('Password', is_password=True)
        layout.addWidget(self.login_password)

        # Error message label
        self.login_error = QLabel('')
        self.login_error.setAlignment(Qt.AlignCenter)
        self.login_error.setStyleSheet("""
            QLabel {
                color: #ff4444;
                background: rgba(255, 68, 68, 0.2);
                padding: 10px;
                border-radius: 10px;
                font-size: 13px;
            }
        """)
        self.login_error.hide()
        layout.addWidget(self.login_error)

        # Login button
        login_btn = self._create_button('Login', primary=True)
        login_btn.clicked.connect(self._handle_login)
        layout.addWidget(login_btn)

        # Switch to signup
        switch_layout = QHBoxLayout()
        switch_label = QLabel('Don\'t have an account?')
        switch_label.setStyleSheet('color: white; background: transparent; font-size: 13px;')
        switch_btn = self._create_button('Sign Up', primary=False)
        switch_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        switch_layout.addStretch()
        switch_layout.addWidget(switch_label)
        switch_layout.addWidget(switch_btn)
        switch_layout.addStretch()
        layout.addLayout(switch_layout)

        # Allow Enter key to login
        self.login_password.returnPressed.connect(self._handle_login)

        return page

    def _create_signup_page(self) -> QWidget:
        """Create signup form"""
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        # Form title
        form_title = QLabel('Create Account')
        form_title.setAlignment(Qt.AlignCenter)
        form_title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: white;
                background: transparent;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(form_title)

        # Full name field
        self.signup_fullname = self._create_input_field('Full Name (Optional)')
        layout.addWidget(self.signup_fullname)

        # Username field
        self.signup_username = self._create_input_field('Email Address')
        layout.addWidget(self.signup_username)

        # Password field
        self.signup_password = self._create_input_field('Password', is_password=True)
        layout.addWidget(self.signup_password)

        # Confirm password field
        self.signup_confirm = self._create_input_field('Confirm Password', is_password=True)
        layout.addWidget(self.signup_confirm)

        # Error/Success message label
        self.signup_message = QLabel('')
        self.signup_message.setAlignment(Qt.AlignCenter)
        self.signup_message.setStyleSheet("""
            QLabel {
                color: #ff4444;
                background: rgba(255, 68, 68, 0.2);
                padding: 10px;
                border-radius: 10px;
                font-size: 13px;
            }
        """)
        self.signup_message.hide()
        layout.addWidget(self.signup_message)

        # Signup button
        signup_btn = self._create_button('Create Account', primary=True)
        signup_btn.clicked.connect(self._handle_signup)
        layout.addWidget(signup_btn)

        # Switch to login
        switch_layout = QHBoxLayout()
        switch_label = QLabel('Already have an account?')
        switch_label.setStyleSheet('color: white; background: transparent; font-size: 13px;')
        switch_btn = self._create_button('Sign In', primary=False)
        switch_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        switch_layout.addStretch()
        switch_layout.addWidget(switch_label)
        switch_layout.addWidget(switch_btn)
        switch_layout.addStretch()
        layout.addLayout(switch_layout)

        # Allow Enter key to signup
        self.signup_confirm.returnPressed.connect(self._handle_signup)

        return page

    def _show_error(self, widget: QLabel, message: str, is_error: bool = True):
        """Show error or success message"""
        if is_error:
            widget.setStyleSheet("""
                QLabel {
                    color: #ff4444;
                    background: rgba(255, 68, 68, 0.2);
                    padding: 10px;
                    border-radius: 10px;
                    font-size: 13px;
                }
            """)
        else:
            widget.setStyleSheet("""
                QLabel {
                    color: #44ff44;
                    background: rgba(68, 255, 68, 0.2);
                    padding: 10px;
                    border-radius: 10px;
                    font-size: 13px;
                }
            """)
        widget.setText(message)
        widget.show()

    def _handle_login(self):
        """Handle login attempt"""
        username = self.login_username.text().strip()
        password = self.login_password.text()

        if not username or not password:
            self._show_error(self.login_error, 'Please fill in all fields')
            return

        if self.user_manager.authenticate(username, password):
            self.current_user = username
            self.login_successful.emit(username)
            self.accept()
        else:
            self._show_error(self.login_error, 'Invalid username or password')
            self.login_password.clear()
            self.login_password.setFocus()

    def _handle_signup(self):
        """Handle signup attempt with OTP verification"""
        fullname = self.signup_fullname.text().strip()
        username = self.signup_username.text().strip()
        password = self.signup_password.text()
        confirm = self.signup_confirm.text()

        # Basic validation
        if not username or not password:
            self._show_error(self.signup_message, 'Username and password are required')
            return

        if password != confirm:
            self._show_error(self.signup_message, 'Passwords do not match')
            self.signup_confirm.clear()
            self.signup_confirm.setFocus()
            return

        if len(username) < 3:
            self._show_error(self.signup_message, 'Username must be at least 3 characters')
            return

        if len(password) < 4:
            self._show_error(self.signup_message, 'Password must be at least 4 characters')
            return

        users = self.user_manager._load_users()
        if username in users:
            self._show_error(self.signup_message, 'Username already exists')
            return

        if '@' not in username or '.' not in username:
            self._show_error(self.signup_message, 'Username must be a valid email address')
            return

        # Show loading message
        self._show_error(self.signup_message, 'Sending verification code...', is_error=False)
        QApplication.processEvents()

        # Store these values for use in the callback
        stored_username = username
        stored_password = password
        stored_fullname = fullname

        # Define callback function for when OTP is sent
        def on_otp_sent(success, message, otp):
            print(f"OTP sent callback: success={success}, message={message}")

            if not success:
                self._show_error(self.signup_message, f'Failed to send OTP: {message}')
                return

            # IMPORTANT: Hide the login window completely
            self.hide()
            QApplication.processEvents()

            # Show OTP verification dialog as a standalone window
            self._show_otp_dialog(stored_username, stored_password, stored_fullname)

        # Create and start the thread
        self.otp_thread = OTPSenderThread(
            self.otp_manager,
            username,
            fullname if fullname else username
        )

        # Connect the signal
        self.otp_thread.finished.connect(on_otp_sent)

        # Start the thread
        self.otp_thread.start()

    def _show_otp_dialog(self, username, password, fullname):
        """Show OTP verification dialog as standalone"""
        print(f"Showing OTP dialog for {username}")

        # Create OTP dialog with NO parent (standalone window)
        otp_dialog = OTPVerificationDialog(None, username, self.otp_manager)

        # Make it appear in front
        otp_dialog.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        otp_dialog.show()
        otp_dialog.raise_()
        otp_dialog.activateWindow()

        result = otp_dialog.exec()
        print(f"Dialog result: {result}, verified: {otp_dialog.verified}")

        if result == QDialog.Accepted and otp_dialog.verified:
            # OTP verified, create account
            success, message = self.user_manager.register(username, password, fullname)

            if success:
                # Show success message briefly
                self.show()
                QApplication.processEvents()
                self._show_error(self.signup_message, message, is_error=False)
                QApplication.processEvents()

                # Set the current user and emit login successful
                self.current_user = username

                # Close the dialog after a short delay to show success message
                QTimer.singleShot(1000, lambda: self._complete_signup(username))
            else:
                # Show error and return to signup
                self.show()
                QApplication.processEvents()
                self._show_error(self.signup_message, message)
        else:
            # OTP verification cancelled or failed - show login window again
            self.show()
            QApplication.processEvents()
            self._show_error(self.signup_message, 'Email verification cancelled')

    def _complete_signup(self, username):
        """Complete the signup process and open the main app"""
        print(f"Completing signup for {username}")
        self.current_user = username
        self.login_successful.emit(username)
        self.accept()  # This closes the LoginWindow and returns Accepted status


class TorrentAddingDialog(QDialog):
    SELECTION_LABEL_FORMAT = 'Selected {} files ({})'

    def _traverse_file_tree(self, name: str, node: FileTreeNode, parent: QWidget):
        item = QTreeWidgetItem(parent)
        item.setCheckState(0, Qt.Checked)
        item.setText(0, name)
        if isinstance(node, FileInfo):
            item.setText(1, humanize_size(node.length))
            item.setIcon(0, file_icon)
            self._file_items.append((node, item))
            return

        item.setIcon(0, directory_icon)
        for name, child in node.items():
            self._traverse_file_tree(name, child, item)

    def _get_directory_browse_widget(self):
        widget = QWidget()
        hbox = QHBoxLayout(widget)
        hbox.setContentsMargins(0, 0, 0, 0)

        self._path_edit = QLineEdit(self._download_dir)
        self._path_edit.setReadOnly(True)
        self._path_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background: #f8f9fa;
                color: #2c3e50;
            }
        """)
        hbox.addWidget(self._path_edit, 3)

        browse_button = QPushButton('Browse...')
        browse_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: none;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #764ba2, stop:1 #667eea);
            }
        """)
        browse_button.clicked.connect(self._browse)
        hbox.addWidget(browse_button, 1)

        widget.setLayout(hbox)
        return widget

    def _browse(self):
        new_download_dir = QFileDialog.getExistingDirectory(self, 'Select download directory', self._download_dir)
        if not new_download_dir:
            return

        self._download_dir = new_download_dir
        self._path_edit.setText(new_download_dir)

    def __init__(self, parent: QWidget, filename: str, torrent_info: TorrentInfo,
                 control_thread: 'ControlManagerThread'):
        super().__init__(parent)
        self._torrent_info = torrent_info
        download_info = torrent_info.download_info
        self._control_thread = control_thread
        self._control = control_thread.control

        # Apply beautiful styling
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f7fa, stop:1 #e8eef5);
            }
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 12px;
            }
            QTreeWidget {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background: white;
                padding: 5px;
            }
        """)

        vbox = QVBoxLayout(self)
        vbox.setSpacing(12)
        vbox.setContentsMargins(20, 20, 20, 20)

        self._download_dir = get_directory(self._control.last_download_dir)
        vbox.addWidget(QLabel('📁 Download directory:'))
        vbox.addWidget(self._get_directory_browse_widget())

        vbox.addWidget(QLabel('🌐 Announce URLs:'))

        url_tree = QTreeWidget()
        url_tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        url_tree.header().close()
        vbox.addWidget(url_tree)
        for i, tier in enumerate(torrent_info.announce_list):
            tier_item = QTreeWidgetItem(url_tree)
            tier_item.setText(0, 'Tier {}'.format(i + 1))
            for url in tier:
                url_item = QTreeWidgetItem(tier_item)
                url_item.setText(0, url)
        url_tree.expandAll()
        vbox.addWidget(url_tree, 1)

        file_tree = QTreeWidget()
        file_tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        file_tree.setHeaderLabels(('Name', 'Size'))
        file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._file_items = []
        self._traverse_file_tree(download_info.suggested_name, download_info.file_tree, file_tree)
        file_tree.sortItems(0, Qt.AscendingOrder)
        file_tree.expandAll()
        file_tree.itemClicked.connect(self._update_checkboxes)
        vbox.addWidget(file_tree, 3)

        self._selection_label = QLabel(TorrentAddingDialog.SELECTION_LABEL_FORMAT.format(
            len(download_info.files), humanize_size(download_info.total_size)))
        self._selection_label.setStyleSheet("""
            QLabel {
                color: #667eea;
                font-size: 13px;
                padding: 8px;
                background: rgba(102, 126, 234, 0.1);
                border-radius: 6px;
            }
        """)
        vbox.addWidget(self._selection_label)

        self._button_box = QDialogButtonBox(self)
        self._button_box.setOrientation(Qt.Horizontal)
        self._button_box.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self._button_box.setStyleSheet("""
            QDialogButtonBox QPushButton {
                padding: 10px 25px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                min-width: 80px;
            }
            QDialogButtonBox QPushButton[text="OK"] {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
            }
            QDialogButtonBox QPushButton[text="OK"]:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #764ba2, stop:1 #667eea);
            }
            QDialogButtonBox QPushButton[text="Cancel"] {
                background: #e0e0e0;
                color: #2c3e50;
            }
            QDialogButtonBox QPushButton[text="Cancel"]:hover {
                background: #d0d0d0;
            }
        """)
        self._button_box.button(QDialogButtonBox.Ok).clicked.connect(self.submit_torrent)
        self._button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        vbox.addWidget(self._button_box)

        self.setFixedSize(500, 600)
        self.setWindowTitle('✨ Adding "{}"'.format(filename))

    def _set_check_state_to_tree(self, item: QTreeWidgetItem, check_state: Qt.CheckState):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, check_state)
            self._set_check_state_to_tree(child, check_state)

    def _update_checkboxes(self, item: QTreeWidgetItem, column: int):
        if column != 0:
            return

        new_check_state = item.checkState(0)
        self._set_check_state_to_tree(item, new_check_state)

        while True:
            item = item.parent()
            if item is None:
                break

            has_checked_children = False
            has_partially_checked_children = False
            has_unchecked_children = False
            for i in range(item.childCount()):
                state = item.child(i).checkState(0)
                if state == Qt.Checked:
                    has_checked_children = True
                elif state == Qt.PartiallyChecked:
                    has_partially_checked_children = True
                else:
                    has_unchecked_children = True

            if not has_partially_checked_children and not has_unchecked_children:
                new_state = Qt.Checked
            elif has_checked_children or has_partially_checked_children:
                new_state = Qt.PartiallyChecked
            else:
                new_state = Qt.Unchecked
            item.setCheckState(0, new_state)

        self._update_selection_label()

    def _update_selection_label(self):
        selected_file_count = 0
        selected_size = 0
        for node, item in self._file_items:
            if item.checkState(0) == Qt.Checked:
                selected_file_count += 1
                selected_size += node.length

        ok_button = self._button_box.button(QDialogButtonBox.Ok)
        if not selected_file_count:
            ok_button.setEnabled(False)
            self._selection_label.setText('Nothing to download')
        else:
            ok_button.setEnabled(True)
            self._selection_label.setText(TorrentAddingDialog.SELECTION_LABEL_FORMAT.format(
                selected_file_count, humanize_size(selected_size)))

    def submit_torrent(self):
        self._torrent_info.download_dir = self._download_dir
        self._control.last_download_dir = os.path.abspath(self._download_dir)

        file_paths = []
        for node, item in self._file_items:
            if item.checkState(0) == Qt.Checked:
                file_paths.append(node.path)
        if not self._torrent_info.download_info.single_file_mode:
            self._torrent_info.download_info.select_files(file_paths, 'whitelist')

        self._control_thread.loop.call_soon_threadsafe(self._control.add, self._torrent_info)

        self.close()


class TorrentListWidgetItem(QWidget):
    _name_font = QFont()
    _name_font.setBold(True)

    _stats_font = QFont()
    _stats_font.setPointSize(10)

    def __init__(self):
        super().__init__()

        # Apply beautiful styling
        self.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 8px;
            }
        """)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(15, 12, 15, 12)
        vbox.setSpacing(8)

        self._name_label = QLabel()
        self._name_label.setFont(TorrentListWidgetItem._name_font)
        self._name_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
        """)
        vbox.addWidget(self._name_label)

        self._upper_status_label = QLabel()
        self._upper_status_label.setFont(TorrentListWidgetItem._stats_font)
        self._upper_status_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 11px;
            }
        """)
        vbox.addWidget(self._upper_status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(10000)
        self._progress_bar.setFixedHeight(24)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setAlignment(Qt.AlignCenter)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                text-align: center;
                background: #f5f7fa;
                color: #2c3e50;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
                border-radius: 10px;
                margin: 2px;
            }
        """)
        vbox.addWidget(self._progress_bar)

        self._lower_status_label = QLabel()
        self._lower_status_label.setFont(TorrentListWidgetItem._stats_font)
        self._lower_status_label.setStyleSheet("""
            QLabel {
                color: #34495e;
                font-size: 11px;
            }
        """)
        vbox.addWidget(self._lower_status_label)

        self._state = None
        self._waiting_control_action = False

    @property
    def state(self) -> TorrentState:
        return self._state

    @state.setter
    def state(self, state: TorrentState):
        self._state = state
        self.force_update()

    @property
    def waiting_control_action(self) -> bool:
        return self._waiting_control_action

    @waiting_control_action.setter
    def waiting_control_action(self, value: bool):
        self._waiting_control_action = value
        self.force_update()

    def force_update(self):
        if self._state is None:
            return

        state = self._state
        self._name_label.setText(state.suggested_name)

        if state.downloaded_size < state.selected_size:
            status_text = '{} of {} downloaded'.format(
                humanize_size(state.downloaded_size),
                humanize_size(state.selected_size)
            )
        else:
            status_text = '{} (complete)'.format(humanize_size(state.selected_size))
        status_text += ' | Ratio: {:.2f}'.format(state.ratio)
        self._upper_status_label.setText(status_text)

        progress_value = int(state.progress * 10000)
        self._progress_bar.setValue(progress_value)
        percentage = state.progress * 100
        self._progress_bar.setFormat('{:.1f}%'.format(percentage))

        if self.waiting_control_action:
            status_text = '⏳ Waiting...'
        elif state.paused:
            status_text = '⏸ Paused'
        elif state.complete:
            peer_count = max(state.total_peer_count, 1)
            upload_count = state.uploading_peer_count if state.uploading_peer_count > 0 else 0

            status_text = '⬆ Uploading to {} of {} peer{}'.format(
                upload_count,
                peer_count,
                's' if peer_count != 1 else ''
            )
            if state.upload_speed and state.upload_speed > 0:
                status_text += ' @ {}/s'.format(humanize_size(state.upload_speed))
        else:
            peer_count = max(state.total_peer_count, 1)
            download_count = max(state.downloading_peer_count, 1)

            status_text = '⬇ Downloading from {} of {} peer{}'.format(
                download_count,
                peer_count,
                's' if peer_count != 1 else ''
            )

            if state.download_speed and state.download_speed > 0:
                status_text += ' @ {}/s'.format(humanize_size(state.download_speed))

            eta_seconds = state.eta_seconds
            if eta_seconds is not None and eta_seconds > 0:
                status_text += ' | {} remaining'.format(humanize_time(eta_seconds))
            elif state.downloaded_size == 0:
                status_text += ' | Starting download...'

        self._lower_status_label.setText(status_text)
        self.update()
        self.repaint()


class TorrentListWidget(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSpacing(3)
        self.setAcceptDrops(True)

    def drag_handler(self, event: QDropEvent, drop: bool = False):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            if drop:
                self.files_dropped.emit([url.toLocalFile() for url in event.mimeData().urls()])
        else:
            event.ignore()

    dragEnterEvent = drag_handler
    dragMoveEvent = drag_handler
    dropEvent = partialmethod(drag_handler, drop=True)


class MainWindow(QMainWindow):
    def __init__(self, control_thread: 'ControlManagerThread', username: str):
        super().__init__()

        self._control_thread = control_thread
        self._current_user = username
        control = control_thread.control

        # Apply modern styling to main window
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f7fa, stop:1 #e8eef5);
            }
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
                padding: 8px;
                spacing: 10px;
            }
            QToolButton {
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 15px;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.1);
                margin: 2px;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            QToolButton:pressed {
                background: rgba(255, 255, 255, 0.3);
            }
            QToolButton:disabled {
                color: rgba(255, 255, 255, 0.4);
                background: transparent;
            }
        """)

        toolbar = self.addToolBar('Controls')
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setMovable(False)

        self._add_action = toolbar.addAction(load_icon('add'), 'Add Torrent')
        self._add_action.triggered.connect(self._add_torrents_triggered)

        self._pause_action = toolbar.addAction(load_icon('pause'), 'Pause')
        self._pause_action.setEnabled(False)
        self._pause_action.triggered.connect(partial(self._control_action_triggered, control.pause))

        self._resume_action = toolbar.addAction(load_icon('resume'), 'Resume')
        self._resume_action.setEnabled(False)
        self._resume_action.triggered.connect(partial(self._control_action_triggered, control.resume))

        self._remove_action = toolbar.addAction(load_icon('remove'), 'Remove')
        self._remove_action.setEnabled(False)
        self._remove_action.triggered.connect(partial(self._control_action_triggered, control.remove))

        toolbar.addSeparator()

        self._about_action = toolbar.addAction(load_icon('about'), 'About')
        self._about_action.triggered.connect(self._show_about)

        # Create beautiful list widget
        self._list_widget = TorrentListWidget()
        self._list_widget.setStyleSheet("""
            QListWidget {
                background: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }
            QListWidget::item {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: white;
                margin: 3px;
            }
            QListWidget::item:selected {
                border: 2px solid #667eea;
                background: #f0f3ff;
            }
            QListWidget::item:hover {
                background: #f8f9fa;
            }
        """)
        self._list_widget.itemSelectionChanged.connect(self._update_control_action_state)
        self._list_widget.files_dropped.connect(self.add_torrent_files)
        self._torrent_to_item = {}

        # Create container with padding
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.addWidget(self._list_widget)

        self.setCentralWidget(container)
        self.setMinimumSize(650, 550)
        self.resize(750, 650)
        self.setWindowTitle(f'🔥 BizFiz - BitTorrent Client | User: {username}')

        control_thread.error_happened.connect(self._error_happened)
        control.torrents_suggested.connect(self.add_torrent_files)
        control.torrent_added.connect(self._add_torrent_item)
        control.torrent_changed.connect(self._update_torrent_item)
        control.torrent_removed.connect(self._remove_torrent_item)

        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._poll_torrent_states)
        self._update_timer.start(200)

        self.show()

    def _poll_torrent_states(self):
        try:
            if hasattr(self._control_thread.control, '_torrents'):
                torrents_dict = self._control_thread.control._torrents
                for info_hash, torrent_info in torrents_dict.items():
                    if info_hash in self._torrent_to_item:
                        state = TorrentState(torrent_info)
                        self._update_torrent_item(state)
            QApplication.processEvents()
        except Exception as e:
            pass

    def _add_torrent_item(self, state: TorrentState):
        widget = TorrentListWidgetItem()
        widget.state = state

        item = QListWidgetItem()
        item.setIcon(file_icon if state.single_file_mode else directory_icon)
        item.setSizeHint(widget.sizeHint())
        item.setData(Qt.UserRole, state.info_hash)

        items_upper = 0
        for i in range(self._list_widget.count()):
            prev_item = self._list_widget.item(i)
            widget_item = self._list_widget.itemWidget(prev_item)
            if widget_item and widget_item.state.suggested_name > state.suggested_name:
                break
            items_upper += 1

        self._list_widget.insertItem(items_upper, item)
        self._list_widget.setItemWidget(item, widget)
        self._torrent_to_item[state.info_hash] = item

    def _update_torrent_item(self, state: TorrentState):
        if state.info_hash not in self._torrent_to_item:
            return
        item = self._torrent_to_item[state.info_hash]
        widget = self._list_widget.itemWidget(item)
        if widget is None:
            return
        if widget.state and widget.state.paused != state.paused:
            widget.waiting_control_action = False
        widget.state = state
        self._update_control_action_state()

    def _remove_torrent_item(self, info_hash: bytes):
        if info_hash not in self._torrent_to_item:
            return
        item = self._torrent_to_item[info_hash]
        self._list_widget.takeItem(self._list_widget.row(item))
        del self._torrent_to_item[info_hash]
        self._update_control_action_state()

    def _update_control_action_state(self):
        self._pause_action.setEnabled(False)
        self._resume_action.setEnabled(False)
        self._remove_action.setEnabled(False)
        for item in self._list_widget.selectedItems():
            widget = self._list_widget.itemWidget(item)
            if widget is None or widget.waiting_control_action:
                continue
            if widget.state.paused:
                self._resume_action.setEnabled(True)
            else:
                self._pause_action.setEnabled(True)
            self._remove_action.setEnabled(True)

    def _error_happened(self, description: str, err: Exception):
        QMessageBox.critical(self, description, str(err))

    def add_torrent_files(self, paths: List[str]):
        for path in paths:
            try:
                torrent_info = TorrentInfo.from_file(path, download_dir=None)
                self._control_thread.control.last_torrent_dir = os.path.abspath(os.path.dirname(path))
                if torrent_info.download_info.info_hash in self._torrent_to_item:
                    raise ValueError('This torrent is already added')
            except Exception as err:
                self._error_happened('Failed to add "{}"'.format(path), err)
                continue
            TorrentAddingDialog(self, path, torrent_info, self._control_thread).exec()

    def _add_torrents_triggered(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            'Add Torrents',
            self._control_thread.control.last_torrent_dir,
            'Torrent Files (*.torrent);;All Files (*)'
        )
        self.add_torrent_files(paths)

    @staticmethod
    async def _invoke_control_action(action, info_hash: bytes):
        try:
            result = action(info_hash)
            if asyncio.iscoroutine(result):
                await result
        except ValueError:
            pass

    def _control_action_triggered(self, action):
        for item in self._list_widget.selectedItems():
            widget = self._list_widget.itemWidget(item)
            if widget is None or widget.waiting_control_action:
                continue
            info_hash = item.data(Qt.UserRole)
            asyncio.run_coroutine_threadsafe(
                MainWindow._invoke_control_action(action, info_hash),
                self._control_thread.loop
            )
            widget.waiting_control_action = True
        self._update_control_action_state()

    def _show_about(self):
        QMessageBox.about(
            self,
            'About BizFiz',
            f'<p><b>BitTorrent Client - BizFiz</b></p>'
            f'<p>Version 1.0</p>'
            f'<p>Logged in as: <b>{self._current_user}</b></p>'
            f'<p>Created by <b>Fonyuy Berka Dzekem JR.</b></p>'
            f'<p>A fully functional BitTorrent client with download/upload capabilities.</p>'
            f'<p>Features: Multi-file torrents, resume support, speed monitoring</p>'
        )

    def closeEvent(self, event):
        if hasattr(self, '_update_timer'):
            self._update_timer.stop()
        event.accept()


class ControlManagerThread(QThread):
    error_happened = pyqtSignal(str, Exception)

    def __init__(self):
        super().__init__()
        self._loop = None
        self._control = ControlManager()
        self._control_server = ControlServer(self._control, None)
        self._stopping = False

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def control(self) -> ControlManager:
        return self._control

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        with closing(self._loop):
            self._loop.run_until_complete(self._control.start())
            self._loop.run_until_complete(self._control_server.start())
            try:
                self._control.load_state()
            except Exception as err:
                self.error_happened.emit('Failed to load program state', err)
            self._control.invoke_state_dumps()
            self._loop.run_forever()

    def stop(self):
        if self._stopping:
            return
        self._stopping = True
        if self._loop is None or not self._loop.is_running():
            return

        async def stop_all():
            try:
                server_stop = self._control_server.stop()
                if asyncio.iscoroutine(server_stop):
                    await server_stop
            except Exception as e:
                logging.error(f"Error stopping control server: {e}")
            try:
                control_stop = self._control.stop()
                if asyncio.iscoroutine(control_stop):
                    await control_stop
            except Exception as e:
                logging.error(f"Error stopping control manager: {e}")

        try:
            stop_future = asyncio.run_coroutine_threadsafe(stop_all(), self._loop)

            def on_stop_complete(fut):
                try:
                    fut.result()
                except Exception as e:
                    logging.error(f"Error during shutdown: {e}")
                finally:
                    if self._loop and self._loop.is_running():
                        self._loop.call_soon_threadsafe(self._loop.stop)

            stop_future.add_done_callback(on_stop_complete)
            self.wait(5000)
        except Exception as e:
            logging.error(f"Error scheduling shutdown: {e}")


def suggest_torrents(manager: ControlManager, filenames: List[str]):
    manager.torrents_suggested.emit(filenames)


async def find_another_daemon(filenames: List[str]) -> bool:
    try:
        async with ControlClient() as client:
            if filenames:
                await client.execute(partial(suggest_torrents, filenames=filenames))
        return True
    except RuntimeError:
        return False


def main():
    parser = argparse.ArgumentParser(description='BitTorrent Client - BizFiz (GUI)')
    parser.add_argument('--debug', action='store_true', help='Show debug messages')
    parser.add_argument('filenames', nargs='*', help='Torrent file names')
    args = parser.parse_args()

    if not args.debug:
        logging.disable(logging.INFO)

    app = QApplication(sys.argv)
    app.setWindowIcon(load_icon('logo'))

    # Show login window first
    login_window = LoginWindow()
    if login_window.exec() != QDialog.Accepted:
        return 0

    username = login_window.current_user

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        if loop.run_until_complete(find_another_daemon(args.filenames)):
            if not args.filenames:
                QMessageBox.critical(
                    None,
                    'Failed to start',
                    'Another program instance is already running'
                )
            return 0
    finally:
        loop.close()

    control_thread = ControlManagerThread()
    main_window = MainWindow(control_thread, username)

    control_thread.start()
    app.lastWindowClosed.connect(control_thread.stop)

    main_window.add_torrent_files(args.filenames)

    exit_code = app.exec()

    control_thread.stop()
    control_thread.wait(5000)

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
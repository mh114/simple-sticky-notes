import os
import sys

# Force XWayland backend, needs XCB
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import (
	QApplication, QWidget, QSystemTrayIcon, QLabel, QPushButton, QLineEdit,
	QMenu, QTextEdit, QVBoxLayout, QHBoxLayout, QMessageBox, QGraphicsDropShadowEffect, QSizeGrip, QStackedWidget
)
from PySide6.QtCore import Qt, QPoint, QEvent, QTimer, QSettings
from PySide6.QtGui import QIcon, QColor, QCursor, QTextCursor, QFont, QFontDatabase
from PySide6.QtDBus import QDBusInterface, QDBusConnection, QDBusMessage

APP_NAME = "simple-sticky-notes"
APP_ORG = "MHGames"
RESIZE_MARGIN = 24
SHADOW_COLOR = QColor(0, 0, 0, 50)
SHADOW_COLOR_FOCUSED = QColor(0, 0, 0, 100)


class StickyNote(QWidget):

	def __init__(self, parent = None, text = "New Note", title = "Note", app: StickyManager = None):
		super().__init__(parent)
		self.app = app
		self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
		self.setAttribute(Qt.WidgetAttribute.WA_MouseTracking, True)
		self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
		self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
		#self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
		#self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

		# Build the layout: main layout only has margins and a container layout, container has a drop-shadow
		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 12, 12)
		#layout.setSpacing(0)

		self.container = QWidget(self)
		self.container.setObjectName("container")
		self.container.setStyleSheet("""
			QWidget#container {
				background-color: #fff9c4;
				border: 1px solid #e0d88e;
				border-radius: 3px;
			}
		""")
		layout.addWidget(self.container)
		inner_layout = QVBoxLayout(self.container)
		inner_layout.setContentsMargins(3, 3, 3, 3)
		inner_layout.setSpacing(0)

		# Header has title label + stacked title editor and a delete-button
		self.header = QWidget(self.container)
		self.header.setObjectName("header")
		self.header.setMaximumHeight(32)
		self.header.setStyleSheet("QWidget#header { background-color: #10000000; border: none; border-radius: 3px; }")
		header_layout = QHBoxLayout(self.header)
		header_layout.setContentsMargins(6, 2, 4, 2)

		# Title label
		self.title = QLabel(title, self.header)
		self.title.setStyleSheet("color: #cc000000; font-weight: bold; border: none; background: transparent;")

		# Stacked title editor
		self.title_editor = QLineEdit(title, self.header)
		self.title_editor.setPlaceholderText("Note title...")
		self.title_editor.editingFinished.connect(self.on_title_edit_finished)
		self.editing_title = False

		# Stack of label + editor
		self.title_stack = QStackedWidget(self.header)
		self.title_stack.addWidget(self.title)
		self.title_stack.addWidget(self.title_editor)

		# Delete-button
		delete_button = QPushButton("×", self.header)
		#delete_button.setFixedSize(16, 16)
		delete_button.setStyleSheet("QPushButton { color: #cc000000; border: none; background: transparent; font-weight: bold; } QPushButton:hover { color: red; }")
		delete_button.setToolTip("Delete the note <b>(no undo!)</b>")
		delete_button.clicked.connect(self.close)

		header_layout.addWidget(self.title_stack)
		header_layout.addStretch()
		header_layout.addWidget(delete_button)

		# Main note text editor
		self.editor = QTextEdit(self.container)
		self.editor.setPlainText(text)
		self.editor.setStyleSheet("""
			QTextEdit {
				background-color: transparent;
				color: #2c2c2c;
				border: none;
			}
		""")

		# Footer has grip handle for resizing the note
		self.footer = QWidget(self.container)
		size_grip = QSizeGrip(self.footer)
		footer_layout = QHBoxLayout(self.footer)
		footer_layout.setContentsMargins(0, 0, 2, 2)
		footer_layout.addStretch()
		footer_layout.addWidget(size_grip)

		# Inner layout of header, editor and footer
		inner_layout.addWidget(self.header)
		inner_layout.addWidget(self.editor)
		inner_layout.addWidget(self.footer)
		self.resize(280, 220)

		# Monitor events on these widgets
		self.header.installEventFilter(self)
		self.editor.viewport().installEventFilter(self)
		self.title.installEventFilter(self)
		self.title_editor.installEventFilter(self)

		# Drop shadow on note container, because why not :D
		self.shadow = QGraphicsDropShadowEffect()
		self.shadow.setBlurRadius(15)
		self.shadow.setOffset(5, 5)
		self.shadow.setColor(SHADOW_COLOR)
		self.container.setGraphicsEffect(self.shadow)


	def on_title_edit_finished(self):
		if not self.editing_title:
			return
		self.title.setText(self.title_editor.text())
		self.title_stack.setCurrentWidget(self.title)
		print("FINISHED title edit")


	def send_to_front(self):
		if self.windowHandle():
			self.windowHandle().requestActivate()
		self.activateWindow()
		self.raise_()
		if self.app:
			self.app.note_was_sent_to_front(self)
		print("Raising " + str(self))

	def closeEvent(self, event: QCloseEvent):
		print("closing note...")
		if self.app:
			self.app.delete_note(self)
		super().closeEvent(event)


	def eventFilter(self, watched, event) -> bool:
		if event.type() == QEvent.Type.MouseButtonPress:
			# Send the note to front upon clicking anywhere
			self.send_to_front()

			# Drag from header/title to move note
			if event.button() == Qt.MouseButton.LeftButton:
				if watched in (self.header, self.title) and self.windowHandle():
					self.windowHandle().startSystemMove()
					return True

		# Double-click header/title to edit the title text
		elif event.type() == QEvent.Type.MouseButtonDblClick:
			if event.button() == Qt.MouseButton.LeftButton and watched in (self.title, self.header):
				title = self.title.text()
				self.editing_title = True
				self.title_editor.setText(title)
				self.title_stack.setCurrentWidget(self.title_editor)
				self.title_editor.setFocus()
				return True

		# Accept title edit when losing focus
		elif event.type() == QEvent.Type.FocusOut:
			if watched == self.title_editor and self.editing_title:
				self.title_editor.editingFinished.emit()
				return True

		# ..but cancel when pressing ESC
		elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
			if watched == self.title_editor and self.editing_title:
				self.editing_title = False
				self.title_stack.setCurrentWidget(self.title)
				return True

		return super().eventFilter(watched, event)


	def save(self, settings: QSettings):
		settings.setValue("geometry", self.saveGeometry())
		settings.setValue("text", self.editor.toPlainText())
		settings.setValue("title", self.title.text())

	def load(self, settings: QSettings):
		self.title.setText(settings.value("title"))
		geometry = settings.value("geometry")
		if geometry:
			self.restoreGeometry(geometry)


class StickyManager:
	def __init__(self):
		self.app = QApplication(sys.argv)
		#self.register_kwin_rules()

		# TODO: Offer to import from Linux Mint Sticky notes on 1st startup

		self.app.setDesktopFileName(APP_NAME)
		self.app.setApplicationName(APP_NAME)
		self.app.setQuitOnLastWindowClosed(False)

		# Font with emoji fallbacks
		# FIXME: Any way to get Noto or Twitter emoji working!?
		#print("font load: " + str(QFontDatabase.addApplicationFont("fonts/TwitterColorEmoji-SVGinOT.ttf")))
		QFontDatabase.setApplicationEmojiFontFamilies(["Twitter Color Emoji", "Segoe UI Emoji", "Noto Color Emoji"])
		app_font = QFont()
		#app_font.setFamilies(["Inter", "Noto Sans", "Noto Color Emoji"])
		app_font.setPointSize(14)
		#app_font.setPixelSize(16)
		self.app.setFont(app_font)

		self.settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "SimpleStickyNotes", "notes")

		self.notes = []
		self.are_notes_visible = True

		# Setup System Tray
		self.tray = QSystemTrayIcon(QIcon.fromTheme("note-new"))
		self.tray.setToolTip("(Simple) Sticky Notes")

		# Tray Context Menu
		menu = QMenu()
		menu.addAction("New Note", self.create_note)
		menu.addSeparator()
		menu.addAction("Quit", self.quit_app)
		self.tray.setContextMenu(menu)

		# Single click toggles all notes
		self.tray.activated.connect(self.on_tray_activated)
		self.tray.show()

		# Load saved notes or create initial note if nothing is loaded
		self.load_notes()
		if not self.notes:
			self.create_note()

	def on_tray_activated(self, reason):
		if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
			self.toggle_notes()

	def toggle_notes(self):
		self.are_notes_visible = not self.are_notes_visible
		for note in self.notes:
			note.setVisible(self.are_notes_visible)


	def create_note(self):
		# TODO: Better default text
		note = StickyNote(text = f"Note #{len(self.notes) + 1}", app = self)
		if not self.are_notes_visible:
			self.toggle_notes()

		note.show()
		self.notes.append(note)

	def delete_note(self, note: StickyNote):
		if note in self.notes:
			self.notes.remove(note)
			note.close()
			print("Deleted " + str(note))

	def run(self):
		sys.exit(self.app.exec())

	def quit_app(self):
		self.save_notes()
		self.app.quit()

	def save_notes(self):
		# FIXME: Should clear the settings, otherwise old notes are left lingering
		self.settings.beginWriteArray("notes")
		for i, note in enumerate(self.notes):
			self.settings.setArrayIndex(i)
			note.save(self.settings)
		self.settings.endArray()
		self.settings.sync()

	def load_notes(self):
		num_notes = self.settings.beginReadArray("notes")
		for i in range(num_notes):
			self.settings.setArrayIndex(i)
			text = self.settings.value("text")
			note = StickyNote(text = text, app = self)
			note.load(self.settings)

			note.show()
			self.notes.append(note)

		self.settings.endArray()

	def note_was_sent_to_front(self, note: StickyNote):
		if note not in self.notes:
			print("ERROR: Note not managed?")
			return
		# Set the topmost note to be last on the stack, so order remains when restoring
		self.notes.remove(note)
		self.notes.append(note)

	def register_kwin_rules(self):
		bus = QDBusConnection.sessionBus()
		kwin_interface = QDBusInterface("org.kde.KWin", "/KWin", "org.kde.KWin", bus)
		if kwin_interface.isValid() and bus.isConnected():
			# TODO: Offer to register KWin rules to hide notes from taskbar etc.
			print("KWIN dbus is OK!")
			reply = QMessageBox.question(None,
					"Add window rule",
					"Add KWin window rule to keep sticky notes from appearing in taskbar and task switcher?",
					QMessageBox.Yes | QMessageBox.No,
					QMessageBox.Yes)
			if reply == QMessageBox.Yes:
				# TODO: Add kwin rules, perhaps add them to [General] with UUID, so they are visible in KDE settings
				result = kwin_interface.call("reconfigure")
				print(f"Added window rules")
			else:
				print("Need to add window rule manually!")


if __name__ == "__main__":
	StickyManager().run()

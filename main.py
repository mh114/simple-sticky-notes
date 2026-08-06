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
				background-color: #ffe680;
				border: 1px solid #d4b537;
				border-radius: 4px;
			}

			QTextEdit, QWidget#footer {
				background-color: #50ffffff;
				color: #bf000000;
				border: none;
			}

			QWidget#header {
				background: transparent;
			}

			QWidget#header QLabel, QWidget#header QLineEdit {
				font-weight: 600;
				padding: 3px 0px 3px 0px;
			}

			QWidget#header QLineEdit {
				background: #50ffffff;
				color: black;
			}
		""")
		layout.addWidget(self.container)
		inner_layout = QVBoxLayout(self.container)
		inner_layout.setContentsMargins(1, 1, 1, 1)
		inner_layout.setSpacing(0)

		# Header has title label + stacked title editor and a delete-button
		self.header = QWidget(self.container)
		self.header.setObjectName("header")
		self.header.setMinimumHeight(36)
		self.header.setMaximumHeight(36)
		#self.header.setStyleSheet("QWidget#header { background: transparent; border: none; border-radius: 0px; }")
		header_layout = QHBoxLayout(self.header)
		header_layout.setContentsMargins(2, 2, 8, 2)

		# Title label
		self.title = QLabel(title, self.header)
		self.title.setStyleSheet("color: #a0000000; border: none; background: transparent;")

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
		delete_button.setToolTip("Delete the note<br><small><b>(no undo!)</b></small>")
		delete_button.clicked.connect(self.close)

		# Header layout
		header_layout.addWidget(self.title_stack)
		#header_layout.addStretch()
		header_layout.addWidget(delete_button)

		# Main note text editor
		self.editor = QTextEdit(self.container)
		self.editor.setPlainText(text)
		#self.editor.setStyleSheet("""
		#	QTextEdit {
		#		background-color: #50ffffff;
		#		color: #2c2c2c;
		#		border: none;
		#	}
		#""")

		# Footer has grip handle for resizing the note
		self.footer = QWidget(self.container)
		self.footer.setObjectName("footer")
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


	def send_to_front(self):
		if self.windowHandle():
			self.windowHandle().requestActivate()
		self.activateWindow()
		self.raise_()
		if self.app:
			self.app.note_was_sent_to_front(self)


	def closeEvent(self, event: QCloseEvent):
		# Confirm closing the note (also deletes it), unless we're quitting the app
		if self.app and not self.app.is_quitting:
			title = self.title.text()
			if title:
				title = f" titled <b>\"{title}\"</b>.."
			reply = QMessageBox.question(self,
					"Delete note?",
					f"Are you sure you want to delete note{title}?",
					QMessageBox.Yes | QMessageBox.No,
					QMessageBox.No)
			if reply == QMessageBox.No:
				event.ignore()
				return

			self.app.delete_note(self)
		super().closeEvent(event)


	def eventFilter(self, watched, event: QEvent) -> bool:
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
		self.is_quitting = False

		# Setup tray icon
		self.tray = QSystemTrayIcon(QIcon.fromTheme("note-new"))
		self.tray.setToolTip("(Simple) Sticky Notes")

		# Tray context menu
		menu = QMenu()
		menu.addAction("New Note", self.create_note)
		menu.addSeparator()
		menu.addAction("Quit", self.quit_app)
		self.tray.setContextMenu(menu)

		# Single click on tray icon toggles all notes
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
		# TODO: Perhaps should keep the last deleted note saved and allow undeleting it
		if note in self.notes:
			self.notes.remove(note)
			note.close()
			print("Deleted " + str(note))


	def run(self):
		sys.exit(self.app.exec())


	def quit_app(self):
		self.is_quitting = True
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
			print("ERROR: Note not managed!?")
			return

		# Set the topmost note to be last on the stack, so order remains when restoring
		if self.notes and self.notes[-1] != note:
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

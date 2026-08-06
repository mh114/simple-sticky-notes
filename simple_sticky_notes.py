import os
import sys

# Force XWayland backend, needs XCB
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon, QFont, QFontDatabase
from PySide6.QtDBus import QDBusInterface, QDBusConnection

from components.sticky_note import StickyNote

APP_NAME = "simple-sticky-notes"
APP_ORG = "MHGames"

""" Main application class """
class SimpleStickyNotes:
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

		# TODO: Use proper organization and app names
		self.settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "SimpleStickyNotes", "notes")

		self.notes: list[StickyNote] = []
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
			note.save_note_to(self.settings)
		self.settings.endArray()
		self.settings.sync()


	def load_notes(self):
		assert(len(self.notes) <= 0)
		num_notes = self.settings.beginReadArray("notes")
		for i in range(num_notes):
			self.settings.setArrayIndex(i)
			text = self.settings.value("text")
			title = self.settings.value("title")
			note = StickyNote(text = text, title = title, app = self)
			note.load_note_from(self.settings)

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
	SimpleStickyNotes().run()

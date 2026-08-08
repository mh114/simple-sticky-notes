import json
import os
import sys

# Force XWayland backend, needs XCB
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtCore import QCommandLineOption, QCommandLineParser, QSettings, QSize, QStandardPaths
from PySide6.QtGui import QFont, QFontDatabase, Qt
from PySide6.QtDBus import QDBusInterface, QDBusConnection

from components.icon_cache import IconCache
from components.sticky_note import StickyNote
from components.notes_protocol import NotesProtocol


APP_NAME_PATH = "simple-sticky-notes"
APP_NAME = "SimpleStickyNotes"
APP_DISPLAY_NAME = "(Simple) Sticky Notes"
APP_DESCRIPTION = "Simple sticky notes application."
APP_ORG = "MHGames"
APP_VERSION = "0.1"
NOTES_FILENAME = "notes.json"


class SimpleStickyNotes(NotesProtocol):
	""" Main application class """

	def __init__(self):
		self.app = QApplication(sys.argv)
		#self.register_kwin_rules()

		# TODO: Offer to import from Linux Mint Sticky notes on 1st startup

		self.app.setDesktopFileName(APP_NAME_PATH)
		self.app.setApplicationName(APP_NAME_PATH)
		self.app.setApplicationDisplayName(APP_DISPLAY_NAME)
		self.app.setApplicationVersion(APP_VERSION)
		self.app.setOrganizationName(APP_ORG)
		self.app.setQuitOnLastWindowClosed(False)

		self.process_command_line_args(self.app)

		#icon = QIcon.fromTheme("note-new")
		icon = IconCache.load_icon_svg("stickies.svg", size=QSize(64,64), scale=0.9, color=Qt.GlobalColor.white)
		self.app.setWindowIcon(icon)

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
		self._is_quitting = False

		# Setup tray icon
		self.tray = QSystemTrayIcon(icon)
		self.tray.setToolTip(self.app.applicationDisplayName())

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

		# Stealth-mode?
		if self.stealth_mode:
			self.set_notes_visible(False)


	def process_command_line_args(self, app: QApplication):
		parser = QCommandLineParser()
		parser.setApplicationDescription(APP_DESCRIPTION)
		parser.addHelpOption()
		parser.addVersionOption()

		parser.addOption(QCommandLineOption(["s", "stealth"], "Stealth-mode: hides notes on startup."))
		# TODO: Add option to add the KWin rules
		parser.process(app)

		self.stealth_mode = parser.isSet("stealth")


	def on_tray_activated(self, reason):
		if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
			# If hiding notes, autosave
			if self.are_notes_visible:
				self.save_notes()
			self.toggle_notes()


	def toggle_notes(self):
		self.set_notes_visible(not self.are_notes_visible)


	def set_notes_visible(self, visible: bool):
		self.are_notes_visible = visible
		for note in self.notes:
			note.setVisible(visible)


	def create_note(self):
		# TODO: Better default text
		note = StickyNote(text = f"Note #{len(self.notes) + 1}", app = self)
		if not self.are_notes_visible:
			self.toggle_notes()

		# Center on screen
		screen_geom = QApplication.primaryScreen().availableGeometry()
		note_geom = note.frameGeometry()
		center = screen_geom.center()
		note.move(center.x() - note_geom.width() / 2, center.y() - note_geom.height() / 2)

		note.show()
		self.notes.append(note)
		self.save_notes()


	def run(self):
		sys.exit(self.app.exec())


	def quit_app(self):
		self._is_quitting = True
		self.save_notes()
		self.app.quit()


	def save_notes(self):
		# Serialize notes to JSON
		config_dir = os.path.join(QStandardPaths.writableLocation(QStandardPaths.ConfigLocation), APP_NAME_PATH)
		notes_data = []
		for i, note in enumerate(self.notes):
			n_data = note.serialize()
			n_data["i"] = i # Store the index just in case, although Python should preserve order
			notes_data.append(n_data)

		notes_file = os.path.join(config_dir, NOTES_FILENAME)
		os.makedirs(config_dir, exist_ok=True)
		with open(notes_file, "wt", encoding="utf-8") as f:
			json.dump({ "notes": notes_data }, f, indent=4, ensure_ascii=False)
			print("Notes saved to: " + notes_file)


	def load_notes(self):
		assert(len(self.notes) <= 0)

		# Load notes from JSON
		notes_file = os.path.join(QStandardPaths.writableLocation(QStandardPaths.ConfigLocation), APP_NAME_PATH, NOTES_FILENAME)
		try:
			with open(notes_file, "rt", encoding="utf-8") as f:
				print("Loading notes from: " + notes_file)
				notes_data = json.load(f)["notes"]
				for note_data in notes_data:
					note = StickyNote.deserialize(note_data, app=self)
					if not self.stealth_mode:
						note.show()
					self.notes.append(note)
					print(f"- Loaded note #{note_data["i"]} titled '{note_data["title"]}'")

				if self.notes:
					self.notes[-1].send_to_front()
				
		except FileNotFoundError:
			return
		except BaseException as err:
			print(f"ERROR: Failed to load notes from {notes_file}, error: {err}")
			return


	# Implement NotesProtocol:
	#---------------------------
	def delete_note(self, note: StickyNote):
		# TODO: Perhaps should keep the last deleted note saved and allow undeleting it
		if note in self.notes:
			self.notes.remove(note)
			note.close()
			print("Deleted " + str(note))
			self.save_notes()


	def on_note_sent_to_front(self, note: StickyNote):
		if note not in self.notes:
			print("ERROR: Note not managed!?")
			return

		# Set the topmost note to be last on the stack, so order remains when restoring
		if self.notes and self.notes[-1] != note:
			self.notes.remove(note)
			self.notes.append(note)


	def is_quitting(self):
		return self._is_quitting
	#---------------------------


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

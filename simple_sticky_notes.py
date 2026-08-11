import json
import os
from pathlib import Path
import sys

# Force XWayland backend, needs XCB
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtCore import QCommandLineOption, QCommandLineParser, QSettings, QSize, QStandardPaths, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QIcon, Qt

from components.icon_cache import IconCache
from components.sticky_note import StickyNote
from components.notes_protocol import NotesProtocol
from components.kwin_window_rules import KWinWindowRules


APP_NAME_PATH = "simple-sticky-notes"
APP_NAME = "SimpleStickyNotes"
APP_DISPLAY_NAME = "(Simple) Sticky Notes"
APP_DESCRIPTION = "A quite simple sticky notes application."
APP_ORG = "MHGames"
APP_VERSION = "0.1"
NOTES_FILENAME = "notes.json"
SETTINGS_FILENAME = f"{APP_NAME_PATH}.conf"

FONTS_PATH = Path(__file__).parent / "fonts"


class SimpleStickyNotes(NotesProtocol):
	""" Main application class: manages the notes and app config + system tray icon """

	def __init__(self):
		self.app = QApplication(sys.argv)

		self.app.setDesktopFileName(APP_NAME_PATH)
		self.app.setApplicationName(APP_NAME_PATH)
		self.app.setApplicationDisplayName(APP_DISPLAY_NAME)
		self.app.setApplicationVersion(APP_VERSION)
		self.app.setOrganizationName(APP_ORG)
		self.app.setQuitOnLastWindowClosed(False)

		self.process_command_line_args(self.app)
		first_run = self.load_config()
		if first_run or self.check_window_rule:
			QTimer.singleShot(0, lambda: KWinWindowRules.check_kwin_window_rules(APP_DISPLAY_NAME, self))

		#icon = QIcon.fromTheme("note-new")
		icon = IconCache.load_icon_svg("stickies.svg", size=QSize(64,64), scale=0.9, color=Qt.GlobalColor.white)
		self.app.setWindowIcon(icon)

		self.setup_fonts()
		self.setup_tray_icon(icon)

		# Load saved notes or create initial note if nothing is loaded
		self.notes: list[StickyNote] = []
		self._are_notes_visible = True
		self._is_quitting = False
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
		parser.addOption(QCommandLineOption(["c", "check-window-rule"], "Check if KDE Window Rule exists and offer to add it, if it does not."))
		parser.process(app)

		self.stealth_mode = parser.isSet("stealth")
		self.check_window_rule = parser.isSet("check-window-rule")


	def setup_fonts(self):
		# Set app font and emoji font families. Use the bundled font by default.
		emoji_font = FONTS_PATH / "NotoColorEmoji.ttf"
		if emoji_font.exists():
			QFontDatabase.addApplicationFont(str(emoji_font))
		QFontDatabase.setApplicationEmojiFontFamilies(self.emoji_font_names)
		self.app_font = QFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
		if self.font_name and QFontDatabase.hasFamily(self.font_name):
			self.app_font.setFamily(self.font_name)
		if self.font_size > 0:
			self.app_font.setPointSize(self.font_size)

		# Monospace font
		self.monospace_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
		if self.monospace_font_name and QFontDatabase.hasFamily(self.monospace_font_name):
			self.monospace_font.setFamily(self.monospace_font_name)
		if self.font_size > 0:
			self.monospace_font.setPointSize(self.font_size)

		# Menu font (TODO: should use SystemFont.MenuFont, but not yet available)
		self.menu_font = QFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))


	def setup_tray_icon(self, icon: QIcon):
		# Setup tray icon
		self.tray = QSystemTrayIcon(icon)
		self.tray.setToolTip(self.app.applicationDisplayName())

		# Tray context menu
		menu = QMenu()
		menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.DocumentNew), "Add new note", self.create_note)
		menu.addSeparator()
		hide_on_startup_action = menu.addAction(IconCache.load_icon_svg("eye-slash-regular-full.svg", size=QSize(64,64), scale=0.9, color=Qt.GlobalColor.white), "Hide notes on startup", self.toggle_hide_on_startup)
		hide_on_startup_action.setCheckable(True)
		hide_on_startup_action.setChecked(self.settings.value("notes/hide_on_startup", False, type=bool))
		menu.addSeparator()
		menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.HelpAbout),"About this app...", self.on_about)
		menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.ApplicationExit), "Quit", self.quit_app)
		self.tray.setContextMenu(menu)

		# Single click on tray icon toggles all notes
		self.tray.activated.connect(self.on_tray_activated)
		self.tray.show()

		if hide_on_startup_action.isChecked():
			self.stealth_mode = True


	def on_tray_activated(self, reason):
		if reason == QSystemTrayIcon.ActivationReason.Trigger: # Left click
			# If hiding notes, autosave
			if self._are_notes_visible:
				self.save_notes()
			self.toggle_notes()


	def toggle_hide_on_startup(self):
		hide = not self.settings.value("notes/hide_on_startup", False, type=bool)
		self.settings.setValue("notes/hide_on_startup", hide)


	def on_about(self):
		QMessageBox.about(None,
					APP_DISPLAY_NAME,
					f"""
					<b>{APP_DISPLAY_NAME}</b> — v{APP_VERSION}<br>
					{APP_DESCRIPTION}<br>
					<a href="https://github.com/mh114/simple-sticky-notes">github.com/mh114/simple-sticky-notes</a><br><br>
					<span style="color: grey; font-size: 10pt;">
					Copyright &copy; 2026 Mika Halttunen (<a href="https://www.mhgames.org">www.mhgames.org</a>).
					</span>
					""")


	def toggle_notes(self):
		self.set_notes_visible(not self._are_notes_visible)


	def create_note(self):
		note = StickyNote(
					text = f"Note #{len(self.notes) + 1}",
					title = self.settings.value("notes/default_title"),
					app = self)
		if not self._are_notes_visible:
			self.toggle_notes()

		# Center on screen
		screen_geom = QApplication.primaryScreen().availableGeometry()
		note_geom = note.frameGeometry()
		center = screen_geom.center()
		note.move(center.x() - note_geom.width() / 2, center.y() - note_geom.height() / 2)

		note.show()
		self.notes.append(note)
		self.save_notes()


	def run(self) -> int:
		return self.app.exec()


	def quit_app(self):
		self._is_quitting = True
		self.save_notes(force_save=True)
		self.app.quit()


	def load_config(self) -> bool:
		first_run = False
		config_file = os.path.join(QStandardPaths.writableLocation(QStandardPaths.ConfigLocation), APP_NAME_PATH, SETTINGS_FILENAME)
		print("Config file: " + config_file)
		os.makedirs(os.path.dirname(config_file), exist_ok=True)
		self.settings = QSettings(config_file, QSettings.Format.IniFormat)

		if not self.settings.allKeys():
			first_run = True
			print("No settings, initialize defaults..")
			self.settings.setValue("fonts/font_size", -1)
			self.settings.setValue("fonts/font_name", "")
			self.settings.setValue("fonts/monospace_font_name", "")
			self.settings.setValue("fonts/emoji_font_names", ["Noto Color Emoji", "Segoe UI Emoji"])

			self.settings.setValue("notes/default_title", "Note")
			self.settings.setValue("notes/color_icon_name", "droplet") # "droplet|paintbrush|brush|palette"
			self.settings.setValue("notes/hide_on_startup", False)
			self.settings.sync()

		self.font_size = int(self.settings.value("fonts/font_size", -1))
		self.font_name = str(self.settings.value("fonts/font_name", ""))
		self.monospace_font_name = str(self.settings.value("fonts/monospace_font_name", ""))
		self.emoji_font_names = self.settings.value("fonts/emoji_font_names")
		return first_run


	def save_notes(self, force_save: bool = False):
		# Serialize notes to JSON
		if not force_save:
			# Check if we actually need to save
			need_to_save = False
			for note in self.notes:
				if note.is_dirty:
					need_to_save = True
					break
			if not need_to_save:
				return

		config_dir = os.path.join(QStandardPaths.writableLocation(QStandardPaths.ConfigLocation), APP_NAME_PATH)
		notes_data = []
		for i, note in enumerate(self.notes):
			n_data = note.serialize()
			note.is_dirty = False
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
					#print(f"- Loaded note #{note_data["i"]} titled '{note_data["title"]}'")

				if self.notes:
					self.notes[-1].send_to_front()
				
		except FileNotFoundError:
			return
		except BaseException as err:
			print(f"ERROR: Failed to load notes from {notes_file}, error: {err}")
			return


	# Implement NotesProtocol:
	#---------------------------
	def set_notes_visible(self, visible: bool):
		self._are_notes_visible = visible
		for note in self.notes:
			note.setVisible(visible)


	def are_notes_visible(self) -> bool:
		return self._are_notes_visible


	def delete_note(self, note: StickyNote):
		# TODO: Perhaps should keep the last deleted note saved and allow undeleting it
		if note in self.notes:
			self.notes.remove(note)
			note.close()
			print("Deleted " + str(note))
			self.save_notes(force_save=True)


	def on_note_sent_to_front(self, note: StickyNote):
		if note not in self.notes:
			print("ERROR: Note not managed!?")
			return

		# Set the topmost note to be last on the stack, so order remains when restoring
		note.is_dirty = True
		if self.notes and self.notes[-1] != note:
			self.notes.remove(note)
			self.notes.append(note)


	def is_quitting(self):
		return self._is_quitting


	def get_settings(self) -> QSettings:
		return self.settings


	def get_app_font(self) -> QFont:
		return self.app_font

	def get_monospace_font(self) -> QFont:
		return self.monospace_font

	def get_menu_font(self) -> QFont:
		return self.menu_font
	#---------------------------



if __name__ == "__main__":
	sys.exit(SimpleStickyNotes().run())

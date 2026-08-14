# (Simple) Sticky Notes - Copyright (c) 2026 Mika Halttunen (https://www.mhgames.org)
# https://github.com/mh114/simple-sticky-notes
# Licensed under the MIT-license.

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Force XWayland backend, needs XCB libxcb-cursor library
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtCore import (
	QCommandLineOption,
	QCommandLineParser,
	QSettings,
	QSize,
	QStandardPaths,
	QTimer,
)
from PySide6.QtGui import QFont, QFontDatabase, QIcon, Qt
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from components.icon_cache import IconCache
from components.kwin_window_rules import KWinWindowRules
from components.notes_protocol import NotesProtocol, PlatformType
from components.sticky_note import StickyNote

#from components.notes_importer import NotesImporter


APP_NAME_PATH = "simple-sticky-notes"
APP_NAME = "SimpleStickyNotes"
APP_DISPLAY_NAME = "(Simple) Sticky Notes"
APP_DESCRIPTION = "A quite simple sticky notes application."
APP_ORG = "MHGames"
APP_VERSION = "0.5.0"
NOTES_FILENAME = "notes.json"
SETTINGS_FILENAME = f"{APP_NAME_PATH}.conf"

FONTS_PATH = Path(__file__).parent / "fonts"


class SimpleStickyNotes(NotesProtocol):
	""" Main application class: manages the notes and app config + system tray icon """

	def __init__(self):
		self.app = QApplication(sys.argv)
		self._platform_type = None
		print(f"Running on {self.get_platform_type()}")

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
		icon = IconCache.load_icon_svg("icon-mh.svg", size=QSize(64,64), scale=1.0)
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
		parser.addOption(QCommandLineOption(["i", "install-desktop-file"], f"Generates a .desktop file so that '{APP_DISPLAY_NAME}' appears in the system application launcher."))
		#parser.addOption(QCommandLineOption(["import-from-mint-sticky"], "Import notes from Linux Mint Sticky."))
		parser.process(app)

		self.stealth_mode = parser.isSet("stealth")
		self.check_window_rule = parser.isSet("check-window-rule")
		if parser.isSet("install-desktop-file"):
			self._install_desktop_file()
		#if parser.isSet("import-from-mint-sticky"):
		# 	NotesImporter.import_mint_sticky_notes()
		# 	sys.exit(0)


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
		menu.addAction("Toggle notes", lambda: self.on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger))
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
		parent = None
		if self.notes:
			parent = self.notes[-1]
			if not self._are_notes_visible:
				self.set_notes_visible(True)

		QMessageBox.about(parent,
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

			self.settings.setValue("notes/num_backups", 10)
			self.settings.setValue("notes/default_title", "Note")
			self.settings.setValue("notes/color_icon_name", "droplet") # "droplet|paintbrush|brush|palette"
			self.settings.setValue("notes/color_saturation", "0.55")
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
			self._take_notes_backup(notes_file)
			with open(notes_file, "rt", encoding="utf-8") as f:
				print("Loading notes from: " + notes_file)
				notes_data = json.load(f)["notes"]
				for note_data in notes_data:
					note = StickyNote.deserialize(note_data, app=self)
					if not self.stealth_mode:
						note.show()
					else:
						# In stealth mode we do this trickery to lessen the impact when all notes are toggled visible
						note.setWindowOpacity(0.0)
						note.show()
						note.showMinimized()
					
					self.notes.append(note)
					#print(f"- Loaded note #{note_data["i"]} titled '{note_data["title"]}'")
					
				if self.notes:
					self.notes[-1].send_to_front()
				
		except FileNotFoundError:
			return
		except OSError as err:
			print(f"ERROR: Failed to load notes from {notes_file}, error: {err}")
			return


	# Implement NotesProtocol:
	#---------------------------
	def set_notes_visible(self, visible: bool):
		self._are_notes_visible = visible
		for note in self.notes:
			# NOTE: Several ways of hiding/restoring the note windows
			# note.setVisible(visible)  # <-- 1. this gets very slow for dozens of notes/windows

			# 2. The following method works, but causes slight flicker after restoring the notes.
			# We mask the flicker by setting opacity to zero for some milliseconds before restoring to 100%
			if not visible:
				note.showMinimized()
			else:
				note.setWindowOpacity(0.0)
				note.showNormal()

		if visible and self.notes:
			def restore_note_opacity():
				for note in self.notes:
					note.setWindowOpacity(1.0)
			
			QTimer.singleShot(10, restore_note_opacity)
			if self.get_platform_type() == PlatformType.NativeX11:
				for note in self.notes:
					note.activateWindow()
			else:
				self.notes[-1].activateWindow()


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
		if self.notes and self.notes[-1] != note:
			note.is_dirty = True
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


	def get_platform_type(self) -> PlatformType:
		if not self._platform_type:
			platform = os.environ.get("QT_QPA_PLATFORM", "")
			wayland_env_found = os.environ.get("XDG_SESSION_TYPE") == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
			if platform == "xcb":
				if wayland_env_found:
					self._platform_type = PlatformType.XWayland
				else:
					self._platform_type = PlatformType.NativeX11
			elif platform == "wayland":
				self._platform_type = PlatformType.Wayland
			else:
				self._platform_type = PlatformType.XWayland if wayland_env_found else PlatformType.NativeX11

		return self._platform_type
	#---------------------------


	def _take_notes_backup(self, notes_file: str):
		# Keep a few backups and rotate them: oldest gets overwritten first
		num_backups = int(self.settings.value("notes/num_backups", 10))
		if num_backups <= 0:
			print("Automatic backups are disabled by configuration.")
			return
		
		notes_path = Path(notes_file)
		if not notes_path.exists():
			return # Nothing to backup yet

		num = 0
		while num < num_backups:
			num += 1
			backup_file = notes_path.with_name(f"{notes_path.name}.{num}.bak")
			if not backup_file.exists():
				break
		if backup_file.exists():
			# We've reached the number of backups to keep, overwrite the oldest
			oldest_file: Path = None
			oldest_ts: int = -1
			for i in range(num_backups):
				file = notes_path.with_name(f"{notes_path.name}.{i + 1}.bak")
				modified_ts = file.stat().st_mtime_ns
				if modified_ts < oldest_ts or not oldest_file:
					oldest_file = file
					oldest_ts = modified_ts
			backup_file = oldest_file

		print("Taking a backup to:", backup_file)
		shutil.copy(notes_file, str(backup_file))


	def _install_desktop_file(self):
		app_path = Path(__file__).parent.resolve()
		main_script_path = Path(__file__).resolve()

		# .venv or system Python?
		if sys.prefix != sys.base_prefix:
			python = app_path / ".venv" / "bin" / "python3" # .venv
		else:
			python = "python3"

		desktop_files_path = Path.home() / ".local" / "share" / "applications"
		desktop_files_path.mkdir(parents=True, exist_ok=True)
		desktop_file = desktop_files_path / f"{APP_NAME_PATH}.desktop"

		desktop_file.write_text(f"""[Desktop Entry]
Type=Application
Version=1.5
Name={APP_DISPLAY_NAME}
GenericName=Sticky notes application
Comment={APP_DESCRIPTION}
Exec={python} {main_script_path}
Path={app_path}
Icon={app_path / "assets" / "icon-mh.svg"}
Terminal=false
Categories=Utility;TextEditor;
Keywords=sticky;note;notes;
StartupWMClass={APP_NAME_PATH}
""")

		print(f"Generated .desktop file to '{desktop_file}'")
		print("Updating desktop database..")
		sys.exit(subprocess.run(["update-desktop-database", str(desktop_files_path)], check=False).returncode)



if __name__ == "__main__":
	sys.exit(SimpleStickyNotes().run())

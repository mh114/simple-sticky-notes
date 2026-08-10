from configparser import ConfigParser
from pathlib import Path
import shutil
import uuid

from PySide6.QtWidgets import QMessageBox
from PySide6.QtDBus import QDBusInterface, QDBusConnection

from components.notes_protocol import NotesProtocol


class KWinWindowRules:
	"""
	Helper class to handle KWin window rules
	"""

	def check_kwin_window_rules(app_name: str, app: NotesProtocol):
		kwin_config = Path.home() / ".config" / "kwinrc"
		if not kwin_config.exists():
			# kwinrc does not exists, probably not running KDE -> can't do anything, bail out
			print("KWin config (~/.config/kwinrc) not found, probably not running KDE?")
			return

		# Detect if the KWin rules already include our rule
		kwin_rules_file = kwin_config.with_name("kwinrulesrc")
		if kwin_rules_file.exists():
			config_text = kwin_rules_file.read_text(encoding="utf-8")
			if "SimpleStickyNotes" in config_text and "simple-sticky-notes" in config_text:
				print("Window Rule seems to be already in place, no need to do anything.")
				return
		
		bus = QDBusConnection.sessionBus()
		kwin_interface = QDBusInterface("org.kde.KWin", "/KWin", "org.kde.KWin", bus)
		if kwin_interface.isValid() and bus.isConnected():
			# Offer to register KWin rules to hide notes from taskbar etc.
			reply = QMessageBox.question(None,
					"Add KDE Window Rule",
					f"""
					Thanks for trying <b>{app_name}</b>!<br><br>
					For proper user experience, the sticky notes should not appear in taskbar and task switcher.
					KDE Window Rules can be used to achieve this.<br><br>
					Do you want to add KWin window rule to keep sticky notes from appearing in taskbar and task switcher? (This can be done manually, too.)
					""",
					QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
			if reply == QMessageBox.Yes:
				KWinWindowRules._register_kwin_rule(kwin_interface, app)
			else:
				print("(Probably) need to add window rule manually!")


	def _register_kwin_rule(kwin_interface: QDBusInterface, app: NotesProtocol):
		GENERAL_SECTION = "General"
		kwin_rules_file = Path.home() / ".config" / "kwinrulesrc"

		try:
			rules_config = ConfigParser()
			rules_config.optionxform = lambda opt: opt  # Keep option names as is, by default transforms to lower-case

			if not kwin_rules_file.exists():
				# FIXME: No rules file, probably no rules configured. Create one.
				raise NotImplementedError("Need to create a new rules file!")
			else:
				# Need to add a new rule to the existing config file. We want to have it under [General]-section,
				# so that it will be user visible in KDE Window Rule -settings.

				# First make a backup, abort if backup already exists or cannot be made
				rules_backup_file = kwin_rules_file.with_name("kwinrulesrc.bak")
				if rules_backup_file.exists():
					raise FileExistsError(f"KWin rules file backup already exists at {rules_backup_file}! Aborting rule addition for safety.")
				shutil.copy2(str(kwin_rules_file), str(rules_backup_file))
				if not rules_backup_file.exists() or rules_backup_file.stat().st_size != kwin_rules_file.stat().st_size:
					raise FileNotFoundError(f"Failed to make backup of {kwin_rules_file}! Aborting rule addition for safety.")

				# Read the config file and update the [General]-section
				if not rules_config.read(kwin_rules_file, encoding="utf-8"):
					raise IOError(f"Cannot parse {kwin_rules_file}!")

				if GENERAL_SECTION not in rules_config:
					rules_config[GENERAL_SECTION] = {}

				# Generate a new UUID for the new rule (mixing indices and UUIDs should work)
				new_uuid = str(uuid.uuid4())

				rules_count = rules_config[GENERAL_SECTION].getint("count", 0)
				current_rules = rules_config[GENERAL_SECTION].get("rules", "")
				if not current_rules:
					assert(rules_count == 0)
					new_rules = new_uuid
				else:
					new_rules = f"{current_rules},{new_uuid}"

				rules_config[GENERAL_SECTION]["count"] = str(rules_count + 1)
				rules_config[GENERAL_SECTION]["rules"] = new_rules

				# Create the new rule section
				rules_config[new_uuid] = {
					"Description": "SimpleStickyNotes",
					"desktops": "\\\\0",
					"desktopsrule": "2",
					"skippager": "true",
					"skippagerrule": "2",
					"skipswitcher": "true",
					"skipswitcherrule": "2",
					"skiptaskbar": "true",
					"skiptaskbarrule": "2",
					"title": "StickyNote:",
					"titlematch": "2",
					"wmclass": "simple-sticky-notes",
					"wmclassmatch": "1",
				}

				# Save changes
				with open(str(kwin_rules_file), "wt", encoding="utf-8") as file:
					rules_config.write(file, False)

				# Hide notes temporarily
				notes_were_visible = app.are_notes_visible()
				if notes_were_visible:
					app.set_notes_visible(False)

				# Signal KWin to reload the rules
				kwin_interface.call("reconfigure")
				print("Added a new window rule.")
				QMessageBox.information(None, "Window Rule added", "Successfully added a new window rule for the sticky notes. Please restart the app if it does not immediately work.")

				# Restore notes
				if notes_were_visible:
					app.set_notes_visible(True)


		except BaseException as ex:
			msg = f"Failed to register KWin rule, need to add manually!\n\nError: {ex}"
			print("ERROR: " + msg)
			QMessageBox.warning(None, "Failed to register window rule", msg)
			return


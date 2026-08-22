# (Simple) Sticky Notes - Copyright (c) 2026 Mika Halttunen (https://www.mhgames.org)
# https://github.com/mh114/simple-sticky-notes
# Licensed under the MIT-license.

from PySide6.QtCore import ClassInfo, QObject, Slot
from PySide6.QtDBus import QDBusConnection

from components.notes_protocol import NotesProtocol

SERVICE_NAME: str = "org.mhgames.SimpleStickyNotes"
SERVICE_PATH: str = "/SimpleStickyNotes"


@ClassInfo({ "D-Bus Interface": SERVICE_NAME })
class NotesDBusInterface(QObject):
	def __init__(self, app: NotesProtocol):
		super().__init__()
		self.app = app
		self.ready = False


	def set_ready(self):
		self.ready = True


	@Slot()
	def toggleNotes(self):
		if self.ready:
			self.app.set_notes_visible(not self.app.are_notes_visible())

	@Slot()
	def hideNotes(self):
		if self.ready:
			self.app.set_notes_visible(False)

	@Slot()
	def showNotes(self):
		if self.ready:
			self.app.set_notes_visible(True)


	@classmethod
	def create_dbus_interface(cls, app: NotesProtocol) -> "NotesDBusInterface":
		session_bus = QDBusConnection.sessionBus()
		if not session_bus.registerService(SERVICE_NAME):
			# Already running
			return None
		
		dbus_interface = cls(app)
		if session_bus.registerObject(SERVICE_PATH, dbus_interface, QDBusConnection.RegisterOption.ExportAllSlots):
			print(f"DBus interface is up at {SERVICE_NAME}{SERVICE_PATH}")

		return dbus_interface


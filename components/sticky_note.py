# (Simple) Sticky Notes - Copyright (c) 2026 Mika Halttunen (https://www.mhgames.org)
# https://github.com/mh114/simple-sticky-notes
# Licensed under the MIT-license.

import sys

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QCloseEvent, QColor, QIcon, QResizeEvent
from PySide6.QtWidgets import (
	QGraphicsDropShadowEffect,
	QHBoxLayout,
	QLineEdit,
	QMenu,
	QMessageBox,
	QPushButton,
	QSizeGrip,
	QStackedWidget,
	QToolButton,
	QVBoxLayout,
	QWidget,
)

from components.color_picker_menu import ColorPickerMenu
from components.ellipsis_label import EllipsisLabel
from components.icon_cache import IconCache
from components.note_editor import NoteEditor
from components.notes_protocol import NotesProtocol, PlatformType

SHADOW_COLOR = QColor(0, 0, 0, 50)
SHADOW_COLOR_FOCUSED = QColor(0, 0, 0, 100)
ICON_SIZE = QSize(20, 20)
ICON_OPACITY = 0.6
TOOL_BUTTON_SIZE = QSize(28, 28)

MENU_STYLE_QSS = \
	"""
	QMenu {
		background-color: rgba(64, 64, 64, 0.9);
		border: 1px solid gray;
		border-radius: 0px;
		color: white;
		padding: 3px;
	}
	QMenu::item {
		background-color: transparent;
		border-radius: 4px;
		padding: 5px;
	}
	QMenu::item:selected {
		background-color: rgba(0, 0, 0, 0.4);
	}
	QMenu::item:disabled {
		color: grey;
	}
	QMenu::icon {
		margin: 4px;
	}
	"""

class StickyNote(QWidget):
	def __init__(self, parent = None, text = "New Note", title: str|None = None, font_size_offset: int = 0, app: NotesProtocol = None):
		super().__init__(parent)
		self.app = app
		self.setFont(app.get_app_font())

		# Choose window flags depending on platform: on (X)Wayland we need Dialog, on X11 we can use Tool
		if app.get_platform_type() == PlatformType.NativeX11:
			self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
		else:
			self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)


		self.setAttribute(Qt.WidgetAttribute.WA_MouseTracking, True)
		self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
		self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
		self.setProperty("_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_UTILITY")
		if title == None:
			title = "Note"

		# Running inside .venv?
		running_in_venv = sys.prefix != sys.base_prefix

		# Build the layout: main layout only has margins and a container layout, container has a drop-shadow
		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 12, 12)

		self.change_color(*ColorPickerMenu.default_color())
		self.is_dirty = True

		self.container = QWidget(self)
		self.container.setObjectName("container")
		self.container.setStyleSheet("""
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

			QLabel#title {
				color: #a0000000;
				border: none;
				background: transparent;
			}

			QToolButton, QPushButton {
				border: none;
				background: transparent;
				padding: 0px;
				border-radius: 3px;
			}
			QToolButton:hover, QPushButton:hover {
				background-color: rgba(0, 0, 0, 0.2);
			}
			QToolButton::menu-indicator {
				image: none;
			}
		""")
		layout.addWidget(self.container)
		inner_layout = QVBoxLayout(self.container)
		inner_layout.setContentsMargins(1, 1, 1, 1)
		inner_layout.setSpacing(0)

		# Main note text editor
		self.editor = NoteEditor(text, self.container, font_size_offset, app)
		self.editor.textChanged.connect(self.on_text_changed)

		# Header has title label + stacked title editor and some tool buttons
		self.header = QWidget(self.container)
		self.header.setObjectName("header")
		self.header.setMinimumHeight(36)
		self.header.setMaximumHeight(36)
		header_layout = QHBoxLayout(self.header)
		header_layout.setContentsMargins(4, 2, 4, 2)
		header_layout.setSpacing(0)

		# Title label (uses ellipsis)
		self.title = EllipsisLabel(title, self.header)
		self.title.setFont(app.get_app_font())
		self.title.setObjectName("title")
		self.setWindowTitle(f"StickyNote: {title}")

		# Stacked title editor
		self.title_editor = QLineEdit(title, self.header)
		self.title_editor.setFont(app.get_app_font())
		self.title_editor.setPlaceholderText("Note title...")
		self.title_editor.editingFinished.connect(self.on_title_edit_finished)
		self.editing_title = False

		# Stack of label + editor
		self.title_stack = QStackedWidget(self.header)
		self.title_stack.addWidget(self.title)
		self.title_stack.addWidget(self.title_editor)

		# Color picker -button
		match self.app.get_settings().value("notes/color_icon_name", "droplet"):
			case "paintbrush":
				color_icon_name = "paintbrush-solid-full.svg"
			case "brush":
				color_icon_name = "brush-solid-full.svg"
			case "palette":
				color_icon_name = "palette-solid-full.svg"
			case _:
				color_icon_name = "droplet-solid-full.svg"

		color_button = QToolButton(self.header, popupMode=QToolButton.ToolButtonPopupMode.InstantPopup)
		color_button.setToolTip("Change note color")
		color_button.setIcon(IconCache.load_icon_svg(color_icon_name, size=ICON_SIZE, opacity=ICON_OPACITY))
		color_button.setIconSize(ICON_SIZE)
		color_button.setFixedSize(TOOL_BUTTON_SIZE)
		color_menu = ColorPickerMenu(parent = color_button)
		color_menu.color_picked.connect(self.change_color)
		color_button.setMenu(color_menu)
		self.color_menu = color_menu

		# Font-button
		font_button = QToolButton(self.header, popupMode=QToolButton.ToolButtonPopupMode.InstantPopup)
		font_button.setToolTip("Adjust text formatting")
		font_button.setIcon(IconCache.load_icon_svg("fonts.svg", size=ICON_SIZE, scale=1.2, opacity=ICON_OPACITY))
		font_button.setIconSize(ICON_SIZE)
		font_button.setFixedSize(TOOL_BUTTON_SIZE)
		font_menu = QMenu(parent = font_button)
		font_menu.setFont(app.get_menu_font())
		font_menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.FormatTextBold), "Bold", self.editor.toggle_bold, shortcut="Ctrl+B")
		font_menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.FormatTextItalic), "Italic", self.editor.toggle_italic, shortcut="Ctrl+I")
		font_menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.FormatTextStrikethrough), "Strikethrough", self.editor.toggle_strikethrough, shortcut="Shift+Ctrl+X")
		font_menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.FormatTextUnderline), "Underline", self.editor.toggle_underline, shortcut="Ctrl+U")
		font_menu.addAction("Clear formatting", self.editor.clear_formatting, shortcut="Shift+Ctrl+F")
		font_menu.addSeparator()
		self.monospace_menu_action = font_menu.addAction("Fixed-width font", self.editor.toggle_monospace)
		self.monospace_menu_action.setCheckable(True)
		font_menu.addSeparator()
		font_menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.ZoomIn), "Larger font", self.editor.zoom_in, shortcut="Ctrl++")
		font_menu.addAction(QIcon.fromTheme(QIcon.ThemeIcon.ZoomOut), "Smaller font", self.editor.zoom_out, shortcut="Ctrl+-")
		font_menu.addAction("Reset font size", lambda: self.editor.set_font_size_offset(0), shortcut="Ctrl+0")
		font_button.setMenu(font_menu)
		self.font_menu = font_menu

		# If inside .venv, the menu style can look bad because it doesn't follow the system theme. Restyle it.
		if running_in_venv:
			self.font_menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
			self.font_menu.setStyleSheet(MENU_STYLE_QSS)

		# Delete-button
		delete_button = QPushButton("", self.header)
		delete_button.setIcon(IconCache.load_icon_svg("delete-note-mh.svg", size=ICON_SIZE, scale=0.9, opacity=ICON_OPACITY))
		delete_button.setIconSize(ICON_SIZE)
		delete_button.setFixedSize(TOOL_BUTTON_SIZE)
		delete_button.setToolTip("Delete the note<br><small><b>(no undo!)</b></small>")
		delete_button.clicked.connect(self.close)

		# Header layout
		header_layout.addWidget(self.title_stack)
		# header_layout.addStretch()
		header_layout.addWidget(font_button)
		header_layout.addWidget(color_button)
		header_layout.addWidget(delete_button)

		# Footer has grip handle for resizing the note
		self.footer = QWidget(self.container)
		self.footer.setObjectName("footer")
		size_grip = QSizeGrip(self.footer)
		size_grip.setStyleSheet(f"QSizeGrip {{ image: {IconCache.get_icon_qss_url("size-grip-mh.svg")}; }}")
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
		self.editor.installEventFilter(self)
		self.title.installEventFilter(self)
		self.title_editor.installEventFilter(self)

		# Drop shadow on note container, because why not :D
		self.shadow = QGraphicsDropShadowEffect()
		self.shadow.setBlurRadius(15)
		self.shadow.setOffset(5, 5)
		self.shadow.setColor(SHADOW_COLOR)
		self.container.setGraphicsEffect(self.shadow)


	def change_color(self, color: QColor, index: int = -1):
		self.color_index = index
		self.is_dirty = True
		darker = color.darker(125)
		self.setStyleSheet(f"""
			QWidget#container {{
				background-color: {color.name(QColor.NameFormat.HexRgb)};
				border: 1px solid {darker.name(QColor.NameFormat.HexRgb)};
				border-radius: 4px;
			}}
		""")


	def on_text_changed(self):
		self.is_dirty = True


	def on_title_edit_finished(self):
		if not self.editing_title:
			return
		self.title.setText(self.title_editor.text())
		self.title_stack.setCurrentWidget(self.title)
		self.setWindowTitle(f"StickyNote: {self.title_editor.text()}")
		self.is_dirty = True


	def send_to_front(self):
		self.activateWindow()
		self.raise_()
		if self.windowHandle():
			self.windowHandle().raise_()
			self.windowHandle().requestActivate()

		if self.app:
			#print("sending to front: " + self.title.text())
			self.app.on_note_sent_to_front(self)


	def closeEvent(self, event: QCloseEvent):
		# Confirm closing the note (also deletes it), unless we're quitting the app
		if self.app and not self.app.is_quitting():
			title = self.title.text()
			if title:
				title = f" titled <b>\"{title}\"</b>.."
			reply = QMessageBox.question(self,
					"Delete note",
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
			if event.button() == Qt.MouseButton.LeftButton \
				and watched in (self.header, self.title) and self.windowHandle():
					self.windowHandle().startSystemMove()
					self.is_dirty = True
					return True

		# Double-click title to edit the title text
		elif event.type() == QEvent.Type.MouseButtonDblClick \
			and event.button() == Qt.MouseButton.LeftButton and watched == self.title:
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
			elif watched == self.editor and not self.font_menu.isVisible() and not self.color_menu.isVisible():
				self.editor.clear_selection()

		# ..but cancel when pressing ESC
		elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape \
			and watched == self.title_editor and self.editing_title:
				self.editing_title = False
				self.title_stack.setCurrentWidget(self.title)
				return True

		return super().eventFilter(watched, event)


	def resizeEvent(self, event: QResizeEvent):
		self.is_dirty = event.oldSize() != event.size()
		return super().resizeEvent(event)


	def serialize(self) -> dict[str, int|str]:
		geom = self.geometry()
		data: dict[str, int|str] = {
			"text": self.editor.get_rich_text(),
			"title": self.title.text(),
			"x": geom.x(),
			"y": geom.y(),
			"w": geom.width(),
			"h": geom.height(),
			"color": self.color_index,
			"font_size": self.editor.font_size_offset,
			"fixed_width": self.editor.is_monospace,
		}
		return data


	@classmethod
	def deserialize(cls, data: dict[str, int|str], app: NotesProtocol) -> "StickyNote":
		x = int(data["x"])
		y = int(data["y"])
		w = int(data["w"])
		h = int(data["h"])
		text = str(data["text"])
		title = str(data["title"])
		font_size = int(data.get("font_size", 0))
		color_index = int(data.get("color", -1))
		monospace = bool(data.get("fixed_width", False))

		note = cls(text = text, title = title, app = app, font_size_offset = font_size)
		note.move(x, y)
		note.resize(w, h)

		if monospace:
			note.editor.set_monospace(True)
			note.monospace_menu_action.setChecked(True)

		if color_index >= 0:
			note.change_color(note.color_menu.get_color_for_index(color_index), color_index)

		note.is_dirty = False
		return note
		

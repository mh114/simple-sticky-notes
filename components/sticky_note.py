from PySide6.QtWidgets import (
	QToolButton, QWidget, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout,
	QMessageBox, QGraphicsDropShadowEffect, QSizeGrip, QStackedWidget
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QCloseEvent, QIcon

from components.color_picker_menu import ColorPickerMenu
from components.ellipsis_label import EllipsisLabel
from components.note_editor import NoteEditor

SHADOW_COLOR = QColor(0, 0, 0, 50)
SHADOW_COLOR_FOCUSED = QColor(0, 0, 0, 100)


class StickyNote(QWidget):
	def __init__(self, parent = None, text = "New Note", title = "Note", app: SimpleStickyNotes = None): # type: ignore
		super().__init__(parent)
		self.app = app
		self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
		self.setAttribute(Qt.WidgetAttribute.WA_MouseTracking, True)
		self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
		self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

		# Build the layout: main layout only has margins and a container layout, container has a drop-shadow
		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 12, 12)
		#layout.setSpacing(0)

		self.change_color(*ColorPickerMenu.default_color())

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

			QPushButton#deleteButton {
				color: #cc000000;
				border: none;
				background: transparent;
				font-weight: bold;
			}
			QPushButton#deleteButton:hover {
				color: red;
				font-size: 16pt;
			}
		""")
		layout.addWidget(self.container)
		inner_layout = QVBoxLayout(self.container)
		inner_layout.setContentsMargins(1, 1, 1, 1)
		inner_layout.setSpacing(0)

		# Header has title label + stacked title editor and a delete-button + color picker button
		self.header = QWidget(self.container)
		self.header.setObjectName("header")
		self.header.setMinimumHeight(36)
		self.header.setMaximumHeight(36)
		#self.header.setStyleSheet("QWidget#header { background: transparent; border: none; border-radius: 0px; }")
		header_layout = QHBoxLayout(self.header)
		header_layout.setContentsMargins(4, 2, 6, 2)

		# Title label (uses ellipsis)
		self.title = EllipsisLabel(title, self.header)
		self.title.setObjectName("title")

		# Stacked title editor
		self.title_editor = QLineEdit(title, self.header)
		self.title_editor.setPlaceholderText("Note title...")
		self.title_editor.editingFinished.connect(self.on_title_edit_finished)
		self.editing_title = False

		# Stack of label + editor
		self.title_stack = QStackedWidget(self.header)
		self.title_stack.addWidget(self.title)
		self.title_stack.addWidget(self.title_editor)

		# Color picker -button
		color_button = QToolButton(self.header, popupMode=QToolButton.ToolButtonPopupMode.InstantPopup)
		color_button.setToolTip("Change note color")
		color_button.setIcon(QIcon.fromTheme("draw-brush", QIcon.fromTheme("format-fill-color")))
		color_button.setFixedSize(24, 24)
		color_menu = ColorPickerMenu(parent = color_button)
		color_menu.color_picked.connect(self.change_color)
		color_button.setMenu(color_menu)
		color_button.setStyleSheet("""
			QToolButton {
				border: none;
				background: transparent;
				padding: 2px;
				border-radius: 3px;
			}
			QToolButton:hover {
				background-color: rgba(0, 0, 0, 0.2);
			}
			QToolButton::menu-indicator {
				image: none;
			}
		""")

		# Delete-button
		delete_button = QPushButton("×", self.header)
		delete_button.setObjectName("deleteButton")
		delete_button.setFixedSize(20, 20)
		delete_button.setToolTip("Delete the note<br><small><b>(no undo!)</b></small>")
		delete_button.clicked.connect(self.close)

		# Header layout
		header_layout.addWidget(self.title_stack)
		#header_layout.addStretch()
		header_layout.addWidget(color_button)
		header_layout.addWidget(delete_button)

		# Main note text editor
		self.editor = NoteEditor(text, self.container) # QTextEdit(self.container)

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
		print("color: " + color.name() + ", index: " + str(index))
		self.color_index = index
		darker = color.darker(125)
		self.setStyleSheet(f"""
			QWidget#container {{
				background-color: {color.name(QColor.NameFormat.HexRgb)};
				border: 1px solid {darker.name(QColor.NameFormat.HexRgb)};
				border-radius: 4px;
			}}
		""")


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
			#print("sending to front: " + self.title.text())
			self.app.on_note_sent_to_front(self)


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

		# Double-click title to edit the title text
		elif event.type() == QEvent.Type.MouseButtonDblClick:
			if event.button() == Qt.MouseButton.LeftButton and watched == self.title:
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
			elif watched == self.editor:
				self.editor.clear_selection()

		# ..but cancel when pressing ESC
		elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
			if watched == self.title_editor and self.editing_title:
				self.editing_title = False
				self.title_stack.setCurrentWidget(self.title)
				return True

		return super().eventFilter(watched, event)


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
		}
		return data


	@classmethod
	def deserialize(cls, data: dict[str, int|str], app: SimpleStickyNotes) -> StickyNote: # type: ignore
		x = int(data["x"])
		y = int(data["y"])
		w = int(data["w"])
		h = int(data["h"])
		text = str(data["text"])
		title = str(data["title"])
		color_index = int(data.get("color", -1))

		note = cls(text = text, title = title, app = app)
		note.move(x, y)
		note.resize(w, h)

		if color_index >= 0:
			note.change_color(ColorPickerMenu.get_color_for_index(color_index), color_index)

		return note
		

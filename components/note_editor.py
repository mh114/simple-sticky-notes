import html

from PySide6.QtWidgets import QApplication, QTextEdit
from PySide6.QtGui import QKeyEvent, QTextCharFormat, QFont, QWheelEvent
from PySide6.QtCore import Qt

class NoteEditor(QTextEdit):
	def __init__(self, text: str = "", parent = None, font_size_offset: int = 0, monospace_font: QFont = None):
		super().__init__(parent)
		self.is_monospace = False
		self.monospace_font = monospace_font
		self.set_font_size_offset(font_size_offset)
		self.setTabStopDistance(4 * 8)
		if text:
			self.set_rich_text(text)


	def set_monospace(self, monospace: bool):
		self.is_monospace = monospace
		self.apply_font_size()


	def toggle_monospace(self):
		self.is_monospace = not self.is_monospace
		self.apply_font_size()


	def set_font_size_offset(self, offset: int):
		self.font_size_offset = max(-8, min(16, offset))
		self.apply_font_size()


	def apply_font_size(self):
		# Apply current font size offset to the global app font size
		if not self.is_monospace:
			font = QFont(QApplication.font())
		else:
			font = QFont(self.monospace_font)
		base_size = font.pointSize()
		rel_size = max(6, base_size + self.font_size_offset)
		font.setPointSize(rel_size)
		# print(f"Applying font size {rel_size}, offset: {self.font_size_offset}")

		self.setFont(font)
		self.document().setDefaultFont(font)


	def zoom_in(self):
		self.set_font_size_offset(self.font_size_offset + 1)


	def zoom_out(self):
		self.set_font_size_offset(self.font_size_offset - 1)


	def get_rich_text(self) -> str:
		"""
		Returns custom very simplified HTML-output from the note editor. Only supports
		bold, italic, underline & strike-through tags, new lines and tabs.
		"""
		doc = self.document()
		html_buf: list[str] = []

		block = doc.begin()
		while block.isValid():
			block_content = ""
			it = block.begin()
			while not it.atEnd():
				fragment = it.fragment()
				if fragment.isValid():
					raw_text = fragment.text()
					text = html.escape(raw_text, quote=False) # Escape HTML from user text to avoid messing up our tags

					# Convert new lines and Qt's internal line separator (U+2028) to <br> tags
					text = text.replace("\u2028", "<br>").replace("\n", "<br>")

					if not text:
						it += 1
						continue

					# Apply the correct format tags around text
					format = fragment.charFormat()
					if format.fontWeight() >= QFont.Weight.Bold:
						text = f"<b>{text}</b>"
					if format.fontItalic():
						text = f"<i>{text}</i>"
					if format.fontUnderline():
						text = f"<u>{text}</u>"
					if format.fontStrikeOut():
						text = f"<s>{text}</s>"

					block_content += text

				it += 1

			html_buf.append(block_content.strip())
			block = block.next()

		# Strip whitespace around lines
		# TODO: Could strip extra repeating whitespace inside lines, too?
		html_buf = [line.strip() for line in html_buf]
		return "<br>".join(html_buf)


	def set_rich_text(self, text: str):
		# We can just use the simplified HTML as is (unsafe obviously, but still)
		text = f'<div style="white-space: pre-wrap;">{text}</div>' # Keep tabs \t
		self.document().setHtml(text)


	def clear_selection(self):
		cursor = self.textCursor()
		cursor.clearSelection()
		self.setTextCursor(cursor)


	def wheelEvent(self, event: QWheelEvent):
		delta = event.angleDelta().y()
		if delta and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
			# CTRL + mouse wheel zooming
			if delta > 0:
				self.zoom_in()
			else:
				self.zoom_out()
			event.accept()
			return

		return super().wheelEvent(event)


	def keyPressEvent(self, event: QKeyEvent):
		modifiers = event.modifiers()
		key = event.key()

		# Handle rich text shortcuts + zoom
		if modifiers == Qt.KeyboardModifier.ControlModifier:
			match key:
				# CTRL-B, CTRL-I, CTRL-U
				case Qt.Key.Key_B:
					self.toggle_bold()
					return
				case Qt.Key.Key_I:
					self.toggle_italic()
					return
				case Qt.Key.Key_U:
					self.toggle_underline()
					return

				# Zooming
				case Qt.Key.Key_Plus:
					self.zoom_in()
					return
				case Qt.Key.Key_Minus:
					self.zoom_out()
					return
				case Qt.Key.Key_0:
					self.set_font_size_offset(0)
					return

		# SHIFT-CTRL-X = strikethrough, -F = clear formatting
		if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
			match key:
				case Qt.Key.Key_X:
					self.toggle_strikethrough()
					return

				case Qt.Key.Key_F:
					self.clear_formatting()
					return

		return super().keyPressEvent(event)


	def toggle_bold(self):
		format = QTextCharFormat()
		if self.currentCharFormat().fontWeight() == QFont.Weight.Normal:
			format.setFontWeight(QFont.Weight.Bold)
		else:
			format.setFontWeight(QFont.Weight.Normal)
		self.apply_format(format)


	def toggle_italic(self):
		format = QTextCharFormat()
		format.setFontItalic(not self.currentCharFormat().fontItalic())
		self.apply_format(format)


	def toggle_underline(self):
		format = QTextCharFormat()
		format.setFontUnderline(not self.currentCharFormat().fontUnderline())
		self.apply_format(format)


	def toggle_strikethrough(self):
		format = QTextCharFormat()
		format.setFontStrikeOut(not self.currentCharFormat().fontStrikeOut())
		self.apply_format(format)


	def clear_formatting(self):
		format = QTextCharFormat()
		format.setFontWeight(QFont.Weight.Normal)
		format.setFontItalic(False)
		format.setFontUnderline(False)
		format.setFontStrikeOut(False)
		self.apply_format(format)


	def apply_format(self, format: QTextCharFormat):
		cursor = self.textCursor()
		if cursor.hasSelection():
			# Merge text format with current selection
			cursor.mergeCharFormat(format)
			self.setTextCursor(cursor)
		else:
			# Apply text format for characters that are typed next
			self.setCurrentCharFormat(format)


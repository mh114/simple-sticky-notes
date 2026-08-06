import html

from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCharFormat, QFont
from PySide6.QtCore import QEvent, Qt

class NoteEditor(QTextEdit):
	def __init__(self, text: str = "", parent = None):
		super().__init__(parent)
		if text:
			self.set_rich_text(text)


	def get_rich_text(self) -> str:
		"""
		Returns custom very simplified HTML-output from the note editor. Only supports
		bold, italic, strike-through tags and new lines.
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
		self.document().setHtml(text)


	def keyPressEvent(self, event: QEvent):
		modifiers = event.modifiers()
		key = event.key()

		# Handle rich text shortcuts
		# CTRL-B, CTRL-I
		if modifiers == Qt.KeyboardModifier.ControlModifier:
			match key:
				case Qt.Key.Key_B:
					self.toggle_bold()
					return

				case Qt.Key.Key_I:
					self.toggle_italic()
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


	def toggle_strikethrough(self):
		format = QTextCharFormat()
		format.setFontStrikeOut(not self.currentCharFormat().fontStrikeOut())
		self.apply_format(format)


	def clear_formatting(self):
		format = QTextCharFormat()
		format.setFontWeight(QFont.Weight.Normal)
		format.setFontItalic(False)
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


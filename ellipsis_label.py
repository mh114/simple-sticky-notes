from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QFontMetrics, QPaintEvent

class EllipsisLabel(QLabel):
	def __init__(self, text: str = "", parent = None):
		super().__init__(text, parent)
		self.setText(text, False)
		self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)


	def setText(self, text: str, update_geom: bool = True):
		self._full_text = text
		self.setToolTip(text)

		if update_geom:
			self.updateGeometry()
			self.update()


	def text(self) -> str:
		return self._full_text


	def paintEvent(self, event: QPaintEvent):
		painter = QPainter(self)
		font_metrics = QFontMetrics(self.font())
		ellipsis_text = font_metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
		painter.drawText(self.rect(), self.alignment() | Qt.TextFlag.TextSingleLine, ellipsis_text)


	def _measure_text(self, text: str) -> int:
		font_metrics = QFontMetrics(self.font())
		margins = self.contentsMargins()
		return font_metrics.horizontalAdvance(text) + margins.left() + margins.right()


	def sizeHint(self) -> QSize:
		# Preferred size is width of the full text + margins (height is default)
		orig = super().sizeHint()
		text_width = self._measure_text(self._full_text)
		return QSize(text_width, orig.height())


	def minimumSizeHint(self) -> QSize:
		# Minimum size allows shrinking down to "..." + margins (height is default)
		orig = super().sizeHint()
		min_width = self._measure_text("...")
		return QSize(min_width, orig.height())



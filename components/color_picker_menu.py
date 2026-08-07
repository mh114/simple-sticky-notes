from PySide6.QtWidgets import QGridLayout, QMenu, QPushButton, QWidget, QWidgetAction
from PySide6.QtGui import QColor, Qt
from PySide6.QtCore import Signal

NUM_COLORS = 16
HUE_STEP = 1.0 / NUM_COLORS


class ColorPickerMenu(QMenu):
	"""
	Shows a grid of color squares to choose from. Colors are created dynamically
	from a rainbow of colors (hue variation).
	"""
	color_picked = Signal(QColor, int)

	def __init__(self, columns=4, parent=None):
		super().__init__(parent)
		self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
		self.setStyleSheet("background-color: rgba(128, 128, 128, 0.6); border: 1px solid gray; border-radius: 8px;")

		# Rainbow of colors
		colors: list[QColor] = [ColorPickerMenu.get_color_from_index(i) for i in range(NUM_COLORS)]

		# Grid layout of color buttons
		grid = QWidget(self)
		grid.setStyleSheet("background: transparent; border: none;")
		grid_layout = QGridLayout(grid)
		grid_layout.setContentsMargins(6, 6, 6, 6)
		grid_layout.setSpacing(6)

		for i, color in enumerate(colors):
			button = QPushButton()
			button.setFixedSize(26, 26)
			button.setCursor(Qt.CursorShape.PointingHandCursor)

			button.setStyleSheet(f"""
				QPushButton {{
					background-color: {color.name(QColor.NameFormat.HexRgb)};
					border: 1px solid rgba(0, 0, 0, 0.5);
					border-radius: 4px;
				}}
				QPushButton:hover {{
					border: 2px solid #000000;
				}}
			""")

			row = i // columns
			column = i % columns
			grid_layout.addWidget(button, row, column)

			# Wire the click handler that sends the signal, capturing current color & index for the lambda
			button.clicked.connect(lambda _, col=color, index=i: self._on_color_clicked(col, index))


		# Wrap inside QWidgetAction to display inside the menu
		widget_action = QWidgetAction(self)
		widget_action.setDefaultWidget(grid)
		self.addAction(widget_action)


	def _on_color_clicked(self, color: QColor, index: int):
		self.color_picked.emit(color, index)
		self.close()


	def _color_from_hue(hue: float) -> QColor:
		return QColor.fromHsvF(hue, 0.55, 0.975)


	def get_color_from_index(index: int) -> QColor:
		return ColorPickerMenu._color_from_hue(HUE_STEP * index)


	def default_color() -> tuple[QColor, int]:
		return (ColorPickerMenu._color_from_hue(HUE_STEP * 2), 2)

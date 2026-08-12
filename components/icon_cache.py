# (Simple) Sticky Notes - Copyright (c) 2026 Mika Halttunen (https://www.mhgames.org)
# https://github.com/mh114/simple-sticky-notes
# Licensed under the MIT-license.

from pathlib import Path

from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, Qt
from PySide6.QtSvg import QSvgRenderer

# Cache of icon paths <-> icons
_icons: dict[str, QIcon] = {}

# components/... -> ../assets/...
ASSETS_PATH = Path(__file__).parent.parent / "assets"
DEFAULT_ICON_SIZE = QSize(24, 24)

class IconCache:
	"""
	Loads SVG icons and caches them, so several widgets can share these same icons.
	Optionally alters the icon opacity, scale or color during load.
	"""

	def load_icon_svg(filename: str, size: QSize = DEFAULT_ICON_SIZE, scale: float = 1.0, opacity: float = 1.0, color: QColor = None) -> QIcon:
		# Cache by combination of filename, size, scale and opacity
		cache_path = f"{filename}@{size.toTuple()},{scale:.2f},{opacity:.2f}"
		icon = _icons.get(cache_path, None)
		if not icon:
			# Load the SVG and render it into a pixmap
			renderer = QSvgRenderer(str(ASSETS_PATH / filename))
			pixmap = QPixmap(size)
			pixmap.fill(Qt.GlobalColor.transparent)

			painter = QPainter(pixmap)
			painter.setOpacity(opacity)
			if abs(scale - 1.0) > 0.0001:
				# Optionally scale
				sw = size.width() * scale
				sh = size.height() * scale
				x = size.width() / 2 - sw * 0.5
				y = size.height() / 2 - sh * 0.5
				bounds = QRectF(x, y, sw, sh)
				renderer.render(painter, bounds)
			else:
				renderer.render(painter)

			if color:
				# Optionally replace pixels with given color
				painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
				painter.fillRect(pixmap.rect(), color)
			painter.end()

			icon = QIcon(pixmap)
			_icons[cache_path] = icon
			# print("Loaded new icon to cache: " + cache_path)

		return icon


	def get_icon_qss_url(filename: str) -> str:
		return f"url({str(ASSETS_PATH / filename)})"

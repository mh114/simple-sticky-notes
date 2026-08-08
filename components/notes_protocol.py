from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
	from components.sticky_note import StickyNote


# NOTE: Could use signals for these..
class NotesProtocol(Protocol):
	def delete_note(note: StickyNote): ...
	def on_note_sent_to_front(note: StickyNote): ...
	def is_quitting() -> bool: ...


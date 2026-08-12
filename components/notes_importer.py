# (Simple) Sticky Notes - Copyright (c) 2026 Mika Halttunen (https://www.mhgames.org)
# https://github.com/mh114/simple-sticky-notes
# Licensed under the MIT-license.

import json
import re
from pathlib import Path


class NotesImporter:
	def import_mint_sticky_notes():
		""" Rudimentary importer for Linux Mint Sticky notes. Might be useful for somebody, probably not. """
		try:
			notes_file = Path.home() / ".config" / "sticky" / "notes.json"
			if not notes_file.exists():
				print("Nothing to import!")
				return

			imported_notes = []
			
			groups_data = json.loads(notes_file.read_text(encoding="utf-8"))
			for group in groups_data:
				notes_data = groups_data[group]
				for note in notes_data:
					text = note["text"].strip()
					note["w"] = note["width"]
					note["h"] = note["height"]
					note["color"] = NotesImporter._map_color(note["color"])

					# These tags were inline, but we only support them on per note basis
					if "#tag:large:" in text or "#tag:larger:" in text:
						note["font_size"] = 2
					if "#tag:monospace:" in text:
						note["fixed_width"] = True

					# Replace formatting tags
					text = NotesImporter._replace_tag(text, "bold", "<b>", "</b>")
					text = NotesImporter._replace_tag(text, "italic", "<i>", "</i>")
					text = NotesImporter._replace_tag(text, "underline", "<u>", "</u>")

					# Strip the remaining tags
					text = re.sub(r"#tag:\w+:", "", text)
					text = text.replace("\n", "<br>")
					text = text.replace("##", "#")
					note["text"] = text
					note["i"] = len(imported_notes)
					del note["width"]
					del note["height"]
					imported_notes.append(note)

			output_file = Path.home() / ".config" / "simple-sticky-notes" / "imported_notes.json"
			print(f"IMPORTED {len(imported_notes)} notes. Saving to {output_file} (rename it to 'notes.json' to use!)")
			with open(str(output_file), "wt", encoding="utf-8") as f:
				json.dump({ "notes": imported_notes }, f, indent=4, ensure_ascii=False)
			print("DONE!")

		except Exception as ex:
			print(f"ERROR: Failed to import!\n{ex}")


	def _replace_tag(text: str, tag: str, opening_tag: str, closing_tag: str) -> str:
		return re.sub(rf"(#tag:{tag}:)(.*)(#tag:{tag}:)", rf"{opening_tag}\2{closing_tag}", text)


	def _map_color(color_name: str) -> int:
		match color_name:
			case "red":
				return 0
			case "orange":
				return 1
			case "yellow":
				return 2
			case "green":
				return 4
			case "teal":
				return 6
			case "blue":
				return 8
			case "purple":
				return 10
			case "magenta":
				return 15
			case _:
				return -1

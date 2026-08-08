# (Simple) Sticky Notes
A quite simple sticky notes application, nothing more.

## Short origin story
This app was partially inspired by [**Linux Mint** Sticky](https://github.com/linuxmint/sticky); as I distro-hopped from Mint to **Fedora KDE** I found myself wanting a similar _sticky notes_ app, that would allow freeform note placement and, crucially, one click toggling of notes. I didn't find a suitable replacement so I decided to write one myself!

## Features
- Sticky notes of different colors, basic rich-text support (**bold**, _italic_, ~~strikethrough~~ and <u>underline</u>)
- One click on the system tray icon to hide/show notes!
- Somewhat functional Emoji-support
	- see installation notes below
- Works in KDE, but alas, through XWayland for now... 😔
	- I ran into issues with note/window positioning on Wayland and ultimately ended up side-stepping the issue by running in XWayland 🫣
	- I _have_ some ideas on how to realise native Wayland support, but it remains to be seen if I can be bothered to try them.. 🤔
	- Also needs a _KDE Window Rule_ to avoid stickies from showing up in taskbar / task switcher (see installation notes below)
- Global font name & size can be set through the config-file (`simple-sticky-notes.conf`)
- Written in **Python** using **PySide/Qt**

## Install / setup notes
...

## TODO-list
- note scrollbar should be styled to look nicer
- investigate automatic KWin rule setup
- periodic autosave? (need to detect if notes are "dirty")
	- or trigger save after typing / making changes (with some delay)
- ...

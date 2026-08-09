# (Simple) Sticky Notes
A quite simple sticky notes application, nothing more.

## Short origin story
This app was partially inspired by [**Linux Mint** Sticky](https://github.com/linuxmint/sticky); as I distro-hopped from Mint to **Fedora KDE** I found myself wanting a similar _sticky notes_ app, that would allow freeform note placement and, crucially, one click toggling of notes. I didn't find a suitable replacement so I decided to write one myself!

**TODO: ADD SCREENSHOT(S)**

## Features
- Sticky notes of different colors, basic rich-text support (**bold**, _italic_, ~~strikethrough~~ and <ins>underline</ins>)
- One click on the system tray icon to hide/show notes!
- Global font name & size can be set through the config-file (`simple-sticky-notes.conf`)
	- Text size can be adjusted individually per sticky note as needed
- Somewhat functional Emoji-support
	- → see installation notes below
- Works in KDE, but alas, through XWayland for now... 😔
	- I ran into issues with note/window positioning on Wayland and ultimately ended up side-stepping the issue by running in XWayland 🫣
	- I _have_ some ideas on how to realise native Wayland support, but it remains to be seen if I can be bothered to try them.. 🤔
	- Also needs a _KDE Window Rule_ to avoid stickies from showing up in taskbar / task switcher (→ see installation notes below)
- Written in **Python** using **PySide6**/**Qt**

## Install / setup notes
After cloning the code, run these commands to create the virtual environment, activate it and install dependencies:
```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### To launch the app:
- while within `.venv`-shell: `python3 simple_sticky_notes.py`
	- to exit `.venv`-shell: `deactivate`
- normally (i.e. use the Python from inside the `.venv`):  
  ```
  /PATH/TO/simple-sticky-notes/.venv/bin/python3 /PATH/TO/simple-sticky-notes/simple_sticky_notes.py
  ```

### KDE Window rule, or: _how to avoid stickies being all over the taskbar?_
Two options: manual setup or automatic setup.
#### Automatic setup:
**TODO: IMPLEMENT THIS** On the first run, **Simple Sticky Notes** offers to add the window rule for you, unless it already exists. Accept and it should do the trick.

#### Manual setup:
Go to **KDE System Settings** → **Window Rules** and add a new rule. Configure it like below:
- Window class, match: `simple-sticky-notes`
- Virtual desktops: **Force, All desktops** (this is optional)
- Skip taskbar: **Force, Yes**
- Skip pager: **Force, Yes**
- Skip switcher: **Force, Yes**

![Window rule setup](./img/kde_window_rule.webp)

### Emoji-support
...

## TODO-list
- [ ] Fixed-width/monospace font option per sticky note
- [ ] Note scrollbar should be styled to look nicer
- [ ] Investigate automatic KWin rule setup
- [ ] Periodic autosave? (need to detect if notes are "dirty")
	- Or trigger save after typing / making changes (with some delay)
- [ ] ...

# Anki HTML Exporter

This add-on lets you export the back side of selected cards from Anki’s Browser and save them as a readable HTML document. The exported HTML looks almost exactly like what you see inside Anki because it uses the card’s actual template and CSS.

## Features
- Export the back side of selected cards to a single HTML file.
- Uses each card’s template and CSS so the exported page matches Anki rendering.
- Works from Anki Browser selection.

## Requirements
- Anki 2.1+ (tested on stable releases)
- Add-on compatible with Anki’s bundled Python runtime (no external installation required)

## Installation
1. Download the add-on as a zip or clone this repository.
2. In Anki: Tools → Add-ons → Open Add-ons Folder.
3. Place the add-on folder (or extract the zip) into the add-ons folder.
4. Restart Anki.

Alternatively, install via Anki's Add-ons → Install from file if you have a packaged zip.

## Usage
1. Open Anki Browser and select the notes/cards you want to export.
2. From the add-ons menu or context menu, choose “Export Back Sides as HTML” (or similar).
3. Choose an output file location and name.
4. Open the resulting HTML file in a browser — it will show card backs rendered with the card templates and CSS.

## Configuration
- No complex configuration is required. If you want to tweak the output styling, edit the exported HTML file or modify templates in Anki.

## Troubleshooting
- If styling looks wrong, verify the card template and CSS in the note type.
- If images do not appear, ensure the collection.media files are available in Anki’s media folder and relative paths are preserved.

## Development
- Contributions and bug reports are welcome. Please open an issue on GitHub describing the problem and include Anki version and steps to reproduce.

## License
MIT License — see LICENSE file.

## Contact
Author: yuwayanagitani

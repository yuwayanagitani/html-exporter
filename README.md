# Anki HTML Exporter

AnkiWeb: https://ankiweb.net/shared/by-author/2117859718

Export the back side of selected cards from Anki’s Browser into a readable HTML document. The exported HTML uses the card's actual template and CSS so it looks like what you see in Anki.

## Features
- Export backs of selected cards to a single HTML file
- Preserves card template HTML and CSS
- Option to include front side or notes metadata

## Installation
1. Tools → Add-ons → Open Add-ons Folder.
2. Place the add-on folder in `addons21/`.
3. Restart Anki.

## Usage
- Select cards in the Browser → Tools → Export to HTML.
- Choose output path and options (include front, include CSS).

## Options
- Include front side
- Include inline CSS
- Output filename and preview in browser

## Development
- Python for Anki.
- CSS and templates are included so output matches the card render.

## Issues & Support
Report exporting problems (e.g., missing CSS or assets) with a reproducible example.

## License
See LICENSE.

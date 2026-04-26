# Changelog

## 1.1.0

- 💾 **QR codes now download as PNG** named after the appliance (e.g. `dishwasher.png`), with the appliance name and subtitle rendered below the code
- 🔒 **URL obfuscation**: random suffixes added to all uploaded files and generated HTML pages so URLs aren't easily guessable (e.g. `dishwasher-a7b3c9.html`)
- 🚦 **Rate limiting** on the upload endpoint (30 uploads/min per client) to prevent flooding
- 🖨 Print button still works — opens a clean printable page in a new tab

### Configuration

New option `obfuscate_urls` (default: `true`). Set to `false` if you prefer simple, readable URLs like `/local/manuals/dishwasher.html`.

## 1.0.1

- Fixed Dockerfile build failures with newer Alpine base images

## 1.0.0

- Initial release
- Dashboard listing all manuals
- Editor with video, PDF, and troubleshooting support
- In-page upload from phone camera roll
- QR code generator
- YouTube/Vimeo URL embedding
- Persistent storage in `/config/www/<subfolder>/`

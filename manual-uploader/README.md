# Manual Uploader

Create interactive QR-coded manuals for your appliances, with videos, PDFs, and troubleshooting tips — all uploadable directly from your phone.

## Features

- 📱 **Phone-friendly editor** — add videos and PDFs directly from your camera roll
- 📺 **YouTube/Vimeo support** — paste a URL instead of uploading if you prefer
- 🔧 **Troubleshooting FAQ** — collapsible Q&A for common issues
- 📷 **QR code generator** — printable QR to stick on the appliance
- 🌓 **Auto dark mode** — looks good on every phone
- 🔒 **Fully local** — nothing leaves your network; files live in `/config/www/`

## Installation

1. Install this add-on from the Home Assistant Add-on Store (after adding the repository)
2. Click **Start**
3. Click **Open Web UI** (or use the "Manuals" item in your sidebar)

## Usage

### Create your first manual

1. Click **➕ New Manual**
2. Type the appliance name and subtitle (model, location)
3. Click **➕ Add** under Videos → **📤 Upload** → pick a video from your phone
4. Repeat for PDFs and troubleshooting items
5. Click **💾 Save**
6. A QR code appears — click **🖨 Print QR** to print it
7. Stick the printed QR on the appliance

### Scan the QR code

Anyone on your Wi-Fi can now scan the QR code to open the manual on their phone.

### Edit an existing manual

From the main list, click **Edit** on any manual card. Changes are saved when you click Save again.

## Configuration

| Option | Default | Description |
|---|---|---|
| `max_upload_mb` | `500` | Maximum upload size per file in megabytes |
| `subfolder` | `manuals` | Subfolder inside `/config/www/` where files are stored |

Files are served by Home Assistant at `/local/<subfolder>/<filename>`.

## Where are my files stored?

All uploaded files and generated HTML pages live in:

```
/config/www/manuals/    (or whatever subfolder you configured)
```

This means:
- They persist across add-on restarts and reinstalls
- You can access them directly via Samba or the File Editor add-on
- They're served by HA at `/local/manuals/<filename>`

## Notes

- **Network access**: Manuals are only accessible on your local network by default. If you have Nabu Casa Cloud or an external URL configured, they may also be accessible remotely — but the QR codes will encode whichever URL was active when you printed them.
- **QR codes use your HA base URL**: When you print a QR, it encodes the current HA URL (e.g. `http://192.168.1.50:8123/local/manuals/dishwasher.html`). Make sure you print from a device using the URL you want — ideally your HA IP or hostname, not an external URL.
- **Security**: Files in `/config/www/` are **not** authenticated — anyone who knows the URL can view them. Don't put sensitive content in manuals.

## Troubleshooting

**The QR shows "Save first"** — click Save at the bottom. The QR can only be generated once the manual has a stable URL.

**Uploads failing** — check the add-on logs (Settings → Add-ons → Manual Uploader → Log). Common causes: file larger than `max_upload_mb`, or unsupported file extension.

**Can't see uploaded videos in the printed page** — the video URL uses `/local/manuals/...`. Make sure you're viewing via HA, not directly opening the file from disk.

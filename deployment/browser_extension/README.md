# DueCare browser extension (Chrome Manifest V3)

Analyze any selected text on any webpage for trafficking / exploitation
indicators. Posts the selection to your DueCare server — which can run
entirely on your laptop.

## Install (unpacked, developer mode)

1. Start a DueCare server locally:

   ```bash
   cd gemma4_comp
   uvicorn src.demo.app:app --port 8080
   ```

2. Open `chrome://extensions` (Edge: `edge://extensions`; Brave:
   `brave://extensions`), enable Developer Mode.
3. Click **Load unpacked**, select the `deployment/browser_extension`
   folder.
4. The DueCare toolbar icon appears. Right-click any selected text on a
   webpage to analyze it; or click the toolbar icon to paste text
   directly.

## How it works

- **Right-click context menu:** "Analyze with DueCare" on any selection.
  Fires a `POST /api/v1/analyze` to your endpoint and shows the grade
  and action in a notification.
- **Toolbar popup:** a paste-and-analyze mini dashboard with
  jurisdiction + language selectors.
- **Options page:** point the extension at any DueCare endpoint —
  `localhost`, an HF Spaces URL, a Render deploy, etc. No default
  cloud fallback; if your endpoint is down, analysis fails loudly.

## File layout

```
browser_extension/
├── manifest.json       # MV3 manifest (service worker, permissions)
├── background.js       # Context menu handler + notification dispatcher
├── popup.html + .js    # Toolbar popup UI
├── options.html + .js  # Settings page
├── icons/              # PNG icons (16, 32, 48, 128)
└── README.md
```

## Permissions justification

- `contextMenus` — to add the right-click "Analyze with DueCare" entry.
- `storage` — to remember the endpoint, jurisdiction, and language.
- `activeTab` + `scripting` — to read the selection only when the user
  invokes the extension.
- `notifications` — to show the grade + action after analysis.
- `host_permissions: localhost, *.hf.space` — the extension only
  contacts the configured DueCare endpoint.

No background network activity. No analytics. No tracking.

## Status

Minimum viable extension. Ships with placeholder icons and no Chrome
Web Store listing. The architecture is deliberate: point-and-click for
NGO intake officers who review online job ads in bulk, without ever
leaving the browser tab.

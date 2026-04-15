// DueCare browser extension — service worker (MV3).
// Adds a right-click context menu "Analyze with DueCare" on any selected
// text. Posts the selection to the configured DueCare endpoint and shows
// the grade + action in a notification.

const MENU_ID = "duecare-analyze-selection";
const DEFAULT_ENDPOINT = "http://localhost:8080";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Analyze with DueCare",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID) return;
  if (!info.selectionText) return;

  const { endpoint = DEFAULT_ENDPOINT, jurisdiction = "", language = "en" } =
    await chrome.storage.sync.get(["endpoint", "jurisdiction", "language"]);

  try {
    const resp = await fetch(`${endpoint}/api/v1/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: info.selectionText,
        context: "other",
        jurisdiction,
        language,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    await notify(data);
    await chrome.storage.session.set({ lastResult: data });
  } catch (err) {
    await chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "DueCare — analysis failed",
      message: `Could not reach ${endpoint}. Is your DueCare server running? (${err.message})`,
    });
  }
});

async function notify(result) {
  const grade = (result.grade || "neutral").toUpperCase();
  const action = (result.action || "review").toUpperCase();
  const score = Math.round((result.score || 0) * 100);
  const top = (result.indicators || []).slice(0, 3).join(", ") || "no indicators";
  await chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon128.png",
    title: `DueCare: ${grade} (${score}%) — ${action}`,
    message: top.replaceAll("_", " "),
    priority: action === "BLOCK" || grade === "WORST" ? 2 : 1,
  });
}

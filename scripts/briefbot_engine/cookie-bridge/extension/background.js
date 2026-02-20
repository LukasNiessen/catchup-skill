/**
 * BriefBot Cookie Bridge - Background Service Worker
 *
 * Reads auth_token and ct0 cookies from x.com via Chrome's cookies API
 * (which returns decrypted values, bypassing App-Bound Encryption),
 * then sends them to a native messaging host that writes them to
 * ~/.config/briefbot/.env for bird-search to use.
 *
 * Triggers: on install, on Chrome startup, every 60 min, on cookie change.
 */

const NATIVE_HOST = "com.briefbot.cookies";
const ALARM_NAME = "briefbot-cookie-refresh";
const COOKIE_DOMAIN = ".x.com";

/**
 * Read auth_token and ct0 from Chrome's cookie store for x.com,
 * then send them to the native messaging host.
 */
async function exportCookies() {
  try {
    const cookies = await chrome.cookies.getAll({ domain: COOKIE_DOMAIN });

    const authToken = cookies.find((c) => c.name === "auth_token")?.value;
    const ct0 = cookies.find((c) => c.name === "ct0")?.value;

    if (!authToken || !ct0) {
      // User not logged into X — nothing to export
      return;
    }

    // Send to native host (fire-and-forget; response is logged but not required)
    chrome.runtime.sendNativeMessage(
      NATIVE_HOST,
      { auth_token: authToken, ct0: ct0 },
      (response) => {
        if (chrome.runtime.lastError) {
          console.warn(
            "[BriefBot] Native host error:",
            chrome.runtime.lastError.message
          );
        } else if (response?.status === "ok") {
          console.log("[BriefBot] Cookies exported successfully");
        }
      }
    );
  } catch (err) {
    console.error("[BriefBot] exportCookies failed:", err);
  }
}

// --- Event listeners ---

// On first install or update
chrome.runtime.onInstalled.addListener(() => {
  exportCookies();
  // Refresh every 60 minutes to keep cookies fresh
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 60 });
});

// On Chrome startup
chrome.runtime.onStartup.addListener(() => {
  exportCookies();
  // Re-create alarm (service worker may have been killed)
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 60 });
});

// Periodic refresh
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    exportCookies();
  }
});

// Real-time: export whenever auth_token or ct0 changes
chrome.cookies.onChanged.addListener((changeInfo) => {
  const { cookie, removed } = changeInfo;
  if (
    cookie.domain === COOKIE_DOMAIN &&
    (cookie.name === "auth_token" || cookie.name === "ct0") &&
    !removed
  ) {
    exportCookies();
  }
});

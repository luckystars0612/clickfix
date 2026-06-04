/**
 * ClickFix Awareness Demo - JavaScript Payload
 * MỤC ĐÍCH: Chỉ dùng để test nhận thức an toàn nội bộ
 * Không có hành vi nguy hại - chỉ hiển thị cảnh báo giáo dục
 */

(function runClickFixPayload() {
  // Ghi log sự kiện click về server để tracking
  const lureName = document.body.dataset.lure || 'unknown';
  
  fetch('/api/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lure: lureName, event: 'button_click' })
  }).catch(() => {});

  // Track payload execution
  fetch('/api/exfil', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lure: lureName,
      hostname: '[browser-client]',
      username: '[browser-user]',
      os: navigator.userAgent,
      output: 'JS payload clicked at ' + new Date().toISOString()
    })
  }).catch(() => {});
})();

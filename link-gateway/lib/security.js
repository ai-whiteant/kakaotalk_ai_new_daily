function headers(res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
}
function validId(v) { return typeof v === 'string' && /^evt_[a-f0-9]{20}$/.test(v); }
function safeUrl(v) {
  if (typeof v !== 'string' || /[\s\\]/.test(v)) return false;
  try {
    const u = new URL(v);
    return u.protocol === 'https:' && !!u.hostname && !u.username && !u.password && !u.hash && !u.port;
  } catch { return false; }
}
module.exports = {headers, validId, safeUrl};

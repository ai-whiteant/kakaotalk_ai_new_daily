const targets = require('../data/targets.json');
const {headers, validId, safeUrl} = require('../lib/security');
module.exports = function handler(req, res) {
  headers(res);
  if (!['GET', 'HEAD'].includes(req.method)) {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).end();
  }
  // Arrays (including duplicate query values) are invalid, never first-value wins.
  const id = (req.query || {}).event_id;
  if (!validId(id)) return res.status(400).end();
  if (!Object.hasOwn(targets, id)) return res.status(404).end();
  const target = targets[id];
  if (!safeUrl(target)) return res.status(500).end();
  // No request URL, host, forwarded header or arbitrary query value is used here.
  res.setHeader('Location', target);
  return res.status(302).end();
};

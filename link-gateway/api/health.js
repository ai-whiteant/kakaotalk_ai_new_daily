const {headers} = require('../lib/security');
module.exports = function handler(req, res) {
  headers(res);
  if (!['GET', 'HEAD'].includes(req.method)) {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).end();
  }
  if (req.method === 'HEAD') return res.status(200).end();
  return res.status(200).json({ok:true,service:'kakao-ai-news-link-gateway',version:'1.0.0'});
};

const https = require('https'); https.get('https://cloudcode-pa.googleapis.com', (res) => { console.log('StatusCode:', res.statusCode); }).on('error', (e) => { console.error(e); });

const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('pageerror', error => console.log('PAGE EXCEPTION:', error.message, error.stack));
  
  await page.evaluateOnNewDocument(() => {
    window.addEventListener('error', e => {
      console.log('WINDOW ERROR:', e.message, e.filename, e.lineno, e.colno, e.error ? e.error.stack : 'no stack');
    });
    window.addEventListener('unhandledrejection', e => {
      console.log('PROMISE ERROR:', e.reason);
    });
  });

  page.on('console', msg => console.log('CONSOLE:', msg.text()));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle0' });
  } catch (err) {
    console.error('Failed to load:', err);
  }

  await browser.close();
})();

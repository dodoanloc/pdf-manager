const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  // Go to login page
  await page.goto('http://10.28.10.161:3511/login');
  
  // Fill login form
  await page.type('#username', 'admin');
  await page.type('#password', 'admin');
  
  // Click login button
  await page.click('#loginBtn');
  
  // Wait for navigation
  await page.waitForNavigation({ waitUntil: 'networkidle0' });
  
  // Wait a bit for content to load
  await page.waitForTimeout(2000);
  
  // Take screenshot
  await page.screenshot({ path: '/home/locdodoan/main_screen_admin.png' });
  
  await browser.close();
  console.log('Screenshot saved to /home/locdodoan/main_screen_admin.png');
})();

const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  // Use the HTML we created earlier
  await page.goto('http://localhost:3000/projects', { waitUntil: 'networkidle2' });
  
  // Get computed color
  const color = await page.evaluate(() => {
    const el = document.querySelector('a[href="/projects/new"]');
    if (!el) return 'Element not found';
    return window.getComputedStyle(el).color;
  });
  
  console.log("Color is:", color);
  
  await browser.close();
})();

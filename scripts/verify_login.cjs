const { chromium } = require('playwright-core')
const APP = 'http://localhost:5180'

const out = []
const t = (id, desc, ok, note = '') => {
  out.push({ ok })
  console.log(`${ok ? '  PASS' : '  FAIL'}  ${id}  ${desc}${note ? ' | ' + note : ''}`)
}

const signIn = async (page, email, password) => {
  await page.fill('input[type=email]', email)
  await page.fill('input[type=password]', password)
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForTimeout(1500)
}

;(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 } })
  const page = await ctx.newPage()
  const errs = []
  page.on('pageerror', e => errs.push(e.message))

  await page.goto(APP + '/', { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(2000)
  t('1', 'bina login / -> /login par bhejta hai', page.url().endsWith('/login'), page.url())
  t('2', 'login form dikhta hai', await page.locator('input[type=password]').count() > 0)

  await page.goto(APP + '/tpo/calendar', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1500)
  t('3', 'guarded route bina login nahi khulta', page.url().endsWith('/login'), page.url())

  await signIn(page, 'tpo@campus.test', 'wrong-password')
  const errorText = await page.locator('[role=alert]').innerText().catch(() => '')
  t('4', 'galat password par message', /incorrect/i.test(errorText), errorText.slice(0, 50))
  t('5', 'aur login page par hi rukta hai', page.url().endsWith('/login'))

  await page.fill('input[type=password]', '')
  await signIn(page, 'tpo@campus.test', 'tpo@1234')
  t('6', 'TPO login -> /tpo/calendar', page.url().endsWith('/tpo/calendar'), page.url())
  t('7', 'calendar dikh raha hai', /Campus Calendar/i.test(await page.evaluate(() => document.body.innerText)))

  await page.goto(APP + '/student/calendar', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1200)
  t('8', 'TPO student ka route nahi khol sakta', page.url().endsWith('/tpo/calendar'), page.url())

  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1800)
  t('9', 'reload par session bacha rehta hai', page.url().endsWith('/tpo/calendar'), page.url())

  await page.getByRole('button', { name: /sign out/i }).click()
  await page.waitForTimeout(1200)
  t('10', 'sign out -> /login', page.url().endsWith('/login'), page.url())

  await signIn(page, 'student@campus.test', 'student@1234')
  t('11', 'student login -> /student/calendar', page.url().endsWith('/student/calendar'), page.url())
  await page.goto(APP + '/tpo/calendar', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1200)
  t('12', 'student TPO ka route nahi khol sakta', page.url().endsWith('/student/calendar'), page.url())

  t('13', 'koi JS error nahi', errs.length === 0, errs.slice(0, 2).join(' | '))

  console.log(`\n${out.filter(r => r.ok).length} pass, ${out.filter(r => !r.ok).length} fail`)
  await browser.close()
})().catch(e => { console.error('RUN ERROR:', e.message); process.exit(1) })

gsap.registerPlugin(ScrollTrigger);
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const mobile = () => innerWidth <= 860;

/* плавная прокрутка */
let lenis = null;
if (!reduce && window.Lenis) {
  lenis = new Lenis({ lerp: 0.09 });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add(t => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
  document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', e => {
    const el = document.querySelector(a.getAttribute('href'));
    if (el) { e.preventDefault(); lenis.scrollTo(el, { offset: a.getAttribute('href') === '#top' ? 0 : -40 }); }
  }));
}

/* шапка со стеклом */
const nav = document.getElementById('nav');
ScrollTrigger.create({ start: 60, end: 'max', onToggle: s => nav.classList.toggle('solid', s.isActive) });

/* заголовок «садится»: ширина шрифта сжимается */
function shrinkTitle(el, from, to, st) {
  const spans = [...el.children];
  const set = p => spans.forEach((s, i) => {
    const q = gsap.utils.clamp(0, 1, p * 1.25 - i * 0.12);
    s.style.setProperty('--w', (from + (to - from) * q).toFixed(1));
  });
  set(0);
  ScrollTrigger.create({ ...st, onUpdate: s => set(s.progress) });
}

/* 1. первый экран: покадровая усадка */
const cv = document.getElementById('seq'), ctx = cv.getContext('2d');
const S = window.SEQ || { n: 0 };
const frames = [];
const src = i => `media/seq/s${String(i + 1).padStart(4, '0')}.jpg`;
const still = [new Image(), new Image()];
still[0].src = 'media/hero-start.jpg'; still[1].src = 'media/hero-end.jpg';
if (S.n) for (let i = 0; i < S.n; i++) { const im = new Image(); im.decoding = 'async'; im.src = src(i); frames.push(im); }

let heroP = 0, shown = -1;
function fit() {
  const d = Math.min(devicePixelRatio || 1, 2);
  cv.width = cv.clientWidth * d; cv.height = cv.clientHeight * d;
  shown = -1; draw();
}
function place(im) {
  const W = cv.width, H = cv.height, iw = im.naturalWidth, ih = im.naturalHeight;
  // бутылка занимает ~85% высоты кадра: вписываем по высоте, края кадра растворяем в фон
  const sc = mobile() ? (H * 0.56) / ih : (H * 0.9) / ih;
  const w = iw * sc, h = ih * sc;
  const cx = mobile() ? W * 0.5 : W * 0.66;
  const cy = mobile() ? H * 0.34 : H * 0.55;
  return [cx - w / 2, cy - h / 2, w, h];
}
function feather([x, y, w, h]) {
  const bg = 'rgba(245,238,229,', f = w * 0.16, fv = h * 0.12;
  let g = ctx.createLinearGradient(x, 0, x + f, 0); g.addColorStop(0, bg + '1)'); g.addColorStop(1, bg + '0)'); ctx.fillStyle = g; ctx.fillRect(x - 1, y, f, h);
  g = ctx.createLinearGradient(x + w, 0, x + w - f, 0); g.addColorStop(0, bg + '1)'); g.addColorStop(1, bg + '0)'); ctx.fillStyle = g; ctx.fillRect(x + w - f + 1, y, f, h);
  g = ctx.createLinearGradient(0, y, 0, y + fv); g.addColorStop(0, bg + '1)'); g.addColorStop(1, bg + '0)'); ctx.fillStyle = g; ctx.fillRect(x, y - 1, w, fv);
  g = ctx.createLinearGradient(0, y + h, 0, y + h - fv); g.addColorStop(0, bg + '1)'); g.addColorStop(1, bg + '0)'); ctx.fillStyle = g; ctx.fillRect(x, y + h - fv + 1, w, fv);
}
function draw() {
  const p = heroP;
  ctx.fillStyle = '#f5eee5'; ctx.fillRect(0, 0, cv.width, cv.height);
  if (frames.length) {
    const i = Math.min(frames.length - 1, Math.round(p * (frames.length - 1)));
    let im = frames[i];
    if (!im.complete || !im.naturalWidth) { // ближайший загруженный
      for (let k = 1; k < frames.length; k++) { const a = frames[i - k], b = frames[i + k]; if (a && a.complete && a.naturalWidth) { im = a; break; } if (b && b.complete && b.naturalWidth) { im = b; break; } }
    }
    if (im.complete && im.naturalWidth) { const r = place(im); ctx.drawImage(im, ...r); feather(r); }
  } else {
    [0, 1].forEach(k => { const im = still[k]; if (!im.complete || !im.naturalWidth) return; ctx.globalAlpha = k ? p : 1; const r = place(im); ctx.drawImage(im, ...r); ctx.globalAlpha = 1; feather(r); });
    ctx.globalAlpha = 1;
  }
  // мягкая виньетка в цвет страницы снизу - кадр тает в фон
  const g = ctx.createLinearGradient(0, cv.height * 0.78, 0, cv.height);
  g.addColorStop(0, 'rgba(245,238,229,0)'); g.addColorStop(1, 'rgba(245,238,229,1)');
  ctx.fillStyle = g; ctx.fillRect(0, cv.height * 0.78, cv.width, cv.height * 0.22);
}
still.forEach(im => im.onload = draw);
if (frames[0]) frames[0].onload = draw;
addEventListener('resize', fit); fit();

const gFill = document.getElementById('gFill'), gLbl = document.getElementById('gLbl');
let target = 0;
ScrollTrigger.create({
  trigger: '.hero', start: 'top top', end: 'bottom bottom',
  onUpdate: s => { target = gsap.utils.clamp(0, 1, (s.progress - 0.06) / 0.8); }
});
gsap.ticker.add(() => {
  heroP += (target - heroP) * 0.14;
  if (Math.abs(target - heroP) < 0.0005) heroP = target;
  const f = Math.round(heroP * 1000);
  if (f !== shown) {
    shown = f; draw();
    gFill.style.transform = `scaleX(${heroP})`;
    gLbl.textContent = heroP < 0.04 ? 'Рукав надет' : heroP > 0.97 ? 'Сел по форме' : 'Термотоннель';
  }
});
shrinkTitle(document.getElementById('h1'), 151, 62, { trigger: '.hero', start: 'top top', end: '70% bottom' });
gsap.to('.hero-copy .lead, .cue', { opacity: 0, scrollTrigger: { trigger: '.hero', start: '55% bottom', end: '80% bottom', scrub: true } });
gsap.to('.hero-copy', { yPercent: -18, opacity: 0, scrollTrigger: { trigger: '.hero', start: '82% bottom', end: 'bottom bottom', scrub: true } });

/* 2. принцип: слова проявляются */
const st = document.getElementById('statement');
st.innerHTML = st.textContent.split(' ').map(w => `<span class="w">${w}</span>`).join(' ');
const words = [...st.querySelectorAll('.w')];
ScrollTrigger.create({ trigger: st, start: 'top 82%', end: 'bottom 45%', onUpdate: s => { const n = Math.round(s.progress * words.length); words.forEach((w, i) => w.classList.toggle('on', i < n)); } });

/* 3. витрина */
const lis = [...document.querySelectorAll('#vList li')], imgs = [...document.querySelectorAll('.v-media img')], metas = [...document.querySelectorAll('#vMeta article')];
let cur = 0, auto = true, inView = false;
function pickItem(i) {
  cur = i;
  [lis, imgs, metas].forEach(arr => arr.forEach((el, k) => el.classList.toggle('on', k === i)));
}
lis.forEach((li, i) => {
  const b = li.querySelector('button');
  b.addEventListener('click', () => { auto = false; pickItem(i); });
  b.addEventListener('mouseenter', () => { if (!mobile()) { auto = false; pickItem(i); } });
});
ScrollTrigger.create({ trigger: '.vitrine', start: 'top 70%', end: 'bottom 30%', onToggle: s => { inView = s.isActive; } });
setInterval(() => { if (auto && inView && !document.hidden) pickItem((cur + 1) % lis.length); }, 4200);
gsap.from('.v-list li', { opacity: 0, y: 24, stagger: 0.06, duration: 0.8, ease: 'power3.out', scrollTrigger: { trigger: '.vitrine', start: 'top 80%' } });

/* 4. подбор плёнки */
const k = document.getElementById('k'), kVal = document.getElementById('kVal'), verdict = document.getElementById('verdict');
const vName = document.getElementById('vName'), vText = document.getElementById('vText');
const bPath = document.getElementById('bPath'), sPath = document.getElementById('sPath'), cap = document.getElementById('cap');
let kShow = 1.6;
function bottle(kk) {
  const cx = 130, neck = 30, half = Math.min(112, neck * kk) , top = 46, sh = 110 + (half - neck) * 0.55, base = 404;
  const body = `M${cx - neck},${top} L${cx - neck},${sh - 46} C${cx - neck},${sh - 10} ${cx - half},${sh - 20} ${cx - half},${sh + 24} L${cx - half},${base - 16} Q${cx - half},${base} ${cx - half + 16},${base} L${cx + half - 16},${base} Q${cx + half},${base} ${cx + half},${base - 16} L${cx + half},${sh + 24} C${cx + half},${sh - 20} ${cx + neck},${sh - 10} ${cx + neck},${sh - 46} L${cx + neck},${top} Z`;
  // рукав облегает от горла до низа (с запасом 4 px)
  const n2 = neck + 3, h2 = half + 3, s0 = top + 22;
  const sleeve = `M${cx - n2},${s0} L${cx - n2},${sh - 46} C${cx - n2},${sh - 10} ${cx - h2},${sh - 20} ${cx - h2},${sh + 24} L${cx - h2},${base - 26} L${cx + h2},${base - 26} L${cx + h2},${sh + 24} C${cx + h2},${sh - 20} ${cx + n2},${sh - 10} ${cx + n2},${sh - 46} L${cx + n2},${s0} Z`;
  bPath.setAttribute('d', body); sPath.setAttribute('d', sleeve); document.getElementById('sShade').setAttribute('d', sleeve);
  cap.setAttribute('x', cx - neck - 4); cap.setAttribute('y', top - 28); cap.setAttribute('width', (neck + 4) * 2); cap.setAttribute('height', 30);
}
function updK() {
  const v = parseFloat(k.value);
  kVal.textContent = v.toFixed(1).replace('.', ',');
  k.style.setProperty('--p', ((v - k.min) / (k.max - k.min) * 100) + '%');
  const pet = v > 2;
  verdict.classList.toggle('pet', pet);
  vName.textContent = pet ? 'PET' : 'PVC';
  vText.textContent = pet ? 'Для узкогорлых бутылок, например под шампанское. Усаживается до 70-75 %.' : 'Недорогая и практичная плёнка. Усаживается до 50-53 %.';
    gsap.to({ v: kShow }, { v, duration: 0.5, ease: 'power3.out', onUpdate() { kShow = this.targets()[0].v; bottle(kShow); } });
}
k.addEventListener('input', updK); bottle(kShow); updK();

/* 5. цикл: горизонтальная лента */
const track = document.getElementById('track');
const dist = () => Math.max(0, track.scrollWidth - innerWidth);
gsap.to(track, {
  x: () => -dist(), ease: 'none',
  scrollTrigger: { trigger: '#cyclePin', start: 'top top', end: () => '+=' + dist(), pin: true, scrub: 0.6, invalidateOnRefresh: true }
});

/* 6. дизайн: печатные формы сходятся в изображение */
const sep = [['.plate.c', -70, -30], ['.plate.m', 60, 40], ['.plate.y', 20, -60]];
sep.forEach(([sel, x, y]) => gsap.fromTo(sel, { x, y, opacity: 0.85 }, { x: 0, y: 0, opacity: 1, ease: 'none', scrollTrigger: { trigger: '#sep', start: 'top 85%', end: 'center 45%', scrub: 0.8 } }));

/* 7. годы и условия */
gsap.utils.toArray('.years li, .t-grid article').forEach((el, i) => gsap.from(el, { opacity: 0, y: 30, duration: 0.9, ease: 'power3.out', delay: (i % 4) * 0.08, scrollTrigger: { trigger: el, start: 'top 88%' } }));

/* 8. заявка */
shrinkTitle(document.getElementById('h2c'), 151, 78, { trigger: '#contact', start: 'top 85%', end: 'top 25%' });
document.getElementById('form').addEventListener('submit', e => {
  e.preventDefault();
  const f = e.target;
  if (!f.contact.value.trim()) { f.contact.focus(); return; }
  document.getElementById('ok').hidden = false;
});

addEventListener('load', () => ScrollTrigger.refresh());

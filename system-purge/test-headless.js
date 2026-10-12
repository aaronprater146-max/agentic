// Headless harness for SYSTEM PURGE — boots the real game JS in Node with
// stubbed DOM/canvas/audio, drives the nuke-ritual chain, reports PASS/FAIL.
// Usage: node test-headless.js
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const HTML = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const scripts = [...HTML.matchAll(/<script>([\s\S]*?)<\/script>/g)];
if (scripts.length !== 1) { console.error('expected 1 inline script, found', scripts.length); process.exit(2); }
const code = scripts[0][1] + '\n;globalThis.__EVAL=s=>eval(s);';

// ---------- stubs ----------
function makeCtx() {
  return new Proxy({}, {
    get(t, k) {
      if (k === 'measureText') return () => ({ width: 10 });
      if (k === 'createRadialGradient' || k === 'createLinearGradient')
        return () => ({ addColorStop() {} });
      if (k === 'createPattern') return () => ({});
      if (k === 'getImageData') return () => ({ data: { length: 0 } });
      if (k === 'createImageData') return (w, h) => ({ data: new Uint8ClampedArray(w * h * 4), width: w, height: h });
      return (...a) => {};
    },
    set() { return true; }
  });
}
function makeEl() {
  const el = {
    style: {}, dataset: {}, children: [], width: 300, height: 150,
    textContent: '', innerHTML: '', value: '', checked: false, disabled: false,
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, f) {
        if (f === undefined) this._s.has(c) ? this._s.delete(c) : this._s.add(c);
        else f ? this._s.add(c) : this._s.delete(c);
      },
      contains(c) { return this._s.has(c); }
    },
    addEventListener() {}, removeEventListener() {},
    appendChild(c) { el.children.push(c); }, remove() {},
    prepend(c) { el.children.unshift(c); }, append(c) { el.children.push(c); },
    before() {}, after() {}, replaceWith() {},
    cloneNode() { return makeEl(); },
    parentNode: { replaceChild() {}, appendChild() {}, removeChild() {} },
    setAttribute() {}, getAttribute() { return null; },
    querySelector() { return makeEl(); }, querySelectorAll() { return []; },
    getContext() { return makeCtx(); },
    getBoundingClientRect() { return { left: 0, top: 0, width: 300, height: 150 }; },
    click() {}, focus() {}, blur() {}
  };
  return el;
}
const elCache = {};
const store = {};
class StubAC {
  constructor() {
    this.currentTime = 0; this.state = 'running';
    this.sampleRate = 44100; this.destination = {};
    return new Proxy(this, {
      get(t, k) {
        if (k in t) return t[k];
        if (k === 'createBuffer') return () => ({ getChannelData: () => new Float32Array(128), sampleRate: 44100 });
        return (...a) => U;
      },
      set() { return true; }
    });
  }
  resume() {} suspend() {}
}
const U = new Proxy(function () {}, { get: () => U, set: () => true, apply: () => U });

const sandbox = {
  console,
  performance,
  setTimeout, clearTimeout, setInterval, clearInterval,
  localStorage: {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; }
  },
  requestAnimationFrame: () => 0,
  cancelAnimationFrame: () => {},
  addEventListener: () => {}, removeEventListener: () => {},
  innerWidth: 1280, innerHeight: 720, devicePixelRatio: 2,
  Audio: function () { return { play() {}, pause() {} }; },
  document: {
    getElementById: id => (elCache[id] || (elCache[id] = makeEl())),
    createElement: () => makeEl(),
    querySelector: () => makeEl(), querySelectorAll: () => [],
    body: makeEl(),
    addEventListener: () => {}, removeEventListener: () => {},
    hidden: false, activeElement: null
  },
  navigator: {},
  location: {},
  matchMedia: () => ({ matches: false, addEventListener() {} })
};
sandbox.window = sandbox;
sandbox.window.AudioContext = StubAC;
sandbox.globalThis = sandbox;

const results = [];
function check(name, ok, detail) {
  results.push({ name, ok: !!ok, detail });
  console.log((ok ? 'PASS' : 'FAIL') + ' :: ' + name + (detail ? ' — ' + detail : ''));
}

process.on('uncaughtException', e => {
  console.log('FAIL :: uncaught async exception — ' + (e && e.message));
  process.exit(1);
});

// ---------- boot ----------
const ctx = vm.createContext(sandbox);
try {
  vm.runInContext(code, ctx, { filename: 'game.js' });
  check('boot (eval game script)', true);
} catch (e) {
  check('boot (eval game script)', false, e.message);
  console.log((e.stack || '').split('\n').slice(0, 6).join('\n'));
  process.exit(1);
}
const E = s => vm.runInContext('__EVAL(' + JSON.stringify(s) + ')', ctx);
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  try {
    E('globalThis.__toasts=[];toast=((o)=>(...a)=>{globalThis.__toasts.push(a[0]);return o(...a)})(toast)');
    // 1. new game -> nexus
    const spawn = E(`S.save=newSave();enterArea({area:'nexus',sec:0,lvl:1});
      [G.player.x|0,G.player.y|0,typeof update,typeof render,WORLD]`);
    check('new game boots to nexus', Array.isArray(spawn) && spawn[2] === 'function', JSON.stringify(spawn));

    // 2. isolate arena + grant ritual stats
    E(`G.enemies.length=0;G.spawnQueue.length=0;G.waveState='fighting';G.waveTimer=99999;
      G.neutrals.length=0;G.floaters.length=0;G.projs.length=0;
      G.stats.sustain=1;G.stats.bomb=1;G.stats.pal=1;
      G.player.x=1100;G.player.y=1100;`);

    // 3. build ritual: palisade + 3 bombs + 12-seg ring
    const pre = E(`const px=G.player.x,py=G.player.y;
      G.palisades.push({x:px,y:py,r:60,hp:150,max:150,life:40,shelter:true});
      for(let i=0;i<3;i++)G.bombs.push({x:px+(i-1)*30,y:py,ph:0});
      for(let i=0;i<12;i++){const a=i/12*Math.PI*2;
        G.walls.push({x:px+Math.cos(a)*150,y:py+Math.sin(a)*150,r:14,charge:0,life:30,max:30,arm:0});}
      G.__w=G.walls[0];JSON.stringify(nukeInfo(G.palisades[0]))`);
    const preInfo = JSON.parse(pre);
    check('ritual setup passes scan', preInfo.nb >= 3 && preInfo.ns >= 8 && preInfo.no >= 5, pre);

    // 4. tether-charge wall[0] to crit
    let iters = 0, outcome = 'timeout';
    for (let i = 0; i < 300; i++) {
      iters = i + 1;
      outcome = E(`(()=>{const w=G.__w;
        if(G.nuke)return 'nuke';
        if(!G.walls.includes(w))return 'crit';
        tetHit(G.player,G.stats,weapEl(),1/60,{o:w,k:'w'});
        return 'charging:'+w.charge.toFixed(2);})()`);
      if (outcome === 'nuke' || outcome === 'crit') break;
    }
    await sleep(400); // let ultraBlast timeout (if any) fire
    const post = E(`JSON.stringify({nuke:!!G.nuke,bombs:G.bombs.length,walls:G.walls.length,
      pals:G.palisades.length,toasts:globalThis.__toasts.slice(-3)})`);
    check('tether crit arms the nuke (no silent fail)', outcome === 'nuke',
      `iters=${iters} outcome=${outcome} post=${post}`);

    // 5. charge -> black hole
    if (E('!!G.nuke')) {
      let holeAt = -1;
      for (let i = 0; i < 160; i++) { E('update(1/60)'); if (E('!!G.hole')) { holeAt = i + 1; break; } }
      E('G.player.x+=600'); // step clear: no drag (>520), no magnet vacuum of the loot
      check('charge completes into black hole', holeAt > 0, 'holeAt frame ' + holeAt);
      try { E('render()'); E('render()'); check('render smoke (hole active)', true); }
      catch (e) { check('render smoke (hole active)', false, e.message); }
      // 6. implosion -> loot
      let endAt = -1;
      for (let i = 0; i < 300; i++) { E('update(1/60)'); if (E('!G.hole')) { endAt = i + 1; break; } }
      const loot = E(`JSON.stringify({carbon:G.pickups.filter(p=>p.kind==='carbon').length,
        crystal:G.pickups.filter(p=>p.kind==='crystal').length,
        omega:G.pickups.filter(p=>p.kind==='omega').length})`);
      const lj = JSON.parse(loot);
      check('implosion clears hole + drops matter', endAt > 0 && lj.carbon >= 2,
        `endAt=${endAt} loot=${loot}`);
    } else {
      check('charge completes into black hole', false, 'no G.nuke (skipped)');
      check('render smoke (hole active)', false, 'no G.nuke (skipped)');
      check('implosion clears hole + drops matter', false, 'no G.nuke (skipped)');
    }

    // 7. soak: live combat frames with attack held
    E('G.attacking=true');
    let throws = 0, firstErr = '';
    for (let i = 0; i < 400; i++) {
      try { E('update(1/60)'); if (i % 100 === 0) E('render()'); }
      catch (e) { throws++; if (!firstErr) firstErr = e.message; }
    }
    E('G.attacking=false');
    check('400-frame combat soak, no exceptions', throws === 0,
      throws ? `${throws} throws, first: ${firstErr}` : 'clean');

    const fails = results.filter(r => !r.ok);
    console.log(`\n==== ${results.length - fails.length}/${results.length} passed ====`);
    process.exit(fails.length ? 1 : 0);
  } catch (e) {
    console.log('FAIL :: harness error — ' + (e && e.stack || e));
    process.exit(1);
  }
})();

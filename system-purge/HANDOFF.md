# SYSTEM PURGE — Session Handoff (v0.26)

Single-file browser game. Everything lives in **`index.html`** (~190k chars).
Test with **`test-headless.js`** (`node test-headless.js` — must stay 8/8 green).

## 1. How to work in a new chat
- **Patch discipline**: never hand-edit game logic blind. Write `patch_vNN.py` scripts that
  `assert` exact-match counts (`count==1`) for every hunk, run, then verify:
  `node --check` on extracted JS + duplicate-`id` scan + marker grep.
- **Same-file parallel edits RACE (last write wins)** — never `edit_file`/`sed` the same
  file twice in one parallel block. This bit us twice (v0.19b `perfNow`, v0.20 precheck).
- **Boot-referenced DOM must precede `<script>`** (v0.19 lens lesson).
- **Verify with the harness** after gameplay changes: `cd system-purge && node test-headless.js`.
- Phone-first user (Englewood, Ohio, EDT). Landscape-first, must work portrait too,
  downloadable single file. Keep replies short; user plays on phone.

## 2. Current state (v0.26, all verified)
- **Firewall sustain = LIGHTSPEED TIMESTOP latch**: tap dash = instant burst (0.18s);
  hold 0.3s with Afterburner Drive = latch forever; tap dash again to cut.
  While latched: world at **0.05×** (enemy move/fire/target/lunge, enemy projs+their
  fuses, neutral drift, pickup drift), player crawls at `st.spd×0.7`, steering is
  heading-inertia gated by turn jets (`warpTurn=0.35+max(0,st.turn-3.2)×1.1`;
  base 0.35 rad/s, single Precog Lattice ≈6 rad/s "on a dime").
  Walls: seg every 12px traveled, r14, **30s life**, cap 600, spawn 26px behind tail,
  0.6s arm grace; self-damage (5) only while sustaining (currently neutered by
  sustain i-frames — see §7). Connected ribbon + arcs between segs. Blue tint,
  warp streaks, FOV stretch, motion ghosts while latched.
- **Dash chains**: sustain entry dropped the `dashCD<=0` gate — hold flows straight
  from burst into latch, no 2.2s wait.
- **Bombs**: `◉` plants only (max 3, bombCD 0.8s); separate `✸` **DETONATE** button
  above it, visible only while ≥1 bomb is down. Wall-crit with bombs down still
  detonates (+`ultraBlast` at 3+). Nuke needs exactly the planted bombs.
- **Palisade Emitter** (`pal1`, t2 weapon, 600 CPU/50 BIN/10 MD, rank 4, MD from
  Brute+Warden): `⬢` button, bubble at player pos, r60/HP150/40s life, max 3
  (oldest replaced), enemies bounce, eats all `G.projs`, hp-0 death = **NULL blast**
  (40 + NUL stun/DoT proc, new `NUL` element: `#9d8cff`, `st.nul`, frozen-like skip).
- **NUKE RITUAL** (tether-overcharge crit is the ONLY trigger — auto-arm was removed):
  3+ bombs within 120px of a palisade + 8+ wall segs within 260px + 5/8 octants →
  gold pulse on ready palisade → tether a ring seg ~2s to crit → **scan runs BEFORE
  `wallCrit`** (the v0.26 fix: crit used to eat ring+bombs first, scan always failed).
  Ritual hit skips `wallCrit`, `nukeIgnite` consumes bombs, 1.6s charge (converging
  streaks, suck particles, progress ring, shake ramp) → catalyst implodes (200 dmg,
  shockwaves) → white flash → 3.2s **black hole** (swirl pull: enemies deadly,
  player escapable ~360 max + 0.8s ramp; shelter palisade = immune; <65px = death
  + body drops 2 carbon/1 crystal/15% omega) → implosion clears enemies/projs/
  `spawnQueue` (was `G.spawnQ` crash — the v0.24 lockup) → `SECTOR STERILIZED`
  banner + loot (2+K/8 carbon, crystal K≥10, +1 K≥30, omega 5→50% K≥30).
- **REFINE economy**: forge legend shows `MATTER ◆/◈/◉` + REFINE button
  (carbon→20CPU/1BIN, crystal→150/5, omega→800/25); **24h real-time decay**
  (`matterDecay`, boot-guarded for null save since v0.26-fix).
- **Buttons gated on parts**: bomb/frz/shield/pal/seekers on `st.*`, stealth on
  Cloak Weave **mod** (`st.cloak`), detonate on bombs-down. Dash/attack always
  (base). Seeker indicator is `▲` (no emoji).
- **Lens**: SVG `feDisplacementMap` barrel lens over `.screen`, HIGH/LOW/OFF user
  toggle, ignores perf system (only user toggle disables). Scan nameplate UI for
  nearest struct (window-first, pointer line window→object).
- **SFX-only** (music removed): WebAudio synth, VOXMAX=36, everything reverberant;
  nuke set = `nukeArm/nukeCharge/holeLoop/nukeBoom` (massive layered).
- **Harness** `test-headless.js`: vm-sandbox boot + ritual chain + render smoke +
  400-frame soak. **8/8 green at v0.26 (verified 2x consecutive).** Game bugs it has caught: `G.beams`
  (never init'd), `perfNow` (undefined), `G.spawnQ`→`spawnQueue`, bare `save()`→
  `persist()` (×3), `matterDecay` null-save boot crash. Harness stubs that were
  added along the way: `querySelectorAll`, `createImageData`, el `prepend/append/cloneNode` + stub `parentNode`,
  `StubAC` audio, explicit `process.exit` (game leaves a live interval).

## 3. Standing user constraints (do not regress)
- Phone-first; landscape-first, portrait must work; single downloadable file.
- No `CP` abbreviation; no persistent in-world explanatory text (only contextual
  area names + ENTER SOURCE/PORT/TRAVEL states). SOURCE in Nexus, PORT elsewhere.
- Map upper-right → pause map with EXIT / RETURN TO SOURCE; stats below map;
  vertical zoom slider left of map; options live in map/source/port menus, not HUD.
- Small buttons; attack radius only while holding attack.
- Dark gritty horror (Tron/ReBoot/Matrix); firewall pulses 1s, never upgradeable.
- **SFX-only**; best quality; glitchy/staticy; cloak = Halo-style; DERESOLUTION
  death screen w/ sub-bass; recompile / back-to-source / exit-to-menu.
- Main menu needs CREDITS (legal/attribution). Default triangle hull; user color
  wheel for hull/tool/core. VCR OSD font look (mono+tracking+glow+hard shadow).
- Map menu shows inventory; pickups show abbreviated +N labels.
- Nexus wave-3 miniboss gates sector 1; sector doors random; nothing overlaps
  doors/ports/source; SOURCE has VIRUS DEFINITIONS bestiary.
- Forge: no SIZE option; fixed triangle mounts only (3 weapon nose/side points,
  2 turn side-midpoints, 1 rear thrust, 1 core); tap anchor node → then EQUIP/BUY/
  SELL/REPLICATE (symbols only: ⊕ $ ⊖ ∞ ▲); one-view layout, only parts box scrolls;
  viewport upper-left + stats under, attachments right, description bottom-left.
- Start: nose tether only, no thrust/turn jets, slow base. Shield button only with
  Palisade Node on CORE; shield break = radial electro-blast.
- Only Sector 1 (3 sublevels) playable; S2/S3/Partition 2 sealed; prime boss wave 10.
- No center-screen spam: subtle transparent log upper-left with OFF toggle.
- Glitches must not hurt framerate (auto quality OK); **lens ignores perf**.
- v0.20-batch decisions still binding: sustain gated by Afterburner Drive (THRUST);
  shelter palisades immune to hole/nuke; bosses die to hole; detonate() untouched.

## 4. Architecture map (`index.html`, approx line nos. at v0.26)
- Boot: settings/load (`S={set,save}` ~724), `newSave()` 716, boot calls incl.
  `matterDecay()` (null-guarded), `requestAnimationFrame(loop)` 1122.
- `enterArea(loc,resume,spawn)` 860: builds `G={...}` 865
  (`enemies,projs,pickups,parts,structs,neutrals,floaters,bombs,msls,flares,
  walls,palisades,spawnQueue,...`), player, `stats:playerStats()`.
- `update(dt)` 1124: player/dash/sustain (~1136–1156), nuke+hole (~1199–1242),
  targeting+`fireBeam` (~1262–1284), enemies (~1311+), projs/neutrals/pickups/parts.
- `render()` 1503: camera world pass (walls ribbon+arcs+segs, palisades+ready ring+
  progress ring, hole, pickups incl. carbon/crystal/omega, bombs, …), screen pass
  (`lensPass` + sustain blue tint).
- Combat: `tetHit` 1418 (`k:'w'` wall charge 0.5/s → crit branch w/ scan-first),
  `wallCrit` (splice + 110px chain + bomb-detonate/ultraBlast link), `dealDot`,
  `enemyShoot` 1431 (`e.atkCD`), `hurtEnemy/hurtPlayer`, `killEnemy`,
  `applyStatus` (NUL→`st.nul=3`), `statusTick` (NUL DoT + `wallCD` decay).
- Nuke fns ~1990–2080: `doPal`, `palBlast`, `nukeInfo/nukeScan`, `nukeIgnite`,
  `holeSpawn`, `holeLoot`, `holeDeathDrop`, `matterGain/matterDecay/renderMatter/
  refineMatter`, `ultraBlast`, `doBomb/doDetonate/detonate`.
- Slow-mo sites: slowE/wmo/pdt `?0.05:1`, enemy timers `wts`, neutrals `nwts`,
  pickups `pkts`, `pr.life-=pdt`.
- Forge/UI: parts `PARTS` (~600–660, `pal1` after `frz1`), `refreshSpecBtns` 1933,
  bindings ~1968–1976, `updateForgeRes` + `renderMatter`, legend row w/ matterLine
  + REFINE. Buttons CSS ~90–125, HTML ~284–291.
- Audio: `AC`/`audio()` 382–385, `T()` 397 (try-wrapped), `BR/NZ/CRS/WOB/GL`,
  `SFX={...}` (~430–480, incl. nuke set), VOXMAX 36.

## 5. Ritual recipe (tell the user)
Latch sustain → crawl ring around palisade → plant 3 bombs inside → **gold pulse** =
ready → hold attack near ring (~2s tether to crit) → shelter in 2nd palisade or
keep 300px+ clear → loot + REFINE in forge. Crit with no ritual → progress toast
`RITUAL nb/3 · ns/8 · no/5`.

## 6. Patch files (workspace root, applied — do NOT rerun)
`patch_v04…patch_v25.py` = ordered history v0.4→v0.26 (names lag versions:
v19a/v19b→v0.20, v20→v0.21, v21→v0.22, v22→v0.23, v23→v0.24, v24→v0.25,
v25→v0.26). Plus 3 unscripted micro-fixes in v0.26 cycle: `matterDecay`
null-guard, `;save()`→`;persist()` ×3 (via sed).

## 7. Known issues / open threads
- Sustain self-damage (5/hit while sustaining) is likely neutered by the
  per-frame sustain i-frame refresh (`p.hitCD=max(...,0.12)`) — same refresh also
  makes the player untouchable while latched. User hasn't complained; timestop +
  untouchable is arguably the fantasy. Touch only if asked.
- `SFX.derez()` inside `die()`/SFX chains and `zapStart/zapWatch` are audio-stubbed
  in harness but untested with real AudioContext — browser-ear check pending.
- Balance: hole kill credit `H.kills` only counts <70px derezzes, not implosion
  clears (implosion victims give no loot scaling — intended "bonus loot drops
  remain" but they don't drop; only `holeLoot` table). Revisit if user complains.
- `G.nuke.hot` holds wall refs; ring segs aging out mid-charge are skipped safely
  (`indexOf` guard) but shorten visuals. Fine.

## 8. External sources (licenses matter for CREDITS)
- Sonniss GDC bundles (royalty-free, no attribution) — recommended, not downloaded.
- Eric Matyas soundimage.org sci-fi-6/7 (royalty-free, attribution required) —
  v0.2 menu/combat URLs (MUSIC REMOVED since; SFX-only now).
- Kenney CC0, Freesound (CC0 filter), Pixabay (no-attribution), Incompetech (CC-BY),
  OpenGameArt per-item, OwlishMedia CC0 pack — candidates only.
- Lens refs: valerie.desnoux.free.fr/pano (stereographic), naturettl.com (fisheye).

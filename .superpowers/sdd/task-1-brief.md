### Task 1: Host-side fbOk / selectThetaEst (TDD)

**Files:**
- Modify: `transwing_lua_mix_model.mjs`
- Modify: `transwing_lua_mix_model.test.mjs`

**Interfaces:**
- Produces:
  - `fbOk({ en, havePct, lastRxMs, nowMs, staleMs, flt, hld }) 鈫?boolean`
  - `foldPctToTheta(foldPct, thetaMax) 鈫?number`锛坧ct clamp 0鈥?00锛?  - `selectThetaEst({ fbOk, foldPct, thetaMax, thetaOl }) 鈫?{ thetaEst, thetaOl }`锛坒b 鏃跺榻?ol锛?
- [ ] **Step 1: Write failing tests**

Append to `transwing_lua_mix_model.test.mjs`:

```js
import { fbOk, foldPctToTheta, selectThetaEst } from "./transwing_lua_mix_model.mjs";

test("fbOk requires enable, havePct, fresh rx, and clear flt/hld", () => {
  const base = { en: true, havePct: true, lastRxMs: 1000, nowMs: 1500, staleMs: 1000, flt: 0, hld: 0 };
  assert.equal(fbOk(base), true);
  assert.equal(fbOk({ ...base, en: false }), false);
  assert.equal(fbOk({ ...base, havePct: false }), false);
  assert.equal(fbOk({ ...base, nowMs: 2501 }), false);
  assert.equal(fbOk({ ...base, flt: 1 }), false);
  assert.equal(fbOk({ ...base, hld: 1 }), false);
});

test("foldPctToTheta maps 0-100 onto thetaMax", () => {
  assert.equal(foldPctToTheta(0, 90), 0);
  assert.equal(foldPctToTheta(50, 90), 45);
  assert.equal(foldPctToTheta(100, 90), 90);
  assert.equal(foldPctToTheta(-10, 90), 0);
  assert.equal(foldPctToTheta(120, 90), 90);
});

test("selectThetaEst uses feedback and aligns open-loop when fbOk", () => {
  const withFb = selectThetaEst({ fbOk: true, foldPct: 50, thetaMax: 90, thetaOl: 10 });
  assert.equal(withFb.thetaEst, 45);
  assert.equal(withFb.thetaOl, 45);

  const ol = selectThetaEst({ fbOk: false, foldPct: 50, thetaMax: 90, thetaOl: 12 });
  assert.equal(ol.thetaEst, 12);
  assert.equal(ol.thetaOl, 12);
});
```

- [ ] **Step 2: Run tests 鈥?expect FAIL**

```bash
node --test transwing_lua_mix_model.test.mjs
```

Expected: FAIL锛坄fbOk` / `foldPctToTheta` / `selectThetaEst` not exported锛?
- [ ] **Step 3: Implement pure functions**

Add to `transwing_lua_mix_model.mjs`:

```js
export function fbOk({ en, havePct, lastRxMs, nowMs, staleMs, flt, hld }) {
  if (!en) return false;
  if (!havePct) return false;
  if (lastRxMs == null || nowMs == null) return false;
  if ((nowMs - lastRxMs) > staleMs) return false;
  if (Number(flt) === 1) return false;
  if (Number(hld) === 1) return false;
  return true;
}

export function foldPctToTheta(foldPct, thetaMax) {
  const pct = clamp(Number(foldPct), 0, 100);
  return (pct / 100) * thetaMax;
}

export function selectThetaEst({ fbOk: ok, foldPct, thetaMax, thetaOl }) {
  if (!ok) {
    return { thetaEst: thetaOl, thetaOl };
  }
  const thetaEst = foldPctToTheta(foldPct, thetaMax);
  return { thetaEst, thetaOl: thetaEst };
}
```

- [ ] **Step 4: Run tests 鈥?expect PASS**

```bash
node --test transwing_lua_mix_model.test.mjs
```

Expected: PASS锛堝惈鏂版祴渚嬶級

- [ ] **Step 5: Commit**

```bash
git add transwing_lua_mix_model.mjs transwing_lua_mix_model.test.mjs
git commit -m "test: add fold MAVLink feedback theta selection helpers"
```

---


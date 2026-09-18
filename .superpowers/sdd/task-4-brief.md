### Task 4: Docs sync

**Files:**
- Modify: `Transwing_鎶樺彔鎵ц鍣╛MAVLink鍥炰紶璇存槑.md`
- Modify: `Transwing_Lua_鍔ㄦ€佹贩鎺т豢鐪熻鏄?md`
- Modify: `knowledge-base/README.md` / `knowledge-base/index.yaml`锛堜粎褰撶储寮曟湭閾惧埌鍥炰紶璇存槑鎴栧弽棣堝弬鏁版椂锛?
- [ ] **Step 1: Update MAVLink 鍥炰紶璇存槑 搂4 / 搂6**

- 搂4 琛細銆屾帴鏉垮悗鐩爣銆嶆敼涓恒€屽凡瀹炵幇浜?`transwing_dynamic_mix.lua`锛坄TW_FB_*`锛夈€?- 搂6 楠屾敹娓呭崟锛氭妸 Lua 宸ョ▼椤规爣涓鸿剼鏈晶宸叉敮鎸侊紝鍙版灦椤逛繚鐣欎汉宸ュ嬀閫?
- [ ] **Step 2: Update Lua 浠跨湡璇存槑**

澧炲姞鍙傛暟琛ㄨ锛?
| `TW_FB_EN` | 1 | 鍚敤鎶樺彔鍔犻 |
| `TW_FB_REQ` | 1 | 鏃犲弽棣堢姝?CONTROL |
| `TW_FB_STALE` | 1000 | 鍙嶉瓒呮椂 ms |
| `TW_THETA_MAX` | 90 | pct鈫掑害婊¤绋?|

鍐欐槑锛歚theta_est` 浼樺厛 `fold_pct`锛涘け鏁堝洖閫€ `TW_RATE_*` 寮€鐜紱CONTROL 鍐欒埖鏈轰粛鐢ㄦ寚浠?slew 瑙掋€?
- [ ] **Step 3: Commit**

```bash
git add "Transwing_鎶樺彔鎵ц鍣╛MAVLink鍥炰紶璇存槑.md" "Transwing_Lua_鍔ㄦ€佹贩鎺т豢鐪熻鏄?md" knowledge-base/README.md knowledge-base/index.yaml
git commit -m "docs: document Lua fold MAVLink feedback path"
```

---


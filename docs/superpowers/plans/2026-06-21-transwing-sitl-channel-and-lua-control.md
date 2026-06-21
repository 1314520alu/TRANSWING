# Transwing SITL Channel and Lua Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current Transwing SITL physics model, Lua dynamic mixer, and parameter files match the agreed channel contract, then verify that match from source and runtime evidence.

**Architecture:** Keep the existing Transwing channel contract. Replace the incorrect inherited fixed-wing force path in `SIM_TranswingQuadPlane` with a Transwing-specific aerodynamic input mapper that reads `SERVO5-10`, while preserving the existing motor/fold geometry layer on `SERVO1-4` and `SERVO11`. Add Lua `TW_MIX_MODE` so dynamic motor mix moves from observe, to mirror, to real `SERVO1-4` authority explicitly.

**Tech Stack:** ArduPilot SITL C++ in WSL at `/home/alu/ardupilot`, Lua script in `C:/Users/alu/Desktop/TRANSWING/scripts`, Node/Python-style static verification scripts in this repo, SITL build via `./waf` or `sim_vehicle.py`.

---

## File Structure

- Modify: `/home/alu/ardupilot/libraries/SITL/SIM_Plane.h`
  - Expose `getForce()`, `getTorque()`, and `calculate_forces()` to derived classes if needed. Current file already has them under `protected`, so only touch this if compilation proves access is blocked.
- Modify: `/home/alu/ardupilot/libraries/SITL/SIM_TranswingQuadPlane.h`
  - Declare Transwing-specific aerodynamic helper functions and constants.
- Modify: `/home/alu/ardupilot/libraries/SITL/SIM_TranswingQuadPlane.cpp`
  - Stop calling `Plane::calculate_forces(input, rot_accel)`.
  - Add fixed-wing aerodynamic calculation from `SERVO5-10`.
  - Keep motor/fold calculation from `SERVO1-4` and `SERVO11`.
- Modify: `C:/Users/alu/Desktop/TRANSWING/scripts/transwing_dynamic_mix.lua`
  - Add `TW_MIX_MODE`.
  - Preserve `TW_LOG_ONLY` compatibility.
  - Implement modes 0, 1, and 2.
- Modify: `C:/Users/alu/Desktop/TRANSWING/transwing_lua_sitl.params`
  - Add `TW_MIX_MODE,0` or `TW_MIX_MODE,1` for safe default.
- Modify: `C:/Users/alu/Desktop/TRANSWING/transwing_sitl_mp.params`
  - Add `TW_MIX_MODE,0` for visual SITL safety.
- Modify: `C:/Users/alu/Desktop/TRANSWING/transwing_sitl_startup.params`
  - Keep the channel contract unchanged.
- Create: `C:/Users/alu/Desktop/TRANSWING/tools/verify_transwing_mapping.py`
  - Static verifier for source and parameter mapping.
- Create: `C:/Users/alu/Desktop/TRANSWING/patches/ardupilot-transwing-channel-map-and-lua-control.patch`
  - Export patch for the WSL ArduPilot changes so the repo records exactly what changed outside the workspace.

---

## Task 1: Add Source Mapping Verifier

**Files:**
- Create: `tools/verify_transwing_mapping.py`
- Test: run verifier against current source before code changes

- [ ] **Step 1: Write the failing verifier**

Create `tools/verify_transwing_mapping.py` with this content:

```python
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ARDUPILOT = Path("/home/alu/ardupilot")

TRANSWING_CPP = ARDUPILOT / "libraries/SITL/SIM_TranswingQuadPlane.cpp"
TRANSWING_H = ARDUPILOT / "libraries/SITL/SIM_TranswingQuadPlane.h"
LUA = ROOT / "scripts/transwing_dynamic_mix.lua"
PARAMS = [
    ROOT / "transwing_sitl_startup.params",
    ROOT / "transwing_sitl_mp.params",
    ROOT / "transwing_lua_sitl.params",
]

EXPECTED_FUNCTIONS = {
    "SERVO1_FUNCTION": "33",
    "SERVO2_FUNCTION": "34",
    "SERVO3_FUNCTION": "35",
    "SERVO4_FUNCTION": "36",
    "SERVO5_FUNCTION": "4",
    "SERVO6_FUNCTION": "4",
    "SERVO7_FUNCTION": "19",
    "SERVO8_FUNCTION": "19",
    "SERVO9_FUNCTION": "21",
    "SERVO10_FUNCTION": "21",
    "SERVO11_FUNCTION": "41",
}


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def normalize_param_lines(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[\s,]+", line)
        if len(parts) >= 2:
            found[parts[0]] = parts[1]
    return found


def assert_param_contract() -> None:
    for path in PARAMS:
        params = normalize_param_lines(read(path))
        if path.name == "transwing_lua_sitl.params":
            assert params.get("SERVO13_FUNCTION") == "94", f"{path}: SERVO13 mirror missing"
            assert params.get("SERVO14_FUNCTION") == "95", f"{path}: SERVO14 mirror missing"
            assert params.get("SERVO15_FUNCTION") == "96", f"{path}: SERVO15 mirror missing"
            assert params.get("SERVO16_FUNCTION") == "97", f"{path}: SERVO16 mirror missing"
            continue
        for name, value in EXPECTED_FUNCTIONS.items():
            assert params.get(name) == value, f"{path}: expected {name}={value}, got {params.get(name)}"


def assert_cpp_contract() -> None:
    cpp = read(TRANSWING_CPP)
    header = read(TRANSWING_H)

    assert "constexpr uint8_t MOTOR_SERVO_OFFSET = 0" in cpp, "motors must start at SERVO1"
    assert "constexpr uint8_t FOLD_SERVO_IDX = 10" in cpp, "fold must read SERVO11"
    assert "calculate_forces(input, rot_accel)" not in cpp, "Transwing must not call Plane::calculate_forces(input)"
    assert "calculate_transwing_aero_forces" in cpp, "Transwing aero force helper missing"
    assert "AILERON_SERVO_A_IDX = 4" in cpp, "aileron must read SERVO5"
    assert "AILERON_SERVO_B_IDX = 5" in cpp, "aileron must read SERVO6"
    assert "ELEVATOR_SERVO_A_IDX = 6" in cpp, "elevator must read SERVO7"
    assert "ELEVATOR_SERVO_B_IDX = 7" in cpp, "elevator must read SERVO8"
    assert "RUDDER_SERVO_A_IDX = 8" in cpp, "rudder must read SERVO9"
    assert "RUDDER_SERVO_B_IDX = 9" in cpp, "rudder must read SERVO10"
    assert "calculate_transwing_aero_forces" in header, "header declaration missing"


def assert_lua_contract() -> None:
    lua = read(LUA)
    assert '"MIX_MODE"' in lua, "TW_MIX_MODE parameter missing"
    assert "local MIX_MODE_OBSERVE = 0" in lua, "observe mode constant missing"
    assert "local MIX_MODE_MIRROR = 1" in lua, "mirror mode constant missing"
    assert "local MIX_MODE_CONTROL = 2" in lua, "control mode constant missing"
    assert "SRV_Channels:set_output_pwm(32 + i" in lua, "control mode must write SERVO1-4 functions 33-36"
    assert "SRV_Channels:set_output_pwm(93 + i" in lua, "mirror mode must write Scripting1-4"


def main() -> int:
    checks = [
        assert_param_contract,
        assert_cpp_contract,
        assert_lua_contract,
    ]
    failures = []
    for check in checks:
        try:
            check()
        except Exception as exc:
            failures.append(f"{check.__name__}: {exc}")
    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run verifier and confirm RED**

Run from `C:/Users/alu/Desktop/TRANSWING`:

```powershell
python tools\verify_transwing_mapping.py
```

Expected: FAIL mentioning at least:

- `Transwing must not call Plane::calculate_forces(input)`
- `TW_MIX_MODE parameter missing`
- control mode missing `SERVO1-4` writes

---

## Task 2: Fix Transwing SITL Aerodynamic Mapping

**Files:**
- Modify: `/home/alu/ardupilot/libraries/SITL/SIM_TranswingQuadPlane.h`
- Modify: `/home/alu/ardupilot/libraries/SITL/SIM_TranswingQuadPlane.cpp`
- Test: `python tools\verify_transwing_mapping.py`

- [ ] **Step 1: Update the header declarations**

In `/home/alu/ardupilot/libraries/SITL/SIM_TranswingQuadPlane.h`, add these private methods:

```cpp
    float paired_servo_angle(const struct sitl_input &input,
                             uint8_t first_idx,
                             uint8_t second_idx);
    void calculate_transwing_aero_forces(const struct sitl_input &input,
                                         Vector3f &rot_accel,
                                         Vector3f &body_accel);
```

They belong in the existing `private:` section next to `fold_theta_deg()` and `calculate_transwing_forces()`.

- [ ] **Step 2: Add surface channel constants**

In `/home/alu/ardupilot/libraries/SITL/SIM_TranswingQuadPlane.cpp`, add these constants near `MOTOR_SERVO_OFFSET` and `FOLD_SERVO_IDX`:

```cpp
constexpr uint8_t AILERON_SERVO_A_IDX = 4;   // SERVO5_FUNCTION=4
constexpr uint8_t AILERON_SERVO_B_IDX = 5;   // SERVO6_FUNCTION=4
constexpr uint8_t ELEVATOR_SERVO_A_IDX = 6;  // SERVO7_FUNCTION=19
constexpr uint8_t ELEVATOR_SERVO_B_IDX = 7;  // SERVO8_FUNCTION=19
constexpr uint8_t RUDDER_SERVO_A_IDX = 8;    // SERVO9_FUNCTION=21
constexpr uint8_t RUDDER_SERVO_B_IDX = 9;    // SERVO10_FUNCTION=21
```

- [ ] **Step 3: Implement paired surface input and aero force calculation**

Add these methods after `fold_theta_deg()`:

```cpp
float TranswingQuadPlane::paired_servo_angle(const struct sitl_input &input,
                                             uint8_t first_idx,
                                             uint8_t second_idx)
{
    return 0.5f * (filtered_servo_angle(input, first_idx) + filtered_servo_angle(input, second_idx));
}

void TranswingQuadPlane::calculate_transwing_aero_forces(const struct sitl_input &input,
                                                         Vector3f &rot_accel,
                                                         Vector3f &body_accel)
{
    const float aileron = paired_servo_angle(input, AILERON_SERVO_A_IDX, AILERON_SERVO_B_IDX);
    const float elevator = paired_servo_angle(input, ELEVATOR_SERVO_A_IDX, ELEVATOR_SERVO_B_IDX);
    const float rudder = paired_servo_angle(input, RUDDER_SERVO_A_IDX, RUDDER_SERVO_B_IDX);
    constexpr float fixed_wing_thrust = 0.0f;

    angle_of_attack = atan2f(velocity_air_bf.z, velocity_air_bf.x);
    beta = atan2f(velocity_air_bf.y, velocity_air_bf.x);

    const Vector3f force = getForce(aileron, elevator, rudder);
    rot_accel = getTorque(aileron, elevator, rudder, fixed_wing_thrust, force);
    body_accel = force / mass;
}
```

- [ ] **Step 4: Replace the inherited force call**

Change `TranswingQuadPlane::update()` from:

```cpp
    Vector3f rot_accel;
    calculate_forces(input, rot_accel);
```

to:

```cpp
    Vector3f rot_accel;
    Vector3f aero_accel_body;
    calculate_transwing_aero_forces(input, rot_accel, aero_accel_body);
```

Then change:

```cpp
    accel_body += quad_accel_body;
```

to:

```cpp
    accel_body = aero_accel_body + quad_accel_body;
```

- [ ] **Step 5: Run verifier and confirm remaining Lua failure**

Run:

```powershell
python tools\verify_transwing_mapping.py
```

Expected: C++ mapping failures are gone. Lua failures remain until Task 3.

---

## Task 3: Add Lua `TW_MIX_MODE` and Real Motor Control Mode

**Files:**
- Modify: `scripts/transwing_dynamic_mix.lua`
- Modify: `transwing_lua_sitl.params`
- Modify: `transwing_sitl_mp.params`
- Test: `python tools\verify_transwing_mapping.py`

- [ ] **Step 1: Add parameter table slot**

Increase the table size:

```lua
assert(param:add_table(TABLE_KEY, "TW_", 23), "could not add TW_ parameter table")
```

Add parameter 23:

```lua
assert(param:add_param(TABLE_KEY, 23, "MIX_MODE", 0), "could not add TW_MIX_MODE")
```

Add `"MIX_MODE"` to the `P` list.

- [ ] **Step 2: Add mode constants**

Near the existing `PHASE`, `RISK`, and `ACTION` constants, add:

```lua
local MIX_MODE_OBSERVE = 0
local MIX_MODE_MIRROR = 1
local MIX_MODE_CONTROL = 2
```

- [ ] **Step 3: Preserve `TW_LOG_ONLY` compatibility**

Add:

```lua
local function effective_mix_mode()
  local mode = math.floor(P.MIX_MODE:get() + 0.5)
  if mode < MIX_MODE_OBSERVE then mode = MIX_MODE_OBSERVE end
  if mode > MIX_MODE_CONTROL then mode = MIX_MODE_CONTROL end
  if P.LOG_ONLY:get() < 0.5 and mode == MIX_MODE_OBSERVE then
    return MIX_MODE_MIRROR
  end
  return mode
end
```

- [ ] **Step 4: Split mirror and control writes**

Replace:

```lua
  if P.LOG_ONLY:get() < 0.5 then
    for i = 1, 4 do
      -- Function IDs 94-97 are Scripting1-Scripting4 outputs.
      -- Map isolated SITL outputs to SERVOx_FUNCTION 94-97 before enabling TW_LOG_ONLY=0.
      SRV_Channels:set_output_pwm(93 + i, pwm[i])
    end
  end
```

with:

```lua
  local mix_mode = effective_mix_mode()
  if mix_mode >= MIX_MODE_MIRROR then
    for i = 1, 4 do
      -- Function IDs 94-97 are Scripting1-Scripting4 diagnostic outputs.
      SRV_Channels:set_output_pwm(93 + i, pwm[i])
    end
  end

  if mix_mode == MIX_MODE_CONTROL and action == ACTION.ALLOW then
    for i = 1, 4 do
      -- Function IDs 33-36 are Motor1-Motor4.
      SRV_Channels:set_output_pwm(32 + i, pwm[i])
    end
  end
```

- [ ] **Step 5: Add safe defaults to params**

Add this line to `transwing_lua_sitl.params` and `transwing_sitl_mp.params`:

```text
TW_MIX_MODE,0
```

Keep `TW_LOG_ONLY,1` as compatibility and safe default.

- [ ] **Step 6: Run verifier and confirm GREEN**

Run:

```powershell
python tools\verify_transwing_mapping.py
```

Expected: `PASS`.

---

## Task 4: Export ArduPilot Patch Into Workspace

**Files:**
- Create/Modify: `patches/ardupilot-transwing-channel-map-and-lua-control.patch`

- [ ] **Step 1: Export WSL ArduPilot diff**

Run:

```powershell
wsl bash -lc "cd ~/ardupilot && git diff -- libraries/SITL/SIM_TranswingQuadPlane.cpp libraries/SITL/SIM_TranswingQuadPlane.h Tools/autotest/default_params/quadplane-transwing.parm" > patches\ardupilot-transwing-channel-map-and-lua-control.patch
```

- [ ] **Step 2: Inspect patch**

Run:

```powershell
Get-Content patches\ardupilot-transwing-channel-map-and-lua-control.patch
```

Expected: patch includes Transwing aero mapping changes and does not include unrelated files.

---

## Task 5: Build and Static Verification

**Files:**
- Uses WSL ArduPilot source and local verifier.

- [ ] **Step 1: Run static verifier**

Run:

```powershell
python tools\verify_transwing_mapping.py
```

Expected: `PASS`.

- [ ] **Step 2: Build ArduPlane SITL**

Run:

```powershell
wsl bash -lc "cd ~/ardupilot && ./waf configure --board sitl && ./waf plane"
```

Expected: exit code `0`; build succeeds.

- [ ] **Step 3: Run existing JS model tests**

Run:

```powershell
node --test transwing_lua_mix_model.test.mjs transwing_scene_data.test.mjs
```

Expected: exit code `0`; tests pass.

---

## Task 6: Reconfirm Current State Against Agreement

**Files:**
- No code changes.

- [ ] **Step 1: Re-run source evidence checks**

Run:

```powershell
python tools\verify_transwing_mapping.py
```

Expected: `PASS`.

- [ ] **Step 2: Inspect key lines**

Run:

```powershell
wsl bash -lc "grep -n 'calculate_transwing_aero_forces\|calculate_forces(input\|AILERON_SERVO_A_IDX\|SRV_Channels:set_output_pwm(32' ~/ardupilot/libraries/SITL/SIM_TranswingQuadPlane.cpp /mnt/c/Users/alu/Desktop/TRANSWING/scripts/transwing_dynamic_mix.lua"
```

Expected:

- Contains `calculate_transwing_aero_forces`.
- Contains `AILERON_SERVO_A_IDX = 4`.
- Does not contain `calculate_forces(input, rot_accel)` in `SIM_TranswingQuadPlane.cpp`.
- Contains `SRV_Channels:set_output_pwm(32 + i` in Lua.

- [ ] **Step 3: Report requirement-by-requirement status**

Report:

- Parameter contract: verified by `verify_transwing_mapping.py`.
- Motor/fold layer: verified by constants and verifier.
- Fixed-wing aero layer: verified by no inherited `calculate_forces(input)` call and `SERVO5-10` constants.
- Lua staged control: verified by `TW_MIX_MODE`, mirror write, and real motor write checks.
- Build: verified by `./waf plane`.

---

## Self-Review

Spec coverage:

- Fixed channel contract: Task 1 verifier and Task 6 reconfirmation.
- SITL physics design: Task 2 and Task 5 build.
- Lua control design: Task 3.
- Transition guard: preserved in Task 3 by only writing real motor outputs when `action == ACTION.ALLOW`.
- Diagnostics: current logs stay intact; verifier ensures static mapping. Runtime-enhanced raw `SERVO1-11` diagnostics can be added later if the user wants deeper telemetry.
- Tests and verification: Tasks 1, 5, and 6.

Known deliberate simplification:

- The first fixed-wing surface model is the aggregate model: paired surfaces are averaged. This matches the spec recommendation and fixes the channel mismatch without adding per-surface aerodynamics yet.

# Transwing Coordinate Chain

## Coordinate Sets

The project keeps two coordinate sets deliberately separate:

1. `RAW_MOTORS`
   - Source: real-airframe measured coordinates.
   - File source: `电机位置数据.csv`.
   - Origin: real CG.
   - At `theta = 90 deg`, the four hover motor positions have centroid
     `(-0.1625, 0, -0.4075) m`, so the hover thrust center is 162.5 mm aft
     of the real CG.

2. `SIM_MOTORS`
   - Source: `RAW_MOTORS` shifted by `SIM_CG_X_SHIFT_M = +0.1625 m`.
   - File source: `transwing_scene_data.mjs`.
   - Purpose: SITL control-chain validation where equal hover thrust at
     `theta = 90 deg` has no pitch torque about the simulation CG.
   - At `theta = 90 deg`, the four hover motor positions have centroid
     `(0, 0, -0.4075) m`.

`MOTORS` currently aliases `SIM_MOTORS`, so the viewer, JS mix model, CSV
factor tables, Lua factor table, and SITL C++ geometry all use the same
simulation-corrected geometry.

## Derived Tables

These files are derived from `SIM_MOTORS` and should be regenerated together
when geometry changes:

- `折叠角分配表.csv`
- `电机混控因子.csv`
- `transwing_lua_mix_model.mjs`
- `scripts/transwing_dynamic_mix.lua`
- `patches/ardupilot-transwing-sitl.patch`
- ArduPilot SITL file:
  `~/ardupilot/libraries/SITL/SIM_TranswingQuadPlane.cpp`

Do not treat the simulation shift as a real-airframe CG change. The real
airframe still needs a physical CG/thrust-center decision before fixed-wing
flight testing.

## Transition Guard Defaults

The first transition model is intentionally conservative:

- `TW_SAFE_MIN = 55 deg`: Q assist hold angle for fold + dynamic mix when `TW_ASST_EN=1`.
- `TW_ASST_EN = 1`: link AP assist to Lua fold hold and Motors_dynamic theta floor.
- `TW_ACCEL_MIN = 55 deg`: below this angle, the script requires blend airspeed.
- `TW_BLEND_MIN = 30 deg`: minimum fold angle before fixed-wing airspeed is required.
- `TW_BLEND_AS = 11 m/s`: minimum airspeed for the 30-55 deg blend region (stall≈15 m/s).
- `TW_FW_AS = 15 m/s`: minimum airspeed before fixed-wing fold angles below 30 deg (aligned to stall).
- `AIRSPEED_CRUISE = 20` / `TRIM_ARSP_CM = 2000` (20 m/s cruise), `AIRSPEED_MAX = 30 m/s`.
- `TW_ATT_ABORT = 42 deg`: attitude-abort threshold (slightly above ROLL_LIMIT_DEG 40).
- `ROLL_LIMIT_DEG = 40 deg`: FBWA maximum bank angle.
  back toward Q/hover.
- `TW_ATT_DANG = 35 deg`: attitude danger threshold.
- `TW_DESC_DANG = -8 m/s`: descent-rate danger threshold; fixed-wing abort also requires sustained sink or attitude fault unless descent is severe.
- `TW_GUARD = 1`: active SITL guard enabled by default.

Lua logs `TWTR` with target angle, estimated angle, allowed angle, phase, risk,
airspeed, attitude, climb rate, saturation, and action. When risk is dangerous
and the target angle is below the safe minimum, the guard briefly overrides the
fold output back to the allowed angle.

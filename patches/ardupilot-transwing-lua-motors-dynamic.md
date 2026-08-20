# Transwing Lua motor mix via Motors_dynamic

ArduPilot already ships `AP_MotorsMatrix_Scripting_Dynamic` for QuadPlane when:

```text
Q_FRAME_CLASS = 17    # MOTOR_FRAME_DYNAMIC_SCRIPTING_MATRIX
SCR_ENABLE = 1
```

Lua script `transwing_dynamic_mix.lua` (TW_MIX_MODE=2) calls:

- `Motors_dynamic:add_motor()`
- `Motors_dynamic:load_factors()` with fold-angle-interpolated roll/pitch/yaw/throttle factors
- `Motors_dynamic:init(4)`

ArduPilot attitude controller still provides roll/pitch/yaw/throttle demands; **Lua owns the mix matrix**, not raw PWM overrides.

## Params (control profile)

See `transwing_sitl_mp.params`:

```text
Q_FRAME_CLASS,17
TW_MIX_MODE,2
TW_LOG_ONLY,0
```

## Revert to native AP mix

```text
Q_FRAME_CLASS,1
TW_MIX_MODE,0
TW_LOG_ONLY,1
```

No C++ patch required beyond existing ArduPilot scripting support.

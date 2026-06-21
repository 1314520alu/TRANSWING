# Transwing SITL Channel Mapping and Lua Control Design

## Goal

Align the Transwing SITL physics model with the current real output channel map, and add a staged path for the Lua dynamic mixer to take over the real motor outputs on `SERVO1` through `SERVO4`.

The work fixes the current class of failures where FBWA airspeed rises and the model rolls over because `SIM_Plane` interprets `SERVO1` through `SERVO4` as fixed-wing controls while the Transwing configuration uses those outputs as VTOL motors.

## Current Evidence

Recent Mission Planner SITL logs show repeated FBWA failures at about `13-14 m/s` airspeed. In each failure, roll diverges after entering FBWA and the Lua transition guard switches back to `QSTABILIZE`.

At the failure point, `SERVO5` and `SERVO6` are saturated as ailerons, but `SIM_Plane::calculate_forces()` does not read them. It directly reads:

- `input.servos[0]` as aileron
- `input.servos[1]` as elevator
- `input.servos[2]` as throttle
- `input.servos[3]` as rudder

The Transwing parameter set maps those same outputs to the four VTOL motors. This makes motor PWM enter the fixed-wing aerodynamic calculation as false control-surface inputs.

## Fixed Channel Contract

The Transwing SITL model, Lua mixer, parameter files, diagnostics, and documentation must use one shared channel contract:

| Channel | Meaning |
| --- | --- |
| `SERVO1` | Motor 1 |
| `SERVO2` | Motor 2 |
| `SERVO3` | Motor 3 |
| `SERVO4` | Motor 4 |
| `SERVO5` | Left/right aileron output A |
| `SERVO6` | Left/right aileron output B |
| `SERVO7` | Elevator output A |
| `SERVO8` | Elevator output B |
| `SERVO9` | Rudder output A |
| `SERVO10` | Rudder output B |
| `SERVO11` | Fold/tilt actuator |
| `SERVO12` | Reserved/disabled unless explicitly assigned |
| `SERVO13-16` | Lua diagnostic mirror outputs |

The model must not infer fixed-wing control surfaces from `SERVO1` through `SERVO4`.

## SITL Physics Design

`SIM_TranswingQuadPlane` should stop calling `Plane::calculate_forces(input, rot_accel)` directly. That function is useful for normal plane frames, but its hard-coded channel assumptions do not match Transwing.

The Transwing model should calculate two independent contributions and sum them:

1. Fixed-wing aerodynamic force and torque from the mapped surface channels.
2. Tilted motor force and torque from the mapped motor channels and fold angle.

The fixed-wing aerodynamic layer should derive normalized controls as follows:

- Aileron from `SERVO5` and `SERVO6`
- Elevator from `SERVO7` and `SERVO8`
- Rudder from `SERVO9` and `SERVO10`
- Fixed-wing forward throttle should be zero unless a real forward-thrust channel is added later

For paired surfaces, the first implementation may average the two channels if both are configured with the same ArduPilot function. Later, if the physical left/right signs are modeled separately, the model can calculate per-surface lift and moments instead of using a single normalized aggregate.

The motor layer should continue using:

- `SERVO1-4` as motor command inputs
- `SERVO11` as fold angle input
- Existing fold-angle-dependent motor position and thrust-vector tables

## Lua Control Design

Lua control should become staged and explicit. Add a `TW_MIX_MODE` parameter:

| Value | Behavior |
| --- | --- |
| `0` | Observe only. Log transition state and calculated dynamic mix. Do not write outputs. |
| `1` | Mirror mode. Write calculated dynamic mix to `SERVO13-16` only. |
| `2` | Control mode. Override real motor outputs `SERVO1-4` with Lua dynamic mix. Also mirror to `SERVO13-16` when available. |

`TW_LOG_ONLY` should remain supported as a compatibility alias, but `TW_MIX_MODE` becomes the clear control authority selector.

In control mode, Lua must only write `SERVO1-4` when all of these are true:

- `TW_ENABLE` is enabled.
- Vehicle is in a supported QuadPlane or transition-relevant mode.
- Fold angle estimate is valid and not timed out.
- Transition guard permits the requested fold-angle region.
- Attitude, descent rate, and output saturation are below abort thresholds.

If any condition fails, Lua should release or neutralize motor override according to the safest available ArduPilot Lua API behavior, command the safe fold angle when guard is enabled, and request a safe mode such as `QSTABILIZE` when attitude or descent abort criteria are met.

## Transition Guard

The transition guard remains required. It should be tied to the same channel contract and log enough data to show why it allowed, held, or aborted.

Minimum guard gates:

- Below blend airspeed, do not fold past the acceleration-safe angle.
- Below fixed-wing airspeed, do not enter fixed-wing fold angles.
- On attitude abort, output saturation, or dangerous descent, command safe fold angle and request `QSTABILIZE`.
- If fold estimate is stale, hold or abort instead of continuing transition.

The existing logs show FBWA attempts around `13-14 m/s` while `AIRSPEED_MIN` is `25 m/s`. The implementation should either align `TW_FW_AS` with the fixed-wing minimum speed target or document why a lower staged threshold is safe.

## Diagnostics

Add or update diagnostics so every run can prove the mapping is correct:

- Log raw `SERVO1-11`.
- Log the normalized aerodynamic inputs actually used by SITL: aileron, elevator, rudder.
- Log the motor PWM values actually used by the motor-force layer.
- Log fold target, fold estimate, allowed fold angle, airspeed, attitude, climb rate, saturation, risk, and action.
- In `TW_MIX_MODE=1`, log both native `SERVO1-4` and Lua mirror `SERVO13-16`.
- In `TW_MIX_MODE=2`, log Lua final `SERVO1-4` override values.

## Tests and Verification

Add focused tests before relying on flight behavior:

1. Static mapping test:
   - Changing `SERVO5/6` changes SITL aileron input.
   - Changing `SERVO7/8` changes SITL elevator input.
   - Changing `SERVO9/10` changes SITL rudder input.
   - Changing `SERVO1-4` does not change fixed-wing aerodynamic inputs.

2. Motor geometry test:
   - Changing `SERVO1-4` changes motor force/torque.
   - Changing `SERVO11` changes fold angle and motor thrust direction.

3. Lua mode test:
   - `TW_MIX_MODE=0` writes no override outputs.
   - `TW_MIX_MODE=1` writes only `SERVO13-16`.
   - `TW_MIX_MODE=2` writes `SERVO1-4` and logs control authority.

4. Transition guard test:
   - Low airspeed prevents unsafe fold angles.
   - Attitude abort returns to safe fold angle and requests safe mode.
   - Saturation produces a guard action.

5. SITL flight smoke test:
   - Take off in Q mode.
   - Enter FBWA only after the configured transition airspeed.
   - Confirm no immediate roll-over caused by channel mismatch.
   - Confirm logs show aerodynamic controls coming from `SERVO5-10`, not `SERVO1-4`.

## Implementation Boundaries

This design does not require changing the user-facing channel assignment. The current Transwing output layout remains the source of truth.

This design does not require a full custom autopilot controller. ArduPilot still provides high-level mode handling and attitude demands. The Transwing-specific work is the SITL force model and staged Lua motor-output authority.

This design should not remove the diagnostic mirror outputs. `SERVO13-16` remain useful for comparing native motor output against Lua dynamic mix before enabling real control mode.

## Open Decisions

Before implementation, choose the first fixed-wing surface model:

1. Aggregate model: average paired surfaces into one aileron, one elevator, and one rudder input.
2. Per-surface model: calculate separate left/right surface forces and moments.

The aggregate model is recommended for the first implementation because it directly fixes the channel mismatch with less risk. Per-surface modeling can follow after the transition behavior is stable.

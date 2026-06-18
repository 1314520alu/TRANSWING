import assert from "node:assert/strict";
import test from "node:test";

import {
  AXES,
  BODY_FRAME,
  MOTORS,
  interpolateMotorPosition,
} from "./transwing_scene_data.mjs";

test("uses CG body frame with X forward, Y right, Z up", () => {
  assert.deepEqual(BODY_FRAME.origin, "CG");
  assert.deepEqual(BODY_FRAME.axes, {
    x: "forward",
    y: "right wing",
    z: "up",
  });
});

test("contains the recomputed left and right hinge axes", () => {
  assert.equal(AXES.length, 2);
  assert.deepEqual(AXES.map((axis) => axis.name), [
    "left_wing_hinge_axis",
    "right_wing_hinge_axis",
  ]);
  assert.deepEqual(AXES[0].point, [0, -0.126, 0.416]);
  assert.deepEqual(AXES[0].direction, [-0.457, 0.771, 0.486]);
  assert.deepEqual(AXES[1].point, [0, 0.126, 0.416]);
  assert.deepEqual(AXES[1].direction, [-0.457, -0.771, 0.486]);
});

test("contains four motors with correct unfolded and folded positions", () => {
  assert.equal(MOTORS.length, 4);
  assert.deepEqual(
    MOTORS.map((motor) => [motor.id, motor.testLetter, motor.position, motor.spin]),
    [
      ["M1", "A", "right_front", "CCW"],
      ["M2", "C", "left_rear", "CCW"],
      ["M3", "D", "left_front", "CW"],
      ["M4", "B", "right_rear", "CW"],
    ],
  );
  assert.deepEqual(MOTORS[0].unfolded, [0.525, 0.32, -0.045]);
  assert.deepEqual(MOTORS[0].folded, [0.155, 0.49, -0.46]);
  assert.deepEqual(MOTORS[3].unfolded, [0.52, 0.98, -0.06]);
  assert.deepEqual(MOTORS[3].folded, [-0.48, 0.46, -0.355]);
});

test("interpolation preserves exact endpoints", () => {
  for (const motor of MOTORS) {
    assert.deepEqual(interpolateMotorPosition(motor, 0), motor.unfolded);
    assert.deepEqual(interpolateMotorPosition(motor, 90), motor.folded);
  }
});

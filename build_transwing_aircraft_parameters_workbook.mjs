import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "C:/Users/alu/Desktop/TRANSWING";
const outputDir = path.join(root, "outputs");
const outputPath = path.join(outputDir, "Transwing_Aircraft_Parameters_Check_OneSheet_Clean.xlsx");

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(",");
  return lines.slice(1).map((line) => {
    const values = line.split(",");
    const row = {};
    headers.forEach((header, i) => {
      const value = values[i] ?? "";
      const n = Number(value);
      row[header] = value !== "" && Number.isFinite(n) ? n : value;
    });
    return row;
  });
}

function rowsToMatrix(rows, headers) {
  return [
    headers,
    ...rows.map((row) => headers.map((header) => row[header] ?? "")),
  ];
}

function lettersToNumber(letters) {
  let n = 0;
  for (const c of letters) n = n * 26 + c.charCodeAt(0) - 64;
  return n;
}

function numberToLetters(n) {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function styleTitle(sheet, row, title, subtitle = "") {
  sheet.getRange(`A${row}:P${row}`).merge();
  sheet.getRange(`A${row}`).values = [[title]];
  sheet.getRange(`A${row}`).format = {
    fill: "#233142",
    font: { bold: true, color: "#FFFFFF", size: 16 },
  };
  if (subtitle) {
    sheet.getRange(`A${row + 1}:P${row + 1}`).merge();
    sheet.getRange(`A${row + 1}`).values = [[subtitle]];
    sheet.getRange(`A${row + 1}`).format = {
      fill: "#E9EEF2",
      font: { color: "#233142" },
      wrapText: true,
    };
    return row + 3;
  }
  return row + 2;
}

function styleSection(sheet, row, title) {
  sheet.getRange(`A${row}:P${row}`).merge();
  sheet.getRange(`A${row}`).values = [[title]];
  sheet.getRange(`A${row}`).format = {
    fill: "#3A6073",
    font: { bold: true, color: "#FFFFFF", size: 12 },
  };
  return row + 1;
}

function writeTable(sheet, row, headers, rows) {
  const endCol = numberToLetters(headers.length);
  const endRow = row + rows.length;
  const address = `A${row}:${endCol}${endRow}`;
  sheet.getRange(address).values = rowsToMatrix(rows, headers);
  sheet.getRange(address).format.borders = { preset: "all", style: "thin", color: "#D8DEE5" };
  sheet.getRange(`A${row}:${endCol}${row}`).format = {
    fill: "#DDE8EE",
    font: { bold: true, color: "#17212B" },
    wrapText: true,
  };
  sheet.getRange(address).format.wrapText = true;
  return endRow + 2;
}

function setWidths(sheet, widths) {
  widths.forEach((width, i) => {
    const col = numberToLetters(i + 1);
    sheet.getRange(`${col}:${col}`).format.columnWidthPx = width;
  });
}

async function main() {
  const motorPositions = parseCsv(await fs.readFile(path.join(root, "transwing_motor_positions.csv"), "utf8"));
  const axes = parseCsv(await fs.readFile(path.join(root, "transwing_axes.csv"), "utf8"));
  const allocation = parseCsv(await fs.readFile(path.join(root, "transwing_allocation_table.csv"), "utf8"));
  const factors = parseCsv(await fs.readFile(path.join(root, "transwing_motor_factors.csv"), "utf8"));

  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add("All_Data");
  sheet.showGridLines = false;

  let row = 1;
  row = styleTitle(
    sheet,
    row,
    "Transwing Aircraft Parameters Check",
    "All data in one sheet. Body frame: X forward, Y right, Z down, origin at CG, unit m unless noted.",
  );

  row = styleSection(sheet, row, "1. Coordinate System");
  row = writeTable(sheet, row, ["Item", "Value", "Note"], [
    ["Coordinate origin", "CG", "重心为原点"],
    ["X positive", "Forward", "朝机头"],
    ["Y positive", "Right", "朝右翼"],
    ["Z positive", "Down", "朝下"],
    ["Unit", "m", "角度单位 deg"],
  ]);

  row = styleSection(sheet, row, "2. ArduPilot Starting Parameters");
  row = writeTable(sheet, row, ["Parameter", "Value", "Note"], [
    ["Q_ENABLE", 1, "启用 QuadPlane"],
    ["Q_FRAME_CLASS", 1, "Quad"],
    ["Q_FRAME_TYPE", 1, "X frame；官方文档中 3 才是 H"],
    ["Q_TILT_ENABLE", "TBD", "如果先用原生倾转逻辑测试，再配置；最终动态混控需要 C++"],
    ["Q_TILT_MASK", 15, "四个电机都参与倾转/过渡逻辑的初始假设"],
    ["Q_TRANSITION_MS", "3000~8000", "过渡时间初值，需要地面和试飞调整"],
    ["AIRSPEED_MIN", "TBD", "由翼型、重量、失速速度决定"],
    ["Q_ASSIST_SPEED", "TBD", "建议略高于安全低速阈值"],
    ["SCR_ENABLE", 1, "Lua 控制作动器/记录 theta 时启用"],
    ["SERVOx_FUNCTION", "TBD", "折叠作动器输出通道"],
  ]);

  row = styleSection(sheet, row, "3. Motor Test Mapping");
  row = writeTable(sheet, row, ["Motor Test Letter", "Actual Motor", "Physical Position", "Spin", "Note"], [
    ["A", "MOTOR 1", "right_front", "CCW", "测试顺序第 1 个"],
    ["B", "MOTOR 4", "right_rear", "CW", "测试顺序第 2 个"],
    ["C", "MOTOR 2", "left_rear", "CCW", "测试顺序第 3 个"],
    ["D", "MOTOR 3", "left_front", "CW", "测试顺序第 4 个"],
  ]);

  row = styleSection(sheet, row, "4. Motor Positions");
  row = writeTable(
    sheet,
    row,
    ["motor", "test_letter", "physical_position", "spin", "x0_m", "y0_m", "z0_m", "x90_m", "y90_m", "z90_m"],
    motorPositions,
  );

  row = styleSection(sheet, row, "5. Hinge Points and Unit Axes");
  row = writeTable(sheet, row, ["Name", "X", "Y", "Z", "Note"], [
    ["Left hinge point A", 0, -0.126, 0.416, ""],
    ["Left hinge point B", -0.016, -0.099, 0.433, ""],
    ["Left vector AB", -0.016, 0.027, 0.017, ""],
    ["Left unit axis", -0.457, 0.771, 0.486, ""],
    ["Right hinge point C", 0, 0.126, 0.416, ""],
    ["Right hinge point D", -0.016, 0.099, 0.433, ""],
    ["Right vector CD", -0.016, -0.027, 0.017, ""],
    ["Right unit axis", -0.457, -0.771, 0.486, ""],
  ]);

  row = styleSection(sheet, row, "6. Hinge Axis Table");
  row = writeTable(sheet, row, ["name", "hx_m", "hy_m", "hz_m", "ax", "ay", "az", "radius_m", "source"], axes);

  row = styleSection(sheet, row, "7. Geometry Checks");
  row = writeTable(sheet, row, ["Check", "Value", "Expected / Note"], [
    ["Folded M1.z - M2.z", -0.46 - (-0.355), "M1 比 M2 更上方；Z down 中数值更小"],
    ["Folded M3.z - M4.z", -0.46 - (-0.355), "左侧对应差值"],
    ["Folded M1.y + M3.y", 0.49 + (-0.49), "前排左右 Y 对称，应接近 0"],
    ["Folded M2.y + M4.y", -0.46 + 0.46, "后排左右 Y 对称，应接近 0"],
    ["Unfolded M1.y + M3.y", 0.32 + (-0.32), "内侧推进电机 Y 对称"],
    ["Unfolded M2.y + M4.y", -0.98 + 0.98, "外侧推进电机 Y 对称"],
    ["Hinge point A.y + C.y", -0.126 + 0.126, "左右转轴点 Y 对称"],
    ["Hinge axis left.ay + right.ay", 0.771 + (-0.771), "左右转轴方向 Y 分量相反"],
    ["Hinge axis left.ax - right.ax", -0.457 - (-0.457), "左右转轴方向 X 分量相同"],
    ["Hinge axis left.az - right.az", 0.486 - 0.486, "左右转轴方向 Z 分量相同"],
  ]);

  row = styleSection(sheet, row, "8. Transition Allocation Table");
  row = writeTable(
    sheet,
    row,
    [
      "theta_deg",
      "motor",
      "test_letter",
      "physical_position",
      "spin",
      "x_m",
      "y_m",
      "z_m",
      "dx",
      "dy",
      "dz",
      "vertical_factor_dz",
      "roll_moment_x",
      "pitch_moment_y",
      "yaw_moment_z_from_force",
      "yaw_drag_sign",
    ],
    allocation,
  );

  row = styleSection(sheet, row, "9. Normalized Motor Factors");
  writeTable(
    sheet,
    row,
    [
      "theta_deg",
      "motor",
      "test_letter",
      "physical_position",
      "spin",
      "throttle_factor",
      "roll_factor",
      "pitch_factor",
      "yaw_force_factor",
      "yaw_drag_factor",
    ],
    factors,
  );

  setWidths(sheet, [210, 105, 145, 105, 90, 90, 90, 90, 90, 90, 95, 130, 125, 125, 165, 115]);
  sheet.freezePanes.freezeRows(3);
  sheet.getUsedRange().format.font = { name: "Microsoft YaHei", size: 10 };

  await fs.mkdir(outputDir, { recursive: true });
  await workbook.render({ sheetName: "All_Data", autoCrop: "all", scale: 1, format: "png" });

  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
  });
  console.log(errors.ndjson);

  const exported = await SpreadsheetFile.exportXlsx(workbook);
  await exported.save(outputPath);
  console.log(outputPath);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

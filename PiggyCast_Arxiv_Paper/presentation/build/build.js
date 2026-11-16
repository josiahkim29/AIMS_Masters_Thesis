const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const md = require("react-icons/md");
const path = require("path");
const fs = require("fs");
const { applyTheme } = require(process.env.SKILL + "/scripts/apply_theme.js");

const D = JSON.parse(fs.readFileSync(path.join(__dirname, "data.json")));
const IMG = (f) => path.join(__dirname, "img", f);
const OUT = process.argv[2];

const THEME = {
  name: "PiggyCast",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1F2328", lt1: "FFFFFF", dk2: "15233B", lt2: "EEF2F7",
    accent1: "EB6834", accent2: "2A78D6", accent3: "1BAF7A", accent4: "EDA100",
    accent5: "3B3A37", accent6: "B3202A", hlink: "2A78D6", folHlink: "6250D6",
  },
};
const HEX = THEME.colors;
const MUTED = "5F6670";
// Series colours: identical to the paper figures and notebook.
const COL = { neuralgcm: "3B3A37", graphcast: "8A8984", mmm: "2A78D6", lin_clim: "EB6834", xgb_resid: "1BAF7A", xgb_orig: "EDA100", clim: "B3202A", ifshres: "A9A8A2", pangu: "C9C8C2" };
const NAME = { neuralgcm: "NeuralGCM", graphcast: "GraphCast", ifshres: "IFS HRES", pangu: "Pangu-Weather", mmm: "Multi-model mean", lin_clim: "PiggyCast-Lin", xgb_resid: "PiggyCast-XGB-R", xgb_orig: "PiggyCast-XGB (thesis)", clim: "Climatology" };
const LEADS = ["24", "48", "72", "96", "120", "144", "168", "192", "216", "240"];

async function icon(Comp, color = "FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
  pres.author = "Josiah K. Kimani";
  pres.title = "PiggyCast: results review";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // ---------- layouts ----------
  const footer = (dark) => [
    { text: { text: "PiggyCast · results review · Kimani, Angélil, Fotso, Knoblauch", options: { x: 0.6, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: dark ? "AEB8C8" : MUTED, margin: 0 } } },
  ];
  pres.defineSlideMaster({
    title: "Title (dark)", background: { color: HEX.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.7, w: 7.4, h: 1.6, fontSize: 54, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 3.45, w: 7.4, h: 1.5, fontSize: 22, color: "D6DEEA", valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Section (dark)", background: { color: HEX.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 2.6, w: 12.1, h: 1.2, fontSize: 44, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 3.95, w: 12.1, h: 1.0, fontSize: 20, color: "D6DEEA", valign: "top", align: "left", margin: 0 }, text: "" } },
      ...footer(true),
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "AEB8C8", align: "right" },
  });
  pres.defineSlideMaster({
    title: "Title only", background: { color: HEX.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.95, fontSize: 32, bold: true, color: C.text2, fontFace: THEME.headFontFace, valign: "middle", align: "left", margin: 0 }, text: "" } },
      ...footer(false),
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: MUTED, align: "right" },
  });

  const content = (title, section, notes) => {
    const s = pres.addSlide({ masterName: "Title only", sectionTitle: section });
    s.addText(title, { placeholder: "title" });
    if (notes) s.addNotes(notes);
    return s;
  };
  const txt = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontSize: 15, color: C.text1, valign: "top", ...o });
  const card = (s, x, y, w, h, name, fill = HEX.lt2) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill }, objectName: name });
  const circleIcon = async (s, x, y, d, Comp, fill, name) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: name + " circle" });
    const pad = d * 0.22;
    s.addImage({ data: await icon(Comp), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, altText: name, objectName: name + " icon" });
  };
  const stat = (s, x, y, w, big, label, color, name) => {
    txt(s, big, { x, y, w, h: 1.0, fontSize: 54, bold: true, color, fontFace: THEME.headFontFace, valign: "bottom", objectName: name + " value" });
    txt(s, label, { x, y: y + 1.1, w, h: 1.0, fontSize: 15, color: MUTED, objectName: name + " label" });
  };
  const lineOpts = (extra) => ({
    x: 0.6, y: 1.5, w: 7.9, h: 5.2,
    catAxisTitle: "Lead time (h)", showCatAxisTitle: true,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisTitleFontFace: "+mn-lt", valAxisTitleFontFace: "+mn-lt", legendFontFace: "+mn-lt",
    catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, catAxisTitleColor: MUTED, valAxisTitleColor: MUTED,
    catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, catAxisTitleFontSize: 12, valAxisTitleFontSize: 12,
    valGridLine: { color: "E4E3DF", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: true, legendPos: "t", legendFontSize: 12, legendColor: "1F2328",
    lineSize: 2.25, lineDataSymbol: "circle", lineDataSymbolSize: 6,
    ...extra,
  });
  const series = (keys, src) => keys.map((k) => ({ name: NAME[k], labels: LEADS, values: src[k] }));

  // ---------- 1. title ----------
  pres.addSection({ title: "Introduction" });
  let s = pres.addSlide({ masterName: "Title (dark)", sectionTitle: "Introduction" });
  s.addText("PiggyCast", { placeholder: "title" });
  s.addText("Stacking numerical, AI and hybrid weather models: simple combiners capture most of the gain", { placeholder: "body" });
  txt(s, [
    { text: "Josiah K. Kimani", options: { bold: true, breakLine: true } },
    { text: "Oliver Angélil · Chris Fotso · Steffen Knoblauch", options: { breakLine: true } },
    { text: "AIMS South Africa · Ishango.ai · Heidelberg University", options: { color: "AEB8C8" } },
  ], { x: 0.6, y: 5.3, w: 7.4, h: 1.2, fontSize: 15, color: "FFFFFF", objectName: "Authors" });
  // motif: four model circles feeding one stacked forecast
  const mx = 9.0, my = 1.6;
  const four = [["neuralgcm", md.MdHub], ["graphcast", md.MdMemory], ["ifshres", md.MdPublic], ["pangu", md.MdGridOn]];
  for (let i = 0; i < 4; i++) {
    await circleIcon(s, mx, my + i * 1.05, 0.8, four[i][1], ["5C6B82", "4E5D74", "435168", "3A475C"][i], NAME[four[i][0]]);
    const y0 = my + 0.4 + i * 1.05, y1 = my + 1.975;
    s.addShape(pres.shapes.LINE, { x: mx + 0.85, y: Math.min(y0, y1), w: 1.15, h: Math.abs(y1 - y0), line: { color: "6E7C92", width: 1.25 }, flipV: y0 > y1, objectName: "connector " + i });
  }
  s.addShape(pres.shapes.LINE, { x: mx + 0.85, y: my + 1.975, w: 1.15, h: 0, line: { color: "6E7C92", width: 1.25 }, objectName: "connector mid" });
  await circleIcon(s, mx + 2.0, my + 1.375, 1.2, md.MdLayers, HEX.accent1, "PiggyCast stack");
  txt(s, "four forecasts → one", { x: mx - 0.2, y: my + 4.3, w: 3.6, h: 0.4, fontSize: 14, color: "AEB8C8", align: "center", objectName: "Motif caption" });
  s.addNotes("Results review deck for co-authors and supervisors. It accompanies the paper draft (PiggyCast_Arxiv_Paper/master_document.tex) and the results notebook (experiments/notebooks/PiggyCast_results.ipynb). Every number here comes from experiments/res/ and can be regenerated with ./run_all.sh.");

  // ---------- 2. short version ----------
  s = content("The short version", "Introduction",
    "Three take-aways. (1) A six-parameter linear stack, PiggyCast-Lin, beats NeuralGCM (the best single model) by 9.7-17.8% RMSE at every lead from 1 to 10 days; all bootstrap intervals exclude zero. (2) It needs only about 15 days of training. (3) The XGBoost model from the thesis is worse than a plain equal-weight average at every lead, so the learning in the stack has to be simple to help.");
  const st = [
    ["10–18%", "lower RMSE than NeuralGCM, the best single model, at every lead from 1 to 10 days (PiggyCast-Lin)", HEX.accent1],
    ["6", "parameters in PiggyCast-Lin; 15 days of training data is enough", C.text2],
    ["0 of 10", "lead times at which the thesis XGBoost beats a plain multi-model average", HEX.accent6],
  ];
  st.forEach(([b, l, c], i) => { card(s, 0.6 + i * 4.1, 1.7, 3.8, 3.3, "Stat card " + (i + 1)); stat(s, 0.9 + i * 4.1, 1.95, 3.2, b, l, c, "Stat " + (i + 1)); });
  txt(s, "Most of the gain comes from averaging models whose errors are only half-correlated. Learning adds a little more, but only when the learner is simple.",
    { x: 0.6, y: 5.45, w: 12.1, h: 0.9, fontSize: 18, italic: true, color: C.text2, objectName: "Takeaway" });

  // ---------- 3. four models ----------
  s = content("Four models, three paradigms", "Introduction",
    "IFS HRES is ECMWF's physics-based operational model. GraphCast (graph neural network) and Pangu-Weather (3-D transformer) are purely data-driven and in WeatherBench 2 are initialised from the operational HRES analysis. NeuralGCM is a hybrid: a differentiable dynamical core with learned physics. To check with co-authors: the paper says NeuralGCM's WB2 forecasts are ERA5-initialised (Kochkov et al. 2024); the WB2 docs do not state it.");
  const models = [
    ["IFS HRES", "Physics-based NWP", "ECMWF operational model", md.MdPublic],
    ["GraphCast", "AI · graph neural network", "Google DeepMind; HRES-initialised", md.MdMemory],
    ["Pangu-Weather", "AI · 3-D transformer", "Huawei; HRES-initialised", md.MdGridOn],
    ["NeuralGCM", "Hybrid physics + ML", "Google; best single model here", md.MdHub],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + i * 3.1;
    card(s, x, 1.6, 2.85, 3.3, "Model card " + (i + 1));
    await circleIcon(s, x + 0.3, 1.9, 0.8, models[i][3], i === 3 ? HEX.accent5 : "6D6C68", models[i][0]);
    txt(s, models[i][0], { x: x + 0.3, y: 2.9, w: 2.3, h: 0.5, fontSize: 20, bold: true, color: C.text2, fontFace: THEME.headFontFace });
    txt(s, models[i][1], { x: x + 0.3, y: 3.45, w: 2.3, h: 0.5, fontSize: 15, bold: true, color: C.text1 });
    txt(s, models[i][2], { x: x + 0.3, y: 3.95, w: 2.3, h: 0.8, fontSize: 14, color: MUTED });
  }
  txt(s, [
    { text: "Question: ", options: { bold: true, color: HEX.accent1 } },
    { text: "can a learned combination beat the best of these, and what does learning add over a plain average?" },
  ], { x: 0.6, y: 5.4, w: 12.1, h: 0.9, fontSize: 20, color: C.text2, objectName: "Question" });

  // ---------- 4. setup ----------
  s = content("Setup: one variable, one year, honest folds", "Introduction",
    "Z500 geopotential (m^2 s^-2, not metres) on the 5.625 degree WeatherBench 2 grid, 12-hourly, leads 24-240 h, verified against ERA5. Rows are indexed by valid time, so every lead is scored on the same days: 11 Jan 2020 to 1 Jan 2021. Ten rolling-origin folds with 60-day training and 30-day test windows; the gap between them is 5 days plus the lead time, so no training target is verified after a test forecast is issued. The thesis used a fixed 5-day gap, which leaks for leads above 120 h.");
  const steps = [
    ["Data", "WeatherBench 2 Z500, 5.625°, 12-hourly; leads 24–240 h; ERA5 truth", md.MdStorage],
    ["Align", "Index by valid time; common window 11 Jan 2020 – 1 Jan 2021 for all leads", md.MdSchedule],
    ["Evaluate", "10 rolling folds: 60-day train, 30-day test; gap = 5 days + lead", md.MdLoop],
    ["Score", "Area-weighted RMSE, ACC, activity; 5-day block bootstrap", md.MdInsights],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + i * 3.1;
    await circleIcon(s, x, 1.8, 1.0, steps[i][2], i === 2 ? HEX.accent1 : HEX.dk2, steps[i][0]);
    if (i < 3) s.addShape(pres.shapes.LINE, { x: x + 1.15, y: 2.3, w: 1.8, h: 0, line: { color: "AEB8C8", width: 1.5, endArrowType: "triangle" }, objectName: "Flow arrow " + (i + 1) });
    txt(s, (i + 1) + ". " + steps[i][0], { x, y: 3.0, w: 2.8, h: 0.5, fontSize: 20, bold: true, color: C.text2, fontFace: THEME.headFontFace });
    txt(s, steps[i][1], { x, y: 3.55, w: 2.8, h: 1.4, fontSize: 15, color: C.text1 });
  }
  card(s, 0.6, 5.3, 12.1, 1.3, "Leakage note");
  txt(s, [
    { text: "Why the gap matters: ", options: { bold: true, color: HEX.accent6 } },
    { text: "a 240 h forecast verified on day d was issued on day d − 10. With the thesis's fixed 5-day gap, training targets overlap the test forecasts' issue period for every lead above 120 h." },
  ], { x: 0.9, y: 5.5, w: 11.5, h: 0.95, fontSize: 15, valign: "middle", objectName: "Leakage text" });

  // ---------- 5. combiners ----------
  s = content("Combiners, from an average to gradient boosting", "Introduction",
    "MMM: equal-weight average, nothing learned. PiggyCast-Lin: area-weighted least squares on the four forecasts plus climatology and an intercept, refit per fold and lead. PiggyCast-XGB is the thesis model: XGBoost with default settings, features = four forecasts plus lon/lat, target = ERA5 Z500. PiggyCast-XGB-R keeps XGBoost but makes the task easier: it predicts ERA5 minus the MMM from each model's deviation from the MMM, the MMM anomaly and lon/lat. A per-grid-point ridge stack (Krishnamurti superensemble) is also in the paper as a baseline.");
  const comb = [
    ["mmm", "Multi-model mean", "0 parameters", "Equal-weight average of the four forecasts"],
    ["lin_clim", "PiggyCast-Lin", "6 parameters", "4 model weights + climatology + intercept, least squares"],
    ["xgb_orig", "PiggyCast-XGB", "thesis model", "XGBoost on 4 forecasts + lon/lat; predicts Z500 directly"],
    ["xgb_resid", "PiggyCast-XGB-R", "residual variant", "XGBoost predicts the correction ERA5 − MMM"],
  ];
  comb.forEach(([k, t, sub, d], i) => {
    const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.45;
    card(s, x, y, 5.95, 2.2, "Combiner card " + (i + 1));
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.35, w: 0.45, h: 0.45, fill: { color: COL[k] }, line: { color: COL[k] }, objectName: t + " swatch" });
    txt(s, t, { x: x + 0.95, y: y + 0.3, w: 3.2, h: 0.55, fontSize: 22, bold: true, color: C.text2, fontFace: THEME.headFontFace, valign: "middle" });
    txt(s, sub, { x: x + 4.0, y: y + 0.3, w: 1.7, h: 0.55, fontSize: 14, color: MUTED, align: "right", valign: "middle" });
    txt(s, d, { x: x + 0.95, y: y + 1.0, w: 4.75, h: 0.9, fontSize: 16, color: C.text1 });
  });
  txt(s, "Colours match the paper figures and the notebook.", { x: 0.6, y: 6.5, w: 12.1, h: 0.35, fontSize: 12, color: MUTED });

  // ---------- 6. section ----------
  pres.addSection({ title: "Results" });
  s = pres.addSlide({ masterName: "Section (dark)", sectionTitle: "Results" });
  s.addText("Results", { placeholder: "title" });
  s.addText("Skill, significance, where it comes from, and why XGBoost falls short", { placeholder: "body" });

  // ---------- 7. headline chart ----------
  s = content("PiggyCast-Lin beats the best single model at every lead", "Results",
    "Y axis: RMSE change relative to the best single model at each lead (NeuralGCM at every lead), so 0 = NeuralGCM and negative is better. PiggyCast-Lin (orange) is 10-18% better throughout. The plain average (blue) is close behind beyond day 3 but gains little at 24 h, where NeuralGCM is much better than the other three. The thesis XGBoost (amber) is 39% worse than NeuralGCM at 24 h and stays above the average at every lead.");
  s.addChart(pres.charts.LINE, series(["graphcast", "mmm", "lin_clim", "xgb_resid", "xgb_orig"], D.pct), lineOpts({
    chartColors: [COL.graphcast, COL.mmm, COL.lin_clim, COL.xgb_resid, COL.xgb_orig],
    valAxisTitle: "RMSE change vs best single model (%)", showValAxisTitle: true,
    valAxisMinVal: -20, valAxisMaxVal: 40, valAxisMajorUnit: 10,
  }));
  txt(s, "−17.8%", { x: 9.0, y: 1.7, w: 3.7, h: 0.9, fontSize: 48, bold: true, color: HEX.accent1, fontFace: THEME.headFontFace, objectName: "Stat day 10" });
  txt(s, "PiggyCast-Lin vs NeuralGCM at 240 h; −9.7% at 24 h", { x: 9.0, y: 2.65, w: 3.7, h: 0.7, fontSize: 15, color: MUTED });
  txt(s, "+39%", { x: 9.0, y: 3.6, w: 3.7, h: 0.9, fontSize: 48, bold: true, color: "B07800", fontFace: THEME.headFontFace, objectName: "Stat XGB" });
  txt(s, "thesis XGBoost vs NeuralGCM at 24 h; above the plain average at every lead", { x: 9.0, y: 4.55, w: 3.7, h: 0.9, fontSize: 15, color: MUTED });
  txt(s, "0% line = NeuralGCM. Negative = better.", { x: 9.0, y: 5.8, w: 3.7, h: 0.5, fontSize: 13, italic: true, color: MUTED });

  // ---------- 8. table ----------
  s = content("The gains are significant and hold in every fold", "Results",
    "Fold-mean area-weighted RMSE in m^2 s^-2 with the leakage-safe gap. Bootstrap: 5-day moving blocks, 2000 resamples. Of all pairs tested, only two intervals include zero: XGB-R vs MMM at 72 h and the plain linear stack (no climatology) vs MMM at 240 h. PiggyCast-Lin beats both NeuralGCM and the MMM in 10 of 10 folds at both 72 h and 240 h.");
  const idx = [0, 2, 4, 6, 9];
  const hdr = ["Lead", "NeuralGCM", "Multi-model mean", "PiggyCast-Lin", "PiggyCast-XGB-R", "PiggyCast-XGB (thesis)"];
  const cell = (t, o = {}) => ({ text: t, options: { fontSize: 15, align: "center", valign: "middle", color: "1F2328", fontFace: "Calibri", ...o } });
  const rows = [hdr.map((h) => cell(h, { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 } }))];
  idx.forEach((j, r) => {
    const z = r % 2 ? { fill: { color: "F6F8FB" } } : { fill: { color: "FFFFFF" } };
    rows.push([
      cell(LEADS[j] + " h", { bold: true, ...z }),
      cell(D.rm.neuralgcm[j].toFixed(1), z), cell(D.rm.mmm[j].toFixed(1), z),
      cell(D.rm.lin_clim[j].toFixed(1), { bold: true, color: "FFFFFF", fill: { color: HEX.accent1 } }),
      cell(D.rm.xgb_resid[j].toFixed(1), z), cell(D.rm.xgb_orig[j].toFixed(1), z),
    ]);
  });
  s.addTable(rows, { x: 0.6, y: 1.55, w: 12.1, colW: [1.3, 1.9, 2.2, 2.0, 2.2, 2.5], rowH: 0.48, border: { type: "solid", pt: 0.75, color: "D9DEE5" }, objectName: "RMSE table" });
  txt(s, "Fold-mean area-weighted RMSE, m² s⁻². Lower is better. PiggyCast-XGB-R is slightly better than PiggyCast-Lin at 24 h only.", { x: 0.6, y: 4.6, w: 12.1, h: 0.4, fontSize: 12, color: MUTED });
  const chk = [["All 10 lead times", "PiggyCast-Lin beats NeuralGCM and the MMM; every bootstrap interval excludes zero"], ["10 of 10 folds", "PiggyCast-Lin beats both at 72 h and at 240 h"], ["0 of 10 folds", "the thesis XGBoost beats the MMM at 72 h or 240 h"]];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    await circleIcon(s, x, 5.3, 0.6, i < 2 ? md.MdCheck : md.MdClose, i < 2 ? HEX.accent3 : HEX.accent6, "Check " + (i + 1));
    txt(s, chk[i][0], { x: x + 0.8, y: 5.25, w: 3.1, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
    txt(s, chk[i][1], { x: x + 0.8, y: 5.65, w: 3.1, h: 0.95, fontSize: 14, color: MUTED });
  }

  // ---------- 9. error correlation ----------
  s = content("Averaging works because errors are only half-correlated", "Results",
    "Correlations between the error fields of each pair of models, area-weighted. With mean correlation about 0.56, averaging M = 4 models cuts error variance to sigma^2 (1 + (M-1) rho) / M. The general form of that formula, using each model's own RMSE, predicts the MMM's RMSE almost exactly. The dendrogram (UPGMA on pairwise RMSE at 72 h) shows NeuralGCM closest to ERA5 and the two HRES-initialised AI models grouping with IFS.");
  s.addImage({ path: IMG("fig_error_structure.png"), x: 0.6, y: 1.55, w: 8.3, h: 8.3 * 1059 / 2625, altText: "Error correlation heatmaps at 72 h and 240 h, and a UPGMA dendrogram of the four models and ERA5 at 72 h", objectName: "Error structure figure" });
  txt(s, "ρ̄ ≈ 0.56", { x: 9.3, y: 1.6, w: 3.4, h: 0.9, fontSize: 48, bold: true, color: HEX.accent2, fontFace: THEME.headFontFace });
  txt(s, "mean error correlation between model pairs, at 72 h and 240 h alike", { x: 9.3, y: 2.55, w: 3.4, h: 0.75, fontSize: 15, color: MUTED });
  txt(s, "MSE of the mean = σ²(1 + (M − 1)ρ̄) / M", { x: 9.3, y: 3.5, w: 3.4, h: 0.5, fontSize: 15, bold: true, color: C.text2 });
  const pr = [["Lead", "Predicted", "Actual"], ["72 h", "97.3", "97.5"], ["240 h", "614.4", "614.0"]];
  s.addTable(pr.map((r, i) => r.map((t) => cell(t, i === 0 ? { bold: true, fill: { color: HEX.lt2 } } : {}))), { x: 9.3, y: 4.15, w: 3.4, colW: [1.0, 1.2, 1.2], rowH: 0.42, border: { type: "solid", pt: 0.75, color: "D9DEE5" }, objectName: "Prediction table" });
  txt(s, "Pooled RMSE of the multi-model mean, m² s⁻²", { x: 9.3, y: 5.5, w: 3.4, h: 0.4, fontSize: 12, color: MUTED });
  txt(s, "Error correlations at 72 h and 240 h (left), clustering at 72 h (right)", { x: 0.6, y: 1.55 + 8.3 * 1059 / 2625 + 0.15, w: 8.3, h: 0.4, fontSize: 12, color: MUTED });

  // ---------- 10. maps ----------
  s = content("Gains are global; XGBoost loses near the poles", "Results",
    "Grid-point RMSE ratios over the test period; blue means the numerator is better. (a, b) PiggyCast-Lin vs NeuralGCM at 72 h and 240 h. (c) Thesis XGBoost vs the multi-model mean at 240 h: it is better in the tropics but much worse at high latitudes, where Z500 varies most. Cartopy Robinson projection.");
  const mh = 12.1 * 649 / 2192;
  s.addImage({ path: IMG("fig_maps.png"), x: 0.6, y: 1.5, w: 12.1, h: mh, altText: "Maps of RMSE ratio: PiggyCast-Lin over NeuralGCM at 72 h and 240 h, and thesis XGBoost over the multi-model mean at 240 h", objectName: "RMSE ratio maps" });
  const mapst = [["97%", "of the globe's area where PiggyCast-Lin beats NeuralGCM at 72 h", HEX.accent1], ["99.9%", "of area at 240 h", HEX.accent1], ["+32%", "thesis XGBoost vs MMM north of 60°N at 240 h; −7% in the tropics", "B07800"]];
  mapst.forEach(([b, l, c], i) => {
    const x = 0.6 + i * 4.1;
    txt(s, b, { x, y: 1.5 + mh + 0.3, w: 3.8, h: 0.8, fontSize: 40, bold: true, color: c, fontFace: THEME.headFontFace, valign: "bottom" });
    txt(s, l, { x, y: 1.5 + mh + 1.15, w: 3.8, h: 0.8, fontSize: 15, color: MUTED });
  });

  // ---------- 11. damping ----------
  s = content("At long leads, part of the gain is learned damping", "Results",
    "Activity ratio = RMS of the forecast anomaly divided by the RMS of the ERA5 anomaly. Murphy (1988): the MSE-optimal forecast has activity equal to its ACC. PiggyCast-Lin follows that almost exactly (dashed line is its ACC). So part of its long-lead gain comes from pulling towards climatology: at 240 h its anomalies are a third weaker than reality. That is optimal for RMSE but hides extremes, which the paper states plainly.");
  s.addChart([
    { type: pres.charts.LINE, data: [
      { name: "NeuralGCM activity", labels: LEADS, values: D.act.neuralgcm },
      { name: "MMM activity", labels: LEADS, values: D.act.mmm },
      { name: "PiggyCast-Lin activity", labels: LEADS, values: D.act.lin_clim },
    ], options: { chartColors: [COL.neuralgcm, COL.mmm, COL.lin_clim], lineSize: 2.25, lineDataSymbol: "circle", lineDataSymbolSize: 6 } },
    { type: pres.charts.LINE, data: [{ name: "PiggyCast-Lin ACC (dashed)", labels: LEADS, values: D.acc.lin_clim }],
      options: { chartColors: ["9A3D17"], lineSize: 2.25, lineDash: "dash", lineDataSymbol: "none" } },
  ], lineOpts({
    valAxisTitle: "Ratio / correlation", showValAxisTitle: true, valAxisMinVal: 0.6, valAxisMaxVal: 1.0, valAxisMajorUnit: 0.1, valAxisLabelFormatCode: "0.0",
  }));
  txt(s, "0.66", { x: 9.0, y: 1.7, w: 3.7, h: 0.9, fontSize: 48, bold: true, color: HEX.accent1, fontFace: THEME.headFontFace });
  txt(s, "PiggyCast-Lin activity at 240 h; its ACC is 0.657. Optimal for RMSE (Murphy 1988).", { x: 9.0, y: 2.65, w: 3.7, h: 0.95, fontSize: 15, color: MUTED });
  txt(s, "0.97", { x: 9.0, y: 3.85, w: 3.7, h: 0.9, fontSize: 48, bold: true, color: C.text2, fontFace: THEME.headFontFace });
  txt(s, "NeuralGCM activity at 240 h: realistic amplitude, larger errors", { x: 9.0, y: 4.8, w: 3.7, h: 0.8, fontSize: 15, color: MUTED });
  txt(s, "Trade-off: lower RMSE, weaker extremes.", { x: 9.0, y: 5.85, w: 3.7, h: 0.5, fontSize: 15, bold: true, color: HEX.accent6 });

  // ---------- 12. case study ----------
  s = content("A case where damping costs skill", "Results",
    "The November-December test case with the largest Northern Hemisphere anomaly: 240 h forecasts valid 00 UTC 28 Dec 2020. NeuralGCM has a realistic amplitude but misplaces the pattern. The average and PiggyCast-Lin both smooth; here PiggyCast-Lin smooths too much and is worse than the plain average. The paper shows this case on purpose.");
  s.addImage({ path: IMG("fig_case_study.png"), x: 0.6, y: 1.4, w: 10.0, h: 10.0 * 1041 / 2095, altText: "Northern Hemisphere Z500 anomaly maps for ERA5, NeuralGCM, the multi-model mean and PiggyCast-Lin, 240 h forecasts valid 28 December 2020", objectName: "Case study maps" });
  const cs = [["1324", "NeuralGCM", COL.neuralgcm], ["939", "Multi-model mean", COL.mmm], ["998", "PiggyCast-Lin", HEX.accent1]];
  txt(s, "NH RMSE, m² s⁻²", { x: 10.9, y: 1.5, w: 1.9, h: 0.4, fontSize: 13, color: MUTED });
  cs.forEach(([v, l, c], i) => {
    txt(s, v, { x: 10.9, y: 1.95 + i * 1.25, w: 1.9, h: 0.7, fontSize: 36, bold: true, color: c, fontFace: THEME.headFontFace });
    txt(s, l, { x: 10.9, y: 2.6 + i * 1.25, w: 1.9, h: 0.45, fontSize: 14, color: MUTED });
  });
  txt(s, "Anomaly amplitude: ERA5 1376, NeuralGCM 1326, MMM 893, PiggyCast-Lin 720.", { x: 0.6, y: 1.4 + 10.0 * 1041 / 2095 + 0.25, w: 12.1, h: 0.45, fontSize: 15, color: C.text1 });

  // ---------- 13. weights ----------
  s = content("What the stack learns changes with lead time", "Results",
    "PiggyCast-Lin weights, mean over 10 folds. At 24 h it trusts NeuralGCM (0.59). By 240 h the four models are weighted almost equally and climatology gets 0.21, which is the learned damping. In the thesis XGBoost, mean |SHAP| for latitude rises from 3 to 201 m^2 s^-2 between 24 and 240 h: the trees use location to imitate climatology.");
  s.addChart(pres.charts.LINE, series(["neuralgcm", "graphcast", "ifshres", "pangu", "clim"], D.w), lineOpts({
    chartColors: [COL.neuralgcm, COL.graphcast, COL.ifshres, COL.pangu, COL.clim],
    valAxisTitle: "Regression weight", showValAxisTitle: true, valAxisMinVal: -0.1, valAxisMaxVal: 0.7, valAxisMajorUnit: 0.1, valAxisLabelFormatCode: "0.0",
  }));
  txt(s, "0.59 → 0.24", { x: 9.0, y: 1.7, w: 3.7, h: 0.9, fontSize: 40, bold: true, color: C.text2, fontFace: THEME.headFontFace });
  txt(s, "NeuralGCM weight, 24 h → 240 h: from trusting one model to an even blend", { x: 9.0, y: 2.6, w: 3.7, h: 0.8, fontSize: 15, color: MUTED });
  txt(s, "0 → 0.21", { x: 9.0, y: 3.6, w: 3.7, h: 0.9, fontSize: 40, bold: true, color: HEX.accent6, fontFace: THEME.headFontFace });
  txt(s, "climatology weight: learned damping", { x: 9.0, y: 4.5, w: 3.7, h: 0.5, fontSize: 15, color: MUTED });
  txt(s, "Thesis XGBoost does the same via latitude: mean |SHAP| 3 → 201.", { x: 9.0, y: 5.4, w: 3.7, h: 0.8, fontSize: 15, italic: true, color: C.text1 });

  // ---------- 14. why xgb ----------
  s = content("Why the thesis XGBoost falls short", "Results",
    "Chart: 240 h RMSE relative to the multi-model mean as the training window grows from 15 to 120 days. PiggyCast-Lin is about 2% better than the MMM from 15 days on. Both XGBoost versions improve with more data, but at 120 days the thesis version is still 5.6% worse than the MMM. At 24 h the thesis model's training RMSE is 39.6, already above the MMM's test RMSE of 32.3: trees predicting absolute Z500 across a 44,000-59,000 m^2 s^-2 range cannot resolve 30-unit differences. Predicting the residual from the MMM (XGB-R) fixes most of this.");
  s.addChart(pres.charts.LINE, ["lin_clim", "xgb_resid", "xgb_orig"].map((k) => ({ name: NAME[k], labels: D.trn_days.map(String), values: D.trn[k] })), lineOpts({
    w: 6.6, chartColors: [COL.lin_clim, COL.xgb_resid, COL.xgb_orig],
    catAxisTitle: "Training window (days)", valAxisTitle: "240 h RMSE vs multi-model mean (%)", showValAxisTitle: true,
    valAxisMinVal: -5, valAxisMaxVal: 20, valAxisMajorUnit: 5,
  }));
  const why = [
    [md.MdStraighten, "Wrong scale of target", "Trees predict absolute Z500 over a 44,000–59,000 range; at 24 h even the training RMSE (39.6) is worse than the MMM on test (32.3)."],
    [md.MdBuild, "Residual target fixes most of it", "PiggyCast-XGB-R learns ERA5 − MMM: 29.4 at 24 h, the best of all methods at that lead."],
    [md.MdTrendingUp, "More data helps, slowly", "At 120 training days the thesis XGBoost is still 5.6% worse than the MMM at 240 h."],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 1.6 + i * 1.75;
    await circleIcon(s, 7.6, y, 0.7, why[i][0], i === 1 ? HEX.accent3 : HEX.dk2, why[i][1]);
    txt(s, why[i][1], { x: 8.5, y: y - 0.05, w: 4.2, h: 0.45, fontSize: 18, bold: true, color: C.text2 });
    txt(s, why[i][2], { x: 8.5, y: y + 0.42, w: 4.2, h: 1.2, fontSize: 14, color: C.text1 });
  }

  // ---------- 15. corrections ----------
  pres.addSection({ title: "Discussion" });
  s = content("Corrections to the thesis analysis", "Discussion",
    "Four things in the thesis analysis that the paper fixes. None of them changes the conclusion that stacking helps; two of them change how good the XGBoost model looked. Units: WB2's geopotential is in m^2 s^-2; the thesis, slides and tutorial say metres. Divide by g = 9.81 for geopotential height.");
  const corr = [
    [md.MdLockOpen, "Train/test leakage", "A fixed 5-day gap is shorter than leads above 120 h. Fixing it: PiggyCast-Lin +0.07% at 240 h, thesis XGBoost +2.4%."],
    [md.MdEventBusy, "Missing rows", "The outer merge left NaN rows at every lead except 72 h (Pangu and NeuralGCM have 2020 inits only). Now: one common valid window."],
    [md.MdSquareFoot, "Units", "Z500 is geopotential in m² s⁻², not metres. Divide by g ≈ 9.81 for geopotential height."],
    [md.MdScatterPlot, "MDS figure", "Kruskal stress-1 is 0.24, so the 2-D map distorts distances; the 'S-shape' is not real. Replaced by a dendrogram."],
  ];
  for (const [i, [ic, t, d]] of corr.entries()) {
    const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.55;
    card(s, x, y, 5.95, 2.3, "Correction card " + (i + 1));
    await circleIcon(s, x + 0.3, y + 0.35, 0.75, ic, HEX.accent6, t);
    txt(s, t, { x: x + 1.3, y: y + 0.35, w: 4.4, h: 0.5, fontSize: 20, bold: true, color: C.text2, fontFace: THEME.headFontFace });
    txt(s, d, { x: x + 1.3, y: y + 0.9, w: 4.4, h: 1.25, fontSize: 15, color: C.text1 });
  }

  // ---------- 16. more data ----------
  s = content("Would more data help XGBoost?", "Discussion",
    "Asked: would 2018-2022 data at 0.25 degree (1440 x 721) help? Not with all four models: in WeatherBench 2, NeuralGCM and operational GraphCast exist for 2020 only, and NeuralGCM's finest grid is about 0.7 degree. More grid points mostly add spatially correlated samples, not new weather; the number of independent days is what limits the trees. The training-length test suggests XGBoost improves with more days but stays behind. Feasible next runs: a multi-year two-model test (IFS HRES + Pangu HRES-init, 2020-2022) and a 1.5 degree robustness run with all four.");
  const av = [["Model (WB2)", "Years available", "Finest grid"], ["IFS HRES", "2016–2022", "0.25°"], ["Pangu-Weather (HRES-init)", "2020–2022", "0.25°"], ["GraphCast (HRES-init)", "2020", "0.25°"], ["NeuralGCM", "2020", "≈ 0.7°"]];
  s.addTable(av.map((r, i) => r.map((t, j) => cell(t, i === 0 ? { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 } } : { align: j === 0 ? "left" : "center", fill: { color: i >= 3 && j === 1 ? "FBE3E4" : "FFFFFF" } }))),
    { x: 0.6, y: 1.6, w: 6.4, colW: [2.9, 1.9, 1.6], rowH: 0.5, border: { type: "solid", pt: 0.75, color: "D9DEE5" }, objectName: "Availability table" });
  txt(s, "All four models overlap only in 2020. Independent weather days, not grid points, limit the trees.", { x: 0.6, y: 4.3, w: 6.4, h: 0.8, fontSize: 15, italic: true, color: C.text2 });
  const nxt = [["A", "Multi-year, two models", "IFS HRES + Pangu, 2020–2022: does XGBoost catch the linear stack with 3 years?"], ["B", "1.5° robustness", "All four models at 240 × 121: does the ranking hold at higher resolution?"], ["C", "More variables", "T850 and 2 m temperature, to show the result generalises beyond Z500"]];
  nxt.forEach(([l, t, d], i) => {
    const y = 1.6 + i * 1.6;
    s.addShape(pres.shapes.OVAL, { x: 7.5, y, w: 0.6, h: 0.6, fill: { color: HEX.accent1 }, line: { color: HEX.accent1 }, objectName: "Next " + l });
    txt(s, l, { x: 7.5, y, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
    txt(s, t, { x: 8.3, y: y - 0.02, w: 4.4, h: 0.45, fontSize: 18, bold: true, color: C.text2 });
    txt(s, d, { x: 8.3, y: y + 0.42, w: 4.4, h: 1.0, fontSize: 14, color: C.text1 });
  });

  // ---------- 17. questions ----------
  s = content("Questions for co-authors", "Discussion",
    "Decisions we need before submission to AMS AI for the Earth Systems (and arXiv).");
  const qs = [
    ["Framing", "PiggyCast as a stacking framework, with the 6-parameter linear stack as the main result and the thesis XGBoost as an informative negative. Agree?"],
    ["NeuralGCM initialisation", "Paper says ERA5-initialised (Kochkov et al. 2024); WB2 docs are silent. Can someone confirm?"],
    ["Damping and extremes", "Add an extremes-focused or spectral metric to make the RMSE-vs-amplitude trade-off explicit?"],
    ["Scope before submission", "Run A, B and/or C from the previous slide, or submit Z500-only?"],
  ];
  qs.forEach(([t, d], i) => {
    const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.55;
    card(s, x, y, 5.95, 2.3, "Question card " + (i + 1));
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.35, w: 0.6, h: 0.6, fill: { color: HEX.dk2 }, line: { color: HEX.dk2 }, objectName: "Question number " + (i + 1) });
    txt(s, String(i + 1), { x: x + 0.3, y: y + 0.35, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
    txt(s, t, { x: x + 1.15, y: y + 0.38, w: 4.55, h: 0.5, fontSize: 20, bold: true, color: C.text2, fontFace: THEME.headFontFace });
    txt(s, d, { x: x + 1.15, y: y + 0.95, w: 4.55, h: 1.2, fontSize: 15, color: C.text1 });
  });

  // ---------- 18. close ----------
  s = pres.addSlide({ masterName: "Section (dark)", sectionTitle: "Discussion" });
  s.addText("Thank you", { placeholder: "title" });
  s.addText([
    { text: "Code, data pipeline and results notebook:", options: { breakLine: true } },
    { text: "github.com/josiahkim29/AIMS_Masters_Thesis", options: { bold: true, color: "FFFFFF", hyperlink: { url: "https://github.com/josiahkim29/AIMS_Masters_Thesis/tree/piggycast-paper" } } },
  ], { placeholder: "body" });
  s.addNotes("Pointers: paper draft PiggyCast_Arxiv_Paper/PiggyCast_draft.pdf; notebook PiggyCast_Arxiv_Paper/experiments/notebooks/PiggyCast_results.ipynb; reproduce everything with: cd PiggyCast_Arxiv_Paper/experiments && uv sync && ./run_all.sh. Code is on the piggycast-paper branch until it is merged into main.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();

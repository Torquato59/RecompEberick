import { BeamView3D } from './beam3d.js';
import type { BeamInput, Result, ValidationReport } from './types.js';
type ChartKey = 'shear_kn' | 'moment_kn_m' | 'deflection_mm';

function get<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`Elemento ausente: ${selector}`);
  return element;
}
const form = get<HTMLFormElement>('#beam-form');
const feedback = get<HTMLDivElement>('#feedback');
const resultsColumn = get<HTMLDivElement>('.results-column');
const calculateButton = get<HTMLButtonElement>('#calculate');
const importButton = get<HTMLButtonElement>('#import-project');
const exportButton = get<HTMLButtonElement>('#export-project');
const printButton = get<HTMLButtonElement>('#print-report');
const fileInput = get<HTMLInputElement>('#project-file');
let lastModel: BeamInput | null = null;
let lastResult: Result | null = null;
let editVersion = 0;
let requestId = 0;
let busy = false;
let dirty = true;
let view3D: BeamView3D | null = null;
let sceneUnavailable = false;
let validationReport: ValidationReport | null = null;
const example: BeamInput = { span_m: 6, elastic_modulus_gpa: 30, width_m: 0.2, height_m: 0.5, uniform_load_kn_m: 12, point_load_kn: 0, point_position_m: 3 };

function fmt(value: number, digits = 2): string {
  return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Math.abs(value) < 1e-10 ? 0 : value);
}
function compact(value: number): string {
  if (value !== 0 && (Math.abs(value) >= 1e6 || Math.abs(value) < 0.001)) {
    return value.toExponential(2).replace('.', ',');
  }
  return fmt(value);
}
function input(name: string): HTMLInputElement {
  return get<HTMLInputElement>(`[name="${name}"]`);
}
function readModel(): BeamInput {
  return {
    span_m: input('span_m').valueAsNumber,
    elastic_modulus_gpa: input('elastic_modulus_gpa').valueAsNumber,
    width_m: input('width_cm').valueAsNumber / 100,
    height_m: input('height_cm').valueAsNumber / 100,
    uniform_load_kn_m: input('uniform_load_kn_m').valueAsNumber,
    point_load_kn: input('point_load_kn').valueAsNumber,
    point_position_m: input('point_position_m').valueAsNumber,
  };
}
function writeModel(model: BeamInput): void {
  for (const [key, value] of Object.entries(model)) {
    const name = key === 'width_m' ? 'width_cm' : key === 'height_m' ? 'height_cm' : key;
    input(name).value = String(key === 'width_m' || key === 'height_m' ? value * 100 : value);
  }
  updatePointLimit();
}
function updatePointLimit(): void {
  input('point_position_m').max = String(input('span_m').valueAsNumber || 0);
}
function message(text: string, state: '' | 'error' | 'stale' = ''): void {
  feedback.textContent = text;
  feedback.className = `feedback ${state}`;
}
function updateButtons(): void {
  calculateButton.disabled = busy;
  importButton.disabled = busy;
  exportButton.disabled = busy || dirty || !lastResult;
  printButton.disabled = busy || dirty || !lastResult;
  document.querySelectorAll<HTMLButtonElement>('[data-case-id]').forEach(button => { button.disabled = busy; });
  calculateButton.textContent = busy ? 'Calculando…' : 'Calcular estrutura →';
}
function markDirty(): void {
  editVersion++;
  dirty = true;
  updatePointLimit();
  resultsColumn.classList.add('stale-results');
  message('Dados alterados. Calcule novamente para atualizar os resultados.', 'stale');
  updateButtons();
}

function svgElement<K extends keyof SVGElementTagNameMap>(name: K, attrs: Record<string, string | number> = {}, text?: string): SVGElementTagNameMap[K] {
  const element = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, String(value));
  if (text !== undefined) element.textContent = text;
  return element;
}
function drawBeam(model: BeamInput): void {
  const svg = get<SVGSVGElement>('#beam-model');
  svg.replaceChildren();
  svg.append(svgElement('title', {}, `Viga com vão de ${fmt(model.span_m)} metros, carga distribuída de ${fmt(model.uniform_load_kn_m)} kN/m e pontual de ${fmt(model.point_load_kn)} kN.`));
  const start = 92, end = 808, beamY = 118;
  const textScale = svg.clientWidth < 500 ? 1.5 : 1;
  const xAt = (x: number): number => start + (end - start) * x / model.span_m;
  // Linha de base, seção e apoios A (articulação) e B (rolete).
  svg.append(svgElement('rect', { x: start, y: beamY, width: end - start, height: 9, rx: 1, fill: '#294a55' }));
  for (const [x, name] of [[start, 'A'], [end, 'B']] as const) {
    svg.append(svgElement('path', { d: `M${x},128 l-12,21 h24 Z`, fill: '#e7eeed', stroke: '#5d777d', 'stroke-width': 1.3 }));
    if (name === 'B') {
      for (const dx of [-6, 6]) svg.append(svgElement('circle', { cx: x + dx, cy: 153, r: 3, fill: '#fff', stroke: '#6e878b' }));
    }
    const groundY = name === 'B' ? 159 : 153;
    svg.append(svgElement('path', { d: `M${x - 22},${groundY}h44`, stroke: '#9aadb1', 'stroke-width': 1 }));
    svg.append(svgElement('text', { x, y: 177, 'text-anchor': 'middle', fill: '#48676c', 'font-size': 12 * textScale, 'font-weight': 600 }, name));
  }
  const arrow = (x: number, top: number, bottom: number, color: string): void => {
    svg.append(svgElement('path', { d: `M${x},${top}V${bottom}m-4,-7l4,7l4,-7`, fill: 'none', stroke: color, 'stroke-width': 1.6, 'stroke-linecap': 'round' }));
  };
  if (model.uniform_load_kn_m > 0) {
    svg.append(svgElement('path', { d: `M${start},61H${end}`, stroke: '#62b9a9', 'stroke-width': 1.2 }));
    for (let i = 0; i <= 20; i++) arrow(start + (end - start) * i / 20, 61, 109, '#62b9a9');
    svg.append(svgElement('text', { x: (start + end) / 2, y: 43, 'text-anchor': 'middle', fill: '#3d8e80', 'font-size': 12 * textScale }, `q = ${compact(model.uniform_load_kn_m)} kN/m`));
  }
  if (model.point_load_kn > 0) {
    const x = xAt(model.point_position_m);
    arrow(x, 28, 113, '#b27b38');
    svg.append(svgElement('rect', { x: x - 59, y: 7, width: 118, height: 19, rx: 3, fill: '#fffaf0' }));
    svg.append(svgElement('text', { x, y: 20, 'text-anchor': 'middle', fill: '#a07136', 'font-size': 11 * textScale }, `P = ${compact(model.point_load_kn)} kN`));
    svg.append(svgElement('text', { x: x + (x > 700 ? -12 : 12), y: 101, 'text-anchor': x > 700 ? 'end' : 'start', fill: '#a07136', 'font-size': 9 * textScale }, `a = ${fmt(model.point_position_m)} m`));
  }
  svg.append(svgElement('path', { d: `M${start},192v15m0,-7H${end}m0,-8v15`, fill: 'none', stroke: '#a6b8ba', 'stroke-width': 1 }));
  svg.append(svgElement('rect', { x: 386, y: 190, width: 128, height: 20, fill: '#fff' }));
  svg.append(svgElement('text', { x: 450, y: 204, 'text-anchor': 'middle', fill: '#789196', 'font-size': 11 * textScale }, `${fmt(model.span_m)} m`));
  get('#span-summary').textContent = `L = ${fmt(model.span_m)} m`;
}

function drawChart(id: string, result: Result, model: BeamInput, key: ChartKey, unit: string, positiveDown: boolean): void {
  const svg = get<SVGSVGElement>(`#${id}-chart`);
  svg.replaceChildren();
  const wide = id === 'deflection' && window.matchMedia('(min-width: 1201px)').matches;
  const width = wide ? 960 : 480;
  svg.setAttribute('viewBox', `0 0 ${width} 200`);
  const left = 52, right = width - 16, top = 27, bottom = 163;
  const values = result.samples.map(s => s[key]);
  const minimum = Math.min(0, ...values), maximum = Math.max(0, ...values);
  const extent = maximum - minimum;
  const low = extent > 1e-12 ? minimum : -1;
  const high = extent > 1e-12 ? maximum : 1;
  const padding = (high - low) * 0.12;
  const yMin = low - padding, yMax = high + padding;
  const xAt = (x: number): number => left + (right - left) * x / model.span_m;
  const yAt = (value: number): number => positiveDown
    ? top + (value - yMin) / (yMax - yMin) * (bottom - top)
    : bottom - (value - yMin) / (yMax - yMin) * (bottom - top);
  const zeroY = yAt(0);
  const ticks = [...new Set([minimum, 0, maximum])];
  for (const value of ticks) {
    const y = yAt(value);
    svg.append(svgElement('path', { d: `M${left},${y}H${right}`, stroke: value === 0 ? '#aababb' : '#e7eeee', 'stroke-width': value === 0 ? 1 : 0.7, 'stroke-dasharray': value === 0 ? '' : '3 5' }));
    svg.append(svgElement('text', { x: left - 9, y: y + 3, 'text-anchor': 'end' }, compact(value)));
  }
  for (let i = 0; i <= 4; i++) {
    const x = left + (right - left) * i / 4;
    svg.append(svgElement('path', { d: `M${x},${top}V${bottom}`, stroke: '#edf2f1', 'stroke-width': 0.7, 'stroke-dasharray': '2 5' }));
    svg.append(svgElement('text', { x, y: 185, 'text-anchor': i === 4 ? 'end' : 'middle' }, `${fmt(model.span_m * i / 4, 1)}${i === 4 ? ' m' : ''}`));
  }
  const line = result.samples.map((s, i) => `${i === 0 ? 'M' : 'L'}${xAt(s.x_m)},${yAt(s[key])}`).join(' ');
  const color = id === 'shear' ? '#5a91a5' : id === 'moment' ? '#198c7e' : '#b39156';
  const fill = id === 'shear' ? '#e9f1f5' : id === 'moment' ? '#e3f1eb' : '#f7f1e6';
  svg.append(svgElement('path', { d: `${line} L${right},${zeroY} L${left},${zeroY} Z`, fill, opacity: 0.9 }));
  svg.append(svgElement('path', { d: line, fill: 'none', stroke: color, 'stroke-width': 2, 'stroke-linejoin': 'round' }));
  const focus = svgElement('g', { visibility: 'hidden', 'pointer-events': 'none' });
  const cursorLine = svgElement('line', { y1: top, y2: bottom, stroke: '#7e999b', 'stroke-width': 1, 'stroke-dasharray': '3 3' });
  const cursorDot = svgElement('circle', { r: 4, fill: color, stroke: '#fff', 'stroke-width': 1.5 });
  focus.append(cursorLine, cursorDot);
  svg.append(focus);
  const reading = get(`#${id}-reading`);
  svg.onpointermove = event => {
    const matrix = svg.getScreenCTM();
    if (!matrix) return;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    const x = Math.max(0, Math.min(model.span_m, (point.x - left) / (right - left) * model.span_m));
    let nearest = result.samples[0]!;
    for (const sample of result.samples) if (Math.abs(sample.x_m - x) <= Math.abs(nearest.x_m - x)) nearest = sample;
    cursorLine.setAttribute('x1', String(xAt(nearest.x_m)));
    cursorLine.setAttribute('x2', String(xAt(nearest.x_m)));
    cursorDot.setAttribute('cx', String(xAt(nearest.x_m)));
    cursorDot.setAttribute('cy', String(yAt(nearest[key])));
    focus.setAttribute('visibility', 'visible');
    const discontinuity = key === 'shear_kn' && nearest.x_m === model.point_position_m && model.point_load_kn > 0 ? ' · após P' : '';
    reading.textContent = `x = ${fmt(nearest.x_m)} m · ${compact(nearest[key])} ${unit}${discontinuity}`;
  };
  svg.onpointerleave = () => {
    focus.setAttribute('visibility', 'hidden');
    reading.textContent = id === 'deflection' ? 'Deformação representada em escala ampliada' : 'Passe o cursor pelo diagrama';
  };
}

function metric(selector: string, value: number, unit: string): void {
  const target = get(selector);
  target.textContent = compact(value);
  const label = document.createElement('span');
  label.className = 'unit';
  label.textContent = unit;
  target.append(label);
}
function render(model: BeamInput, result: Result): void {
  drawBeam(model);
  if (!sceneUnavailable) {
    try {
      view3D ??= new BeamView3D(get('#beam-3d'), get('#scene-status'));
      view3D.update(model, result);
    } catch {
      sceneUnavailable = true;
      get('#scene-status').textContent = '3D indisponível neste navegador. Os cálculos e o esquema 2D continuam disponíveis.';
      get('#beam-3d').textContent = 'Ative a aceleração gráfica ou use um navegador com WebGL 2.';
      document.querySelectorAll<HTMLButtonElement>('.scene-controls button').forEach(button => { button.disabled = true; });
      get<HTMLInputElement>('#show-deformed').disabled = true;
    }
  }
  metric('#reaction-a', result.reactions.left_kn, 'kN');
  metric('#reaction-b', result.reactions.right_kn, 'kN');
  metric('#max-moment', result.extrema.moment_kn_m, 'kN·m');
  metric('#max-deflection', result.extrema.deflection_mm, 'mm');
  get('#moment-location').textContent = `em x = ${fmt(result.extrema.moment_position_m)} m`;
  get('#deflection-location').textContent = `em x = ${fmt(result.extrema.deflection_position_m)} m · para baixo`;
  get('#section-inertia').textContent = `I = ${result.inertia_m4.toExponential(3).replace('.', ',')} m⁴`;
  const properties = get('#model-properties');
  properties.textContent = `Seção ${fmt(model.width_m * 100, 1)} × ${fmt(model.height_m * 100, 1)} cm · E = ${compact(model.elastic_modulus_gpa)} GPa · I = ${result.inertia_m4.toExponential(3).replace('.', ',')} m⁴`;
  const loads = document.createElement('div');
  loads.textContent = `q = ${compact(model.uniform_load_kn_m)} kN/m · P = ${compact(model.point_load_kn)} kN · a = ${fmt(model.point_position_m)} m`;
  properties.append(loads);
  const elastic = result.elastic_results;
  metric('#bending-stress', elastic.max_bending_stress_mpa, 'MPa');
  metric('#shear-stress', elastic.max_shear_stress_mpa, 'MPa');
  metric('#total-load', elastic.total_load_kn, 'kN');
  get('#rotation-a').textContent = `${fmt(elastic.left_rotation_mrad, 3)} mrad`;
  get('#rotation-b').textContent = `${fmt(elastic.right_rotation_mrad, 3)} mrad`;
  get('#section-area').textContent = `${compact(result.section.area_m2 * 10000)} cm²`;
  get('#section-modulus').textContent = `${compact(result.section.section_modulus_m3 * 1e6)} cm³`;
  get('#flexural-rigidity').textContent = `${compact(result.flexural_rigidity_kn_m2)} kN·m²`;
  get('#calculation-memory').textContent = [
    `A = b × h = ${result.section.area_m2.toExponential(6)} m²`,
    `I = b × h³ / 12 = ${result.inertia_m4.toExponential(6)} m⁴`,
    `W = I / (h/2) = ${result.section.section_modulus_m3.toExponential(6)} m³`,
    `EI = E × 10⁶ × I = ${compact(result.flexural_rigidity_kn_m2)} kN·m²`,
    `RA = qL/2 + P(L−a)/L = ${compact(result.reactions.left_kn)} kN`,
    `RB = qL/2 + Pa/L = ${compact(result.reactions.right_kn)} kN`,
    `σmáx = Mmáx / W / 1000 = ${compact(elastic.max_bending_stress_mpa)} MPa`,
    `τmáx = 1,5 × |Vmáx| / A / 1000 = ${compact(elastic.max_shear_stress_mpa)} MPa`,
    `θA = δ′(0) = ${fmt(elastic.left_rotation_mrad, 3)} mrad`,
    `θB = δ′(L) = ${fmt(elastic.right_rotation_mrad, 3)} mrad`,
  ].join('\n');
  const force = result.equilibrium.force_residual_kn;
  const moment = result.equilibrium.moment_residual_kn_m;
  const load = model.uniform_load_kn_m * model.span_m + model.point_load_kn;
  const balanced = Math.abs(force) <= Math.max(1, load) * 1e-10 && Math.abs(moment) <= Math.max(1, load * model.span_m) * 1e-10;
  get('#equilibrium').textContent = `${balanced ? '✓ Equilíbrio numérico conferido' : 'Atenção: resíduo de equilíbrio'} · ΣFy = ${force.toExponential(1)} kN · ΣMA = ${moment.toExponential(1)} kN·m`;
  drawChart('shear', result, model, 'shear_kn', 'kN', false);
  drawChart('moment', result, model, 'moment_kn_m', 'kN·m', true);
  drawChart('deflection', result, model, 'deflection_mm', 'mm', true);
}

async function runCalculation(model: BeamInput, replaceForm = false): Promise<void> {
  const thisRequest = ++requestId;
  const startVersion = editVersion;
  busy = true;
  dirty = true;
  resultsColumn.classList.add('stale-results');
  updateButtons();
  message('Calculando reações, esforços e deslocamentos…');
  try {
    const response = await fetch('/api/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(model),
      signal: AbortSignal.timeout(15_000),
    });
    const data: Result & { error?: string } = await response.json();
    if (thisRequest !== requestId) return;
    if (editVersion !== startVersion) {
      message('Dados alterados durante o cálculo. Calcule novamente para atualizar.', 'stale');
      return;
    }
    if (!response.ok) throw new Error(data.error || 'Não foi possível calcular o modelo.');
    if (replaceForm) writeModel(model);
    lastModel = model;
    lastResult = data;
    dirty = false;
    render(model, data);
    resultsColumn.classList.remove('stale-results');
    message('Análise concluída · resultados correspondem aos dados atuais.');
  } catch (error) {
    if (thisRequest === requestId && editVersion === startVersion) {
      message(error instanceof Error && error.name !== 'TypeError' ? error.message : 'Não foi possível acessar o cálculo. Verifique se o servidor está ativo.', 'error');
    }
  } finally {
    if (thisRequest === requestId) {
      busy = false;
      updateButtons();
    }
  }
}

form.addEventListener('input', markDirty);
form.addEventListener('submit', event => {
  event.preventDefault();
  if (!busy && form.reportValidity()) void runCalculation(readModel());
});
get('#reset-example').addEventListener('click', () => {
  if (busy) return;
  writeModel(example);
  markDirty();
  void runCalculation({ ...example });
});
exportButton.addEventListener('click', () => {
  if (dirty || !lastModel) return;
  const project = { format: 'estrutura-beam', version: 1, units: 'm-kN-GPa', model: lastModel };
  const blob = new Blob([JSON.stringify(project, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'estrutura-viga-v01.json';
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
importButton.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', async () => {
  const file = fileInput.files?.[0];
  if (!file || busy) return;
  try {
    if (file.size > 16_384) throw new Error('O arquivo de projeto deve ter no máximo 16 KiB.');
    const project: unknown = JSON.parse(await file.text());
    if (typeof project !== 'object' || project === null) throw new Error('Arquivo de projeto inválido.');
    const data = project as Record<string, unknown>;
    if (data.format !== 'estrutura-beam' || data.version !== 1 || data.units !== 'm-kN-GPa' || typeof data.model !== 'object' || data.model === null) {
      throw new Error('Use um projeto Estrutura versão 1, com unidades m-kN-GPa.');
    }
    await runCalculation(data.model as BeamInput, true);
  } catch (error) {
    message(error instanceof SyntaxError ? 'O arquivo não contém JSON válido.' : error instanceof Error ? error.message : 'Não foi possível abrir o projeto.', 'error');
  } finally {
    fileInput.value = '';
  }
});
printButton.addEventListener('click', () => { if (!dirty && lastResult) window.print(); });
get<HTMLInputElement>('#show-deformed').addEventListener('change', event => {
  view3D?.setDeformed((event.target as HTMLInputElement).checked);
});
get('#reset-camera').addEventListener('click', () => view3D?.reset());
get('#zoom-in').addEventListener('click', () => view3D?.zoom(0.8));
get('#zoom-out').addEventListener('click', () => view3D?.zoom(1.25));

async function loadValidation(): Promise<void> {
  const status = get('#validation-status');
  try {
    const response = await fetch('/api/validation', { signal: AbortSignal.timeout(15_000) });
    if (!response.ok) throw new Error('Não foi possível obter os casos de referência.');
    validationReport = await response.json() as ValidationReport;
    status.textContent = `${validationReport.passed_cases}/${validationReport.total_cases} casos · ${validationReport.passed_checks}/${validationReport.total_checks} comparações dentro da tolerância`;
    status.classList.toggle('validation-failed', !validationReport.passed);
    const tbody = get('#validation-body');
    tbody.replaceChildren();
    for (const test of validationReport.cases) {
      const row = document.createElement('tr');
      const values = [test.label, ...['left_kn', 'right_kn', 'moment_kn_m', 'deflection_mm'].map(quantity => compact(test.checks.find(check => check.quantity === quantity)!.analytical)), test.passed ? 'Conferido' : 'Divergência'];
      for (const value of values) { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); }
      row.lastElementChild!.classList.add(test.passed ? 'check-passed' : 'check-failed');
      const action = document.createElement('td');
      const button = document.createElement('button');
      button.className = 'button case-button';
      button.type = 'button';
      button.textContent = 'Carregar';
      button.dataset.caseId = test.id;
      button.setAttribute('aria-label', `Carregar caso: ${test.label}`);
      button.addEventListener('click', () => {
        if (busy) return;
        writeModel(test.model);
        markDirty();
        void runCalculation({ ...test.model });
      });
      action.append(button); row.append(action); tbody.append(row);
    }
    get<HTMLButtonElement>('#download-validation').disabled = false;
    updateButtons();
  } catch (error) {
    status.textContent = error instanceof Error ? error.message : 'Conferência indisponível.';
    status.classList.add('validation-failed');
  }
}
get('#download-validation').addEventListener('click', () => {
  if (!validationReport) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(validationReport, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = 'estrutura-conferencia-elastica.json'; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
let resizeTimer: ReturnType<typeof setTimeout>;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (lastResult && lastModel) {
      drawBeam(lastModel);
      drawChart('deflection', lastResult, lastModel, 'deflection_mm', 'mm', true);
    }
  }, 100);
});
writeModel(example);
updateButtons();
void runCalculation({ ...example });
void loadValidation();

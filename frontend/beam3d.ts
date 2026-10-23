import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { BeamInput, Result } from './types.js';

/** Representação espacial de um modelo de viga 1D; não é uma análise de sólidos. */
export class BeamView3D {
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(34, 1, 0.001, 10000);
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;
  private group = new THREE.Group();
  private observer: ResizeObserver;
  private model: BeamInput | null = null;
  private result: Result | null = null;
  private deformed = false;
  private scale = 1;
  private request = 0;
  private captureRequested = false;
  private printImage = document.createElement('img');

  constructor(private container: HTMLElement, private status: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0xf4f8f7, 1);
    this.renderer.domElement.setAttribute('aria-label', 'Modelo 3D da viga. Arraste para girar; use a roda do mouse para aproximar.');
    this.renderer.domElement.setAttribute('role', 'img');
    this.renderer.domElement.tabIndex = 0;
    container.append(this.renderer.domElement);
    this.printImage.className = 'scene-print-image';
    this.printImage.alt = 'Vista 3D da viga correspondente aos resultados impressos';
    container.append(this.printImage);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enablePan = false;
    this.controls.minPolarAngle = 0.12;
    this.controls.maxPolarAngle = Math.PI * 0.9;
    this.controls.addEventListener('change', () => this.render());
    this.controls.addEventListener('end', () => this.render(true));
    this.scene.add(new THREE.HemisphereLight(0xeef8ff, 0x708b88, 2.5));
    const light = new THREE.DirectionalLight(0xffffff, 3);
    light.position.set(-5, 8, 6);
    this.scene.add(light, this.group);
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(container);
    this.renderer.domElement.addEventListener('keydown', event => {
      if (event.key === '+' || event.key === '=') { event.preventDefault(); this.zoom(0.85); }
      if (event.key === '-') { event.preventDefault(); this.zoom(1.15); }
      if (event.key === 'Home') { event.preventDefault(); this.reset(); }
      if (event.key.startsWith('Arrow')) {
        event.preventDefault();
        const relative = this.camera.position.clone().sub(this.controls.target);
        const spherical = new THREE.Spherical().setFromVector3(relative);
        spherical.theta += event.key === 'ArrowLeft' ? 0.12 : event.key === 'ArrowRight' ? -0.12 : 0;
        spherical.phi = THREE.MathUtils.clamp(spherical.phi + (event.key === 'ArrowUp' ? -0.1 : event.key === 'ArrowDown' ? 0.1 : 0), 0.12, Math.PI * 0.9);
        this.camera.position.copy(new THREE.Vector3().setFromSpherical(spherical).add(this.controls.target));
        this.controls.update();
      }
    });
    this.renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      status.textContent = 'A visualização foi interrompida. Recarregue a página para restaurar o 3D.';
      container.dataset.ready = 'false';
    });
    window.addEventListener('beforeprint', () => {
      this.renderer.render(this.scene, this.camera);
      this.printImage.src = this.renderer.domElement.toDataURL('image/png');
    });
  }

  update(model: BeamInput, result: Result): void {
    const geometryChanged = !this.model || ['span_m', 'width_m', 'height_m'].some(key =>
      this.model![key as keyof BeamInput] !== model[key as keyof BeamInput]);
    this.model = model;
    this.result = result;
    this.build();
    if (geometryChanged) this.reset();
    this.resize();
    this.container.dataset.ready = 'true';
  }

  setDeformed(value: boolean): void { this.deformed = value; this.build(); }

  reset(): void {
    if (!this.model) return;
    const model = this.model;
    const extent = Math.max(model.span_m, model.width_m * 1.5, model.height_m * 2);
    const aspect = this.container.clientWidth / Math.max(this.container.clientHeight, 1);
    const distance = extent * 1.8 / Math.min(1, aspect);
    this.controls.target.set(model.span_m / 2, model.height_m / 2, 0);
    this.camera.position.copy(this.controls.target).add(new THREE.Vector3(0.95, 0.7, 1.3).normalize().multiplyScalar(distance));
    this.camera.near = extent / 1000;
    this.camera.far = extent * 100;
    this.camera.updateProjectionMatrix();
    this.controls.minDistance = extent * 0.3;
    this.controls.maxDistance = extent * 12;
    this.controls.update();
    this.render(true);
  }

  zoom(factor: number): void {
    const relative = this.camera.position.clone().sub(this.controls.target);
    relative.setLength(THREE.MathUtils.clamp(relative.length() * factor, this.controls.minDistance, this.controls.maxDistance));
    this.camera.position.copy(this.controls.target).add(relative);
    this.controls.update();
    this.render(true);
  }

  private resize(): void {
    const width = Math.max(this.container.clientWidth, 1);
    const height = Math.max(this.container.clientHeight, 1);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.render(true);
  }

  private render(capture = false): void {
    this.captureRequested ||= capture;
    cancelAnimationFrame(this.request);
    this.request = requestAnimationFrame(() => {
      this.renderer.render(this.scene, this.camera);
      if (this.captureRequested) {
        this.printImage.src = this.renderer.domElement.toDataURL('image/png');
        this.captureRequested = false;
      }
    });
  }

  private clear(): void {
    this.group.traverse(object => {
      const mesh = object as THREE.Mesh;
      if (mesh.geometry) mesh.geometry.dispose();
      const materials = mesh.material ? (Array.isArray(mesh.material) ? mesh.material : [mesh.material]) : [];
      for (const material of materials) material.dispose();
    });
    this.group.clear();
  }

  private build(): void {
    if (!this.model || !this.result) return;
    this.clear();
    const m = this.model, r = this.result;
    const extent = Math.max(m.span_m, m.height_m, m.width_m);
    const peak = r.extrema.deflection_mm / 1000;
    this.scale = peak > 0 ? Math.min(1000, m.span_m * 0.07 / peak) : 1;
    const magnification = this.deformed ? this.scale : 0;
    const positions: number[] = [], indices: number[] = [];
    const samples = r.samples.filter((sample, i, list) => i === 0 || sample.x_m !== list[i - 1]!.x_m);
    for (const sample of samples) {
      const offset = -sample.deflection_mm / 1000 * magnification;
      for (const [y, z] of [[0, -m.width_m / 2], [m.height_m, -m.width_m / 2], [m.height_m, m.width_m / 2], [0, m.width_m / 2]]) {
        positions.push(sample.x_m, y! + offset, z!);
      }
    }
    for (let ring = 0; ring < samples.length - 1; ring++) {
      for (let side = 0; side < 4; side++) {
        const a = ring * 4 + side, b = ring * 4 + (side + 1) % 4;
        const c = b + 4, d = a + 4;
        indices.push(a, b, d, b, c, d);
      }
    }
    indices.push(0, 2, 1, 0, 3, 2);
    const last = (samples.length - 1) * 4;
    indices.push(last, last + 1, last + 2, last, last + 2, last + 3);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    const material = new THREE.MeshStandardMaterial({ color: 0x6aa99e, roughness: 0.75, metalness: 0.05, side: THREE.DoubleSide });
    this.group.add(new THREE.Mesh(geometry, material));
    const edges = new THREE.EdgesGeometry(geometry, 22);
    this.group.add(new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x315f5c, transparent: true, opacity: 0.5 })));
    if (this.deformed && peak > 0) {
      const outline = new THREE.EdgesGeometry(new THREE.BoxGeometry(m.span_m, m.height_m, m.width_m));
      const ghost = new THREE.LineSegments(outline, new THREE.LineBasicMaterial({ color: 0x9bb2b0, transparent: true, opacity: 0.45 }));
      ghost.position.set(m.span_m / 2, m.height_m / 2, 0);
      this.group.add(ghost);
    }
    // Apoios apenas esquemáticos, fora do volume da viga.
    const supportSize = Math.min(extent * 0.045, m.height_m * 0.5);
    for (const [x, support] of [[0, m.support_left ?? 'pinned'], [m.span_m, m.support_right ?? 'roller']] as const) {
      if (support === 'free') continue;
      if (support === 'fixed') {
        const thickness = extent * 0.035;
        const wall = new THREE.Mesh(new THREE.BoxGeometry(thickness, m.height_m * 1.6, Math.max(m.width_m * 2, extent * 0.09)), new THREE.MeshStandardMaterial({ color: 0x9cabae, roughness: 1 }));
        wall.position.set(x + (x === 0 ? -thickness / 2 : thickness / 2), m.height_m / 2, 0);
        this.group.add(wall);
        continue;
      }
      const shape = new THREE.Shape();
      shape.moveTo(-supportSize, -supportSize * 1.4);
      shape.lineTo(supportSize, -supportSize * 1.4);
      shape.lineTo(0, 0);
      shape.closePath();
      const supportMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: m.width_m * 1.25, bevelEnabled: false }), new THREE.MeshStandardMaterial({ color: 0xa6b7ba, roughness: 1 }));
      supportMesh.position.set(x, 0, -m.width_m * 0.625);
      this.group.add(supportMesh);
      if (support === 'roller') {
        const wheel = new THREE.Mesh(new THREE.CylinderGeometry(supportSize * 0.25, supportSize * 0.25, m.width_m * 1.25, 16), new THREE.MeshStandardMaterial({ color: 0x728d94 }));
        wheel.rotation.x = Math.PI / 2;
        wheel.position.set(x, -supportSize * 1.65, 0);
        this.group.add(wheel);
      }
    }
    const arrowLength = extent * 0.11;
    if (m.uniform_load_kn_m > 0) {
      for (let i = 0; i <= 12; i++) {
        const arrow = new THREE.ArrowHelper(new THREE.Vector3(0, -1, 0), new THREE.Vector3(m.span_m * i / 12, m.height_m + arrowLength * 1.3, 0), arrowLength, 0x339f8c, arrowLength * 0.2, arrowLength * 0.1);
        this.group.add(arrow);
      }
    }
    if (m.point_load_kn > 0) {
      this.group.add(new THREE.ArrowHelper(new THREE.Vector3(0, -1, 0), new THREE.Vector3(m.point_position_m, m.height_m + arrowLength * 2.2, 0), arrowLength * 1.8, 0xb47c35, arrowLength * 0.3, arrowLength * 0.18));
    }
    const grid = new THREE.GridHelper(extent * 1.5, 16, 0xd0dfda, 0xe3ece8);
    grid.position.set(m.span_m / 2, -supportSize * 2.2 - (this.deformed ? peak * this.scale : 0), 0);
    this.group.add(grid);
    const scaleLabel = this.scale < 0.1 ? this.scale.toExponential(2).replace('.', ',') : this.scale.toFixed(1).replace('.', ',');
    this.status.textContent = this.deformed
      ? peak > 0 ? `Deformada ×${scaleLabel} (${this.scale >= 1 ? 'ampliada' : 'reduzida'}) · linha clara: geometria inicial` : 'Sem deformação para o carregamento atual'
      : 'Geometria em proporções reais · cargas e apoios esquemáticos';
    this.container.dataset.deformed = String(this.deformed);
    this.container.dataset.span = String(m.span_m);
    this.container.dataset.width = String(m.width_m);
    this.container.dataset.height = String(m.height_m);
    this.container.dataset.supportLeft = m.support_left ?? 'pinned';
    this.container.dataset.supportRight = m.support_right ?? 'roller';
    this.render(true);
  }
}

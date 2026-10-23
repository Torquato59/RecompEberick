export type SupportType = 'pinned' | 'roller' | 'fixed' | 'free';
export type BeamInput = {
  span_m: number;
  elastic_modulus_gpa: number;
  width_m: number;
  height_m: number;
  uniform_load_kn_m: number;
  point_load_kn: number;
  point_position_m: number;
  support_left?: SupportType;
  support_right?: SupportType;
};

export type Sample = {
  x_m: number; side: string; shear_kn: number; moment_kn_m: number;
  deflection_mm: number; rotation_mrad: number;
};

export type Result = {
  method: string;
  beam_type: string;
  supports: { left: SupportType; right: SupportType };
  integration_constants: { initial_moment_kn_m: number; c_kn_m2: number; d_kn_m3: number };
  inertia_m4: number;
  flexural_rigidity_kn_m2: number;
  section: { area_m2: number; section_modulus_m3: number };
  elastic_results: {
    total_load_kn: number; max_bending_stress_mpa: number; max_shear_stress_mpa: number;
    left_rotation_mrad: number; right_rotation_mrad: number;
  };
  reactions: { left_kn: number; right_kn: number; left_moment_kn_m: number; right_moment_kn_m: number };
  extrema: { moment_kn_m: number; signed_moment_kn_m: number; positive_moment_kn_m: number; negative_moment_kn_m: number; moment_position_m: number; deflection_mm: number; signed_deflection_mm: number; deflection_position_m: number; absolute_shear_kn: number };
  equilibrium: { force_residual_kn: number; moment_residual_kn_m: number };
  samples: Sample[];
};

export type ValidationCheck = {
  quantity: string; analytical: number; reference: number; absolute_error: number;
  relative_error: number | null; tolerance: number; passed: boolean;
};
export type ValidationCase = {
  id: string; label: string; model: BeamInput; elements: number;
  checks: ValidationCheck[]; passed: boolean;
};
export type ValidationReport = {
  method: string; relative_tolerance: number; absolute_tolerance: number;
  cases: ValidationCase[]; passed_cases: number; total_cases: number;
  passed_checks: number; total_checks: number; passed: boolean;
};

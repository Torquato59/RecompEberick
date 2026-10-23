BASE = {
    "span_m": 6.0, "elastic_modulus_gpa": 30.0, "width_m": 0.2,
    "height_m": 0.5, "uniform_load_kn_m": 12.0, "point_load_kn": 0.0,
    "point_position_m": 3.0,
}

CASES = [
    ("uniform", "Carga distribuída", BASE),
    ("center", "Pontual no centro", BASE | {"uniform_load_kn_m": 0, "point_load_kn": 20}),
    ("eccentric", "Pontual excêntrica", BASE | {"uniform_load_kn_m": 0, "point_load_kn": 23, "point_position_m": 1.7}),
    ("combined", "Cargas combinadas", BASE | {"point_load_kn": 19, "point_position_m": 2}),
    ("mirrored", "Excêntrica espelhada", BASE | {"uniform_load_kn_m": 0, "point_load_kn": 23, "point_position_m": 4.3}),
    ("stiffer", "Módulo E em dobro", BASE | {"elastic_modulus_gpa": 60}),
    ("taller", "Altura em dobro", BASE | {"height_m": 1}),
    ("unloaded", "Sem carregamento", BASE | {"uniform_load_kn_m": 0}),
    ("support", "Pontual no apoio A", BASE | {"uniform_load_kn_m": 0, "point_load_kn": 15, "point_position_m": 0}),
    ("shorter", "Outro vão e seção", BASE | {"span_m": 4.5, "width_m": 0.15, "height_m": 0.4, "elastic_modulus_gpa": 25, "uniform_load_kn_m": 8, "point_load_kn": 11, "point_position_m": 1.6}),
]

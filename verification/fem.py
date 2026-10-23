"""Referência independente de Euler–Bernoulli por rigidez, sem importar backend.

Dois graus de liberdade por nó: deslocamento para baixo e sua derivada em x.
Malha inclui a posição da carga pontual. Carregamento distribuído usa forças
nodais consistentes; deslocamentos usam interpolação cúbica de Hermite.
Não usa a solução por funções de singularidade do aplicativo.
"""

import bisect
import math


def solve_banded_spd(matrix, force, bandwidth=3):
    """Cholesky para a matriz de rigidez simétrica com banda estreita."""
    size = len(force)
    lower = [[0.0] * size for _ in range(size)]
    for row in range(size):
        for col in range(max(0, row - bandwidth), row + 1):
            value = matrix[row][col] - sum(
                lower[row][k] * lower[col][k]
                for k in range(max(0, row - bandwidth, col - bandwidth), col)
            )
            lower[row][col] = math.sqrt(value) if row == col else value / lower[col][col]
    intermediate = [0.0] * size
    for row in range(size):
        intermediate[row] = (force[row] - sum(
            lower[row][col] * intermediate[col]
            for col in range(max(0, row - bandwidth), row)
        )) / lower[row][row]
    displacement = [0.0] * size
    for row in reversed(range(size)):
        displacement[row] = (intermediate[row] - sum(
            lower[col][row] * displacement[col]
            for col in range(row + 1, min(size, row + bandwidth + 1))
        )) / lower[row][row]
    return displacement


def solve(model, subdivisions=32):
    length, a = model["span_m"], model["point_position_m"]
    q, point = model["uniform_load_kn_m"], model["point_load_kn"]
    width, height = model["width_m"], model["height_m"]
    rigidity = model["elastic_modulus_gpa"] * 1e6 * width * height ** 3 / 12
    spacing = length / subdivisions
    # Substituir o nó vizinho evita elementos quase nulos quando a carga está
    # muito próxima da malha regular, sem deslocar a carga ou alterar o vão.
    nodes = sorted({0.0, length, a} | {
        spacing * i for i in range(1, subdivisions)
        if spacing * i == a or abs(spacing * i - a) >= spacing / 4
    })
    size = 2 * len(nodes)
    stiffness = [[0.0] * size for _ in range(size)]
    force = [0.0] * size
    elements = []
    for index, (start, end) in enumerate(zip(nodes, nodes[1:])):
        span = end - start
        matrix = [
            [12, 6 * span, -12, 6 * span],
            [6 * span, 4 * span ** 2, -6 * span, 2 * span ** 2],
            [-12, -6 * span, 12, -6 * span],
            [6 * span, 2 * span ** 2, -6 * span, 4 * span ** 2],
        ]
        matrix = [[value * rigidity / span ** 3 for value in row] for row in matrix]
        equivalent = [q * span / 2, q * span ** 2 / 12, q * span / 2, -q * span ** 2 / 12]
        dofs = [2 * index + k for k in range(4)]
        for local_row, row in enumerate(dofs):
            force[row] += equivalent[local_row]
            for local_col, col in enumerate(dofs):
                stiffness[row][col] += matrix[local_row][local_col]
        elements.append((start, span, dofs, matrix, equivalent))
    force[2 * nodes.index(a)] += point
    restrained = {0, size - 2}
    free = [i for i in range(size) if i not in restrained]
    reduced = [[stiffness[row][col] for col in free] for row in free]
    solution = solve_banded_spd(reduced, [force[i] for i in free])
    displacements = [0.0] * size
    for dof, value in zip(free, solution):
        displacements[dof] = value
    reactions = {
        dof: force[dof] - sum(stiffness[dof][col] * displacements[col] for col in range(size))
        for dof in restrained
    }
    maximum_moment = 0.0
    maximum_shear = 0.0
    maximum_deflection = 0.0
    interpolation = []
    for start, span, dofs, matrix, equivalent in elements:
        local = [displacements[dof] for dof in dofs]
        end_force = [sum(matrix[row][col] * local[col] for col in range(4)) - equivalent[row] for row in range(4)]
        candidates = [0.0, span]
        if q:
            stationary = -end_force[0] / q
            if 0 < stationary < span:
                candidates.append(stationary)
        for x in candidates:
            maximum_moment = max(maximum_moment, end_force[1] - end_force[0] * x - q * x * x / 2)
        maximum_shear = max(maximum_shear, abs(end_force[0]), abs(-end_force[0] - q * span))
        left, rotation_left, right, rotation_right = local
        coefficients = [
            left,
            span * rotation_left,
            -3 * left - 2 * span * rotation_left + 3 * right - span * rotation_right,
            2 * left + span * rotation_left - 2 * right + span * rotation_right,
        ]
        quadratic, linear, constant = 3 * coefficients[3], 2 * coefficients[2], coefficients[1]
        candidates = [0.0, 1.0]
        threshold = max(abs(linear), abs(constant), 1e-30) * 1e-12
        if abs(quadratic) <= threshold:
            if abs(linear) > 1e-30:
                candidates.append(-constant / linear)
        else:
            discriminant = linear ** 2 - 4 * quadratic * constant
            if discriminant >= 0:
                candidates.extend(((-linear + math.sqrt(discriminant)) / (2 * quadratic), (-linear - math.sqrt(discriminant)) / (2 * quadratic)))
        for xi in candidates:
            if 0 <= xi <= 1:
                maximum_deflection = max(maximum_deflection, sum(c * xi ** power for power, c in enumerate(coefficients)))
        interpolation.append((span, coefficients))

    def at(x):
        index = min(len(elements) - 1, max(0, bisect.bisect_right(nodes, x) - 1))
        span, coefficients = interpolation[index]
        xi = (x - nodes[index]) / span
        return sum(c * xi ** power for power, c in enumerate(coefficients)) * 1000

    modulus = width * height ** 2 / 6
    return {
        "elements": len(elements),
        "left_kn": reactions[0],
        "right_kn": reactions[size - 2],
        "moment_kn_m": maximum_moment,
        "deflection_mm": maximum_deflection * 1000,
        "absolute_shear_kn": maximum_shear,
        "left_rotation_mrad": displacements[1] * 1000,
        "right_rotation_mrad": displacements[-1] * 1000,
        "max_bending_stress_mpa": maximum_moment / modulus / 1000,
        "max_shear_stress_mpa": 1.5 * maximum_shear / (width * height) / 1000,
        "deflection_at": at,
    }

"""Gera uma conferência reproduzível entre solução analítica e elementos finitos."""

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verification.report import run_validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/validation")
    args = parser.parse_args()
    result = run_validation()
    version = json.loads((ROOT / "package.json").read_text())["version"]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "resultados.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.output / "comparacoes.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["case", "quantity", "analytical", "fem_reference", "absolute_error", "relative_error", "tolerance", "passed"])
        for case in result["cases"]:
            for check in case["checks"]:
                writer.writerow([case["id"], check["quantity"], check["analytical"], check["reference"], check["absolute_error"], check["relative_error"], check["tolerance"], check["passed"]])
    worst = max(check["relative_error"] or 0 for case in result["cases"] for check in case["checks"])
    lines = [
        f"# Conferência do cálculo elástico · versão {version}", "",
        f"Resultado: **{result['passed_cases']}/{result['total_cases']} casos e {result['passed_checks']}/{result['total_checks']} comparações dentro da tolerância**.", "",
        "O cálculo do aplicativo integra funções de singularidade e determina quatro constantes pelas condições de apoio. A referência independente monta a matriz de rigidez de elementos de Euler–Bernoulli, aplica forças nodais consistentes e resolve os graus de liberdade por Cholesky, restringindo translação/rotação conforme cada apoio. A carga pontual é um nó da malha de 32 ou 33 elementos. São conferidas vigas biapoiadas, em balanço, biengastadas e engastadas com apoio na outra extremidade. Ambos representam o mesmo modelo físico linear; a comparação não verifica concreto fissurado nem critérios normativos.", "",
        "Tolerância por grandeza: erro absoluto ≤ 1e-8 + 3e-6 × |referência|, nas unidades da grandeza. A tolerância absoluta permite avaliar valores nulos sem dividir por zero. O JSON e o CSV guardam todos os valores e erros sem o arredondamento da tabela.", "",
        f"Maior erro relativo entre referências não nulas: **{worst:.9e}** ({worst * 100:.9f}%).", "",
        "| Caso | RA (kN) | RB (kN) | MA (kN·m) | MB (kN·m) | M absoluto (kN·m) | δ absoluta analítica (mm) | δ absoluta MEF (mm) | Estado |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in result["cases"]:
        checks = {check["quantity"]: check for check in case["checks"]}
        values = [checks[name]["analytical"] for name in ["left_kn", "right_kn", "left_moment_kn_m", "right_moment_kn_m", "moment_kn_m", "deflection_mm"]]
        values.append(checks["deflection_mm"]["reference"])
        lines.append(f"| {case['label']} | " + " | ".join(f"{value:.6f}" for value in values) + f" | {'Conferido' if case['passed'] else 'Divergência'} |")
    lines.extend([
        "", "São comparadas onze grandezas: as duas reações verticais, duas reações de momento, máximo absoluto do momento e da flecha, cortante máximo absoluto, duas rotações e tensões máximas de flexão e cisalhamento. MA e MB são reações externas positivas anti-horárias; o momento interno é positivo sagente. A tensão usa o máximo absoluto, incluindo os momentos negativos nos engastes. Tensões referem-se à seção bruta homogênea; não são resistências de cálculo.", "",
        "A suíte também confere diretamente fórmulas fechadas de vigas biapoiadas, em balanço, biengastadas e engastadas-apoiadas. Verifica estabilidade, condições de contorno, cargas nas pontas livres ou apoios, equilíbrio incluindo momentos, superposição e casos gerados com semente fixa. A referência possui teste de refinamento entre nós.", "",
        "- [Resultados completos e parâmetros em JSON](resultados.json)",
        "- [Todas as comparações em CSV](comparacoes.csv)", "",
        "Reproduzir: `npm run validate`. Para atualizar este relatório versionado: `python3 scripts/validate_calculations.py --output docs/validacao`. Os testes são executados por `npm test` após o build.",
    ])
    (args.output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{result['passed_cases']}/{result['total_cases']} casos; {result['passed_checks']}/{result['total_checks']} comparações.")
    print(f"Maior erro relativo: {worst:.9e}. Relatórios: {args.output}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

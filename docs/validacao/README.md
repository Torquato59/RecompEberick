# Conferência do cálculo elástico · versão 0.2.0

Resultado: **10/10 casos e 90/90 comparações dentro da tolerância**.

O cálculo do aplicativo usa funções de singularidade. A referência independente monta a matriz de rigidez de elementos de Euler–Bernoulli, aplica forças nodais consistentes e resolve os graus de liberdade por Cholesky. A posição da carga pontual é um nó da malha de 32 ou 33 elementos. Ambos representam o mesmo modelo físico linear; esta comparação não verifica o comportamento real de concreto fissurado nem critérios normativos.

Tolerância por grandeza: erro absoluto ≤ 1e-8 + 3e-6 × |referência|, nas unidades da grandeza. A tolerância absoluta permite avaliar valores nulos sem dividir por zero. O JSON e o CSV guardam todos os valores e erros sem o arredondamento da tabela.

Maior erro relativo entre referências não nulas: **1.256323543e-07** (0.000012563%).

| Caso | RA (kN) | RB (kN) | M máx. (kN·m) | δ analítica (mm) | δ MEF (mm) | Estado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Carga distribuída | 36.000000 | 36.000000 | 54.000000 | 3.240000 | 3.240000 | Conferido |
| Pontual no centro | 10.000000 | 10.000000 | 30.000000 | 1.440000 | 1.440000 | Conferido |
| Pontual excêntrica | 16.483333 | 6.516667 | 28.021667 | 1.274328 | 1.274328 | Conferido |
| Cargas combinadas | 48.666667 | 42.333333 | 74.671296 | 4.408380 | 4.408379 | Conferido |
| Excêntrica espelhada | 6.516667 | 16.483333 | 28.021667 | 1.274328 | 1.274328 | Conferido |
| Módulo E em dobro | 36.000000 | 36.000000 | 54.000000 | 1.620000 | 1.620000 | Conferido |
| Altura em dobro | 36.000000 | 36.000000 | 54.000000 | 0.405000 | 0.405000 | Conferido |
| Sem carregamento | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | Conferido |
| Pontual no apoio A | 15.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | Conferido |
| Outro vão e seção | 25.088889 | 21.911111 | 30.006049 | 3.064043 | 3.064043 | Conferido |

São comparadas as duas reações, momento máximo, flecha máxima, cortante máximo absoluto, as duas rotações e tensões máximas de flexão e cisalhamento. Tensões referem-se à seção bruta homogênea; não são resistências de cálculo.

A suíte de testes também confere diretamente as soluções fechadas qL²/8, 5qL⁴/384EI, PL/4, PL³/48EI, rotações e tensões, além de superposição, espelhamento e casos gerados com semente fixa. Uma checagem de refinamento verifica a interpolação de deslocamentos do método de referência.

- [Resultados completos e parâmetros em JSON](resultados.json)
- [Todas as comparações em CSV](comparacoes.csv)

Reproduzir: `npm run validate`. Para atualizar este relatório versionado: `python3 scripts/validate_calculations.py --output docs/validacao`. Os testes são executados por `npm test` após o build.

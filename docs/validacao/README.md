# Conferência do cálculo elástico · versão 0.2.1

Resultado: **21/21 casos e 231/231 comparações dentro da tolerância**.

O cálculo do aplicativo integra funções de singularidade e determina quatro constantes pelas condições de apoio. A referência independente monta a matriz de rigidez de elementos de Euler–Bernoulli, aplica forças nodais consistentes e resolve os graus de liberdade por Cholesky, restringindo translação/rotação conforme cada apoio. A carga pontual é um nó da malha de 32 ou 33 elementos. São conferidas vigas biapoiadas, em balanço, biengastadas e engastadas com apoio na outra extremidade. Ambos representam o mesmo modelo físico linear; a comparação não verifica concreto fissurado nem critérios normativos.

Tolerância por grandeza: erro absoluto ≤ 1e-8 + 3e-6 × |referência|, nas unidades da grandeza. A tolerância absoluta permite avaliar valores nulos sem dividir por zero. O JSON e o CSV guardam todos os valores e erros sem o arredondamento da tabela.

Maior erro relativo entre referências não nulas: **4.581103709e-07** (0.000045811%).

| Caso | RA (kN) | RB (kN) | MA (kN·m) | MB (kN·m) | M absoluto (kN·m) | δ absoluta analítica (mm) | δ absoluta MEF (mm) | Estado |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Carga distribuída | 36.000000 | 36.000000 | 0.000000 | 0.000000 | 54.000000 | 3.240000 | 3.240000 | Conferido |
| Pontual no centro | 10.000000 | 10.000000 | 0.000000 | 0.000000 | 30.000000 | 1.440000 | 1.440000 | Conferido |
| Pontual excêntrica | 16.483333 | 6.516667 | 0.000000 | 0.000000 | 28.021667 | 1.274328 | 1.274328 | Conferido |
| Cargas combinadas | 48.666667 | 42.333333 | 0.000000 | 0.000000 | 74.671296 | 4.408380 | 4.408379 | Conferido |
| Excêntrica espelhada | 6.516667 | 16.483333 | 0.000000 | 0.000000 | 28.021667 | 1.274328 | 1.274328 | Conferido |
| Módulo E em dobro | 36.000000 | 36.000000 | 0.000000 | 0.000000 | 54.000000 | 1.620000 | 1.620000 | Conferido |
| Altura em dobro | 36.000000 | 36.000000 | 0.000000 | 0.000000 | 54.000000 | 0.405000 | 0.405000 | Conferido |
| Sem carregamento | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | Conferido |
| Pontual no apoio A | 15.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | Conferido |
| Outro vão e seção | 25.088889 | 21.911111 | 0.000000 | 0.000000 | 30.006049 | 3.064043 | 3.064043 | Conferido |
| Balanço A · distribuída | 72.000000 | 0.000000 | 216.000000 | 0.000000 | 216.000000 | 31.104000 | 31.104000 | Conferido |
| Balanço A · ponta livre | 20.000000 | 0.000000 | 120.000000 | 0.000000 | 120.000000 | 23.040000 | 23.040000 | Conferido |
| Balanço B · distribuída | 0.000000 | 72.000000 | 0.000000 | -216.000000 | 216.000000 | 31.104000 | 31.104000 | Conferido |
| Balanço B · ponta livre | 0.000000 | 20.000000 | 0.000000 | -120.000000 | 120.000000 | 23.040000 | 23.040000 | Conferido |
| Biengastada · distribuída | 36.000000 | 36.000000 | 36.000000 | -36.000000 | 36.000000 | 0.648000 | 0.648000 | Conferido |
| Biengastada · pontual | 10.000000 | 10.000000 | 15.000000 | -15.000000 | 15.000000 | 0.360000 | 0.360000 | Conferido |
| Engaste A e móvel B | 45.000000 | 27.000000 | 54.000000 | 0.000000 | 54.000000 | 1.347704 | 1.347704 | Conferido |
| Engaste A e articulado B | 61.185185 | 29.814815 | 75.111111 | 0.000000 | 75.111111 | 1.741750 | 1.741750 | Conferido |
| Móvel A e engaste B | 27.000000 | 45.000000 | 0.000000 | -54.000000 | 54.000000 | 1.347704 | 1.347704 | Conferido |
| Móvel A e articulado B | 36.000000 | 36.000000 | 0.000000 | 0.000000 | 54.000000 | 3.240000 | 3.240000 | Conferido |
| Dois articulados · flexão | 36.000000 | 36.000000 | 0.000000 | 0.000000 | 54.000000 | 3.240000 | 3.240000 | Conferido |

São comparadas onze grandezas: as duas reações verticais, duas reações de momento, máximo absoluto do momento e da flecha, cortante máximo absoluto, duas rotações e tensões máximas de flexão e cisalhamento. MA e MB são reações externas positivas anti-horárias; o momento interno é positivo sagente. A tensão usa o máximo absoluto, incluindo os momentos negativos nos engastes. Tensões referem-se à seção bruta homogênea; não são resistências de cálculo.

A suíte também confere diretamente fórmulas fechadas de vigas biapoiadas, em balanço, biengastadas e engastadas-apoiadas. Verifica estabilidade, condições de contorno, cargas nas pontas livres ou apoios, equilíbrio incluindo momentos, superposição e casos gerados com semente fixa. A referência possui teste de refinamento entre nós.

- [Resultados completos e parâmetros em JSON](resultados.json)
- [Todas as comparações em CSV](comparacoes.csv)

Reproduzir: `npm run validate`. Para atualizar este relatório versionado: `python3 scripts/validate_calculations.py --output docs/validacao`. Os testes são executados por `npm test` após o build.

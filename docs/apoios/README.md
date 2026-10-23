# Escolha dos apoios · versão 0.2.1

Na seção **Apoios**, escolha separadamente as extremidades A e B e selecione **Calcular estrutura**. A análise, os desenhos 2D/3D, os momentos de reação, os diagramas, a memória e a impressão usam essa combinação. Alterar os apoios invalida os resultados anteriores até recalcular.

| Opção | Comportamento no modelo de flexão vertical |
| --- | --- |
| Articulado | Deslocamento vertical nulo; rotação livre; sem momento de reação |
| Móvel | Deslocamento vertical nulo; rotação livre; sem momento de reação |
| Engastado | Deslocamento vertical e rotação nulos; pode reagir com momento |
| Livre | Sem reação de apoio; a ponta pode deslocar e girar |

São possíveis vigas biapoiadas, balanços com engaste em A ou B, biengastadas e engastadas com apoio articulado/móvel na outra extremidade. Ponta livre sem engaste e dois apoios móveis são bloqueados, inclusive na API. Dois articulados são aceitos apenas no escopo de flexão vertical: o programa não calcula força axial, torção ou reações horizontais. A ausência de restrição horizontal em dois móveis é tratada como instabilidade global.

## Imagens e projeto

- [Viga em balanço: modelos 2D e 3D](balanco-2d-3d.png)
- [Interface e resultados do balanço](balanco-desktop.png)
- [Viga biengastada: modelos 2D e 3D](biengastada-2d-3d.png)
- [Relatório do balanço em PDF](relatorio-balanco.pdf)
- [Projeto de balanço em JSON, formato 2](../../examples/viga-balanco.json)
- [Conferência independente completa](../validacao/README.md)

## Exemplos verificados

Todos usam comprimento de 6 m, seção de 20 × 50 cm e E = 30 GPa.

| Modelo e carga | RA (kN) | RB (kN) | MA (kN·m) | MB (kN·m) | Momento absoluto máximo (kN·m) | Flecha máxima (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Articulado/móvel · q = 12 kN/m | 36 | 36 | 0 | 0 | 54 | 3,24 |
| Engastado/livre · P = 20 kN na ponta B | 20 | 0 | 120 | 0 | 120 | 23,04 |
| Livre/engastado · P = 20 kN na ponta A | 0 | 20 | 0 | −120 | 120 | 23,04 |
| Engastado/engastado · q = 12 kN/m | 36 | 36 | 36 | −36 | 36 | 0,648 |
| Engastado/móvel · q = 12 kN/m | 45 | 27 | 54 | 0 | 54 | 1,347704 |

MA e MB são momentos **externos de reação**, positivos anti-horários. No elemento, o momento interno é positivo sagente. No balanço com engaste em A e carga na ponta B, por exemplo, MA = +120 kN·m e M interno no engaste = −120 kN·m. Na biengastada sob carga distribuída, o momento interno mínimo é −36 kN·m e o máximo positivo é +18 kN·m; a tensão usa o máximo absoluto de 36 kN·m.

## Verificação e compatibilidade

39 testes passaram: incluem todas as dez combinações estáveis, fórmulas fechadas, instabilidade, casos com cargas nas pontas, sinais dos momentos, condições de contorno e 30 combinações geradas para os diferentes apoios, além dos testes anteriores. Os 21 casos publicados totalizam 231 comparações aprovadas contra uma implementação independente de elementos finitos de Euler–Bernoulli. O teste no Chromium cobre seleção e desenho dos apoios, ambas as orientações do balanço, biengastada, engastada-apoiada, combinações instáveis, impressão e arquivos de projeto.

Novos projetos usam formato JSON **versão 2**, com os dois apoios explícitos. Os arquivos antigos de versão 1 continuam abrindo como articulado em A e móvel em B. Os programas antigos que só aceitam formato 1 devem ser atualizados para ler os novos projetos.

O escopo permanece na linha 0.2, com foco desktop e desenvolvimento móvel pausado. Trata-se de análise elástica da seção bruta; resistência, armaduras, detalhamento, fissuração e verificações normativas continuam fora desta etapa.

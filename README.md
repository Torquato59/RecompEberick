# Estrutura · Laboratório de vigas

**Escopo atual: manter a versão 0.2 com foco de uso no Windows. Desenvolvimento e testes específicos para celular estão pausados.** A interface, os cálculos e a arquitetura desta versão foram mantidos. As imagens de celular já publicadas são registros históricos; o layout adaptável existente não exige um aplicativo ou serviço móvel separado.

[Imagens e PDF do primeiro protótipo](docs/prototipo/README.md)

[Versão 0.2: modelo 3D e relatórios](docs/prototipo-3d/README.md) · [Conferência independente dos cálculos](docs/validacao/README.md)

Primeiro módulo do projeto RecompEberick: um aplicativo independente para explorar o comportamento de uma viga biapoiada. Núcleo de cálculo em Python, interface em TypeScript, SVG e Three.js. Não usa código, bibliotecas ou executáveis extraídos do instalador AltoQi. REA permanece como ferramenta separada de análise.

## Executar

Requisitos: Python 3.10 ou superior e Node.js 22 ou superior com npm. O servidor Python não precisa de pacotes externos. A compilação usa TypeScript e esbuild fixados no lockfile e inclui o Three.js no JavaScript servido localmente, sem CDN. A vista 3D requer WebGL 2; os cálculos e o desenho 2D continuam funcionando quando o navegador não oferece esse recurso.

```sh
cd /workspace/RecompEberick
npm ci --cache /workspace/.cache/npm
npm run build
npm test
npm start
```

O servidor usa a porta 8000 e escuta apenas na interface local por padrão. Para executar em outro endereço ou porta, use `python3 -m backend.server --host ENDERECO --port PORTA`. É um servidor de desenvolvimento, sem autenticação ou infraestrutura de publicação. A interface compilada é servida pelo mesmo processo que oferece a API. Após alterar TypeScript, HTML ou CSS, execute `npm run build` e recarregue a página. Após alterar Python, reinicie o servidor.

`npm run check` verifica os tipos. `npm test` executa os casos analíticos, a validação de entradas e as requisições HTTP reais, incluindo os arquivos compilados; execute o build antes. Os testes HTTP iniciam e encerram um servidor próprio em uma porta livre.

Teste opcional de interface: com Playwright (`requirements-browser.txt`), Chromium e o servidor ativo, execute `npm run test:browser`. O teste cobre cálculo, edição, importação/exportação, resposta atrasada, impressão, layout desktop, rotação/zoom/deformada 3D, atualização das dimensões, casos de referência e fallback sem WebGL; grava imagens e um PDF de exemplo na pasta ignorada `artifacts/`. O Chromium de teste usa SwiftShader para renderizar WebGL em ambiente sem GPU. Se não houver Chromium do sistema, instale o navegador com `python3 -m playwright install chromium`.

## Usar o protótipo

1. Informe o vão, a seção retangular e o módulo de elasticidade.
2. Defina a carga distribuída em todo o vão e/ou uma carga pontual. A posição é medida a partir de A. Use zero para remover uma carga.
3. Selecione **Calcular estrutura**. Os diagramas mostram valores amostrados ao passar o cursor. As máximas de momento e flecha são obtidas independentemente da malha de desenho.
4. **Salvar projeto** exporta os dados em JSON; **Abrir projeto** valida e recalcula o arquivo. O exemplo está em `examples/viga-distribuida.json`.
5. **Imprimir relatório** usa a impressão do navegador, com layout próprio para papel/PDF. Mudanças nos dados invalidam os resultados anteriores até um novo cálculo.
6. Na vista 3D, arraste para girar e use a roda ou os botões para aproximar. Com foco no modelo, as setas giram, +/− alteram o zoom e Home restaura a câmera. **Exibir deformada** usa a flecha já calculada; o fator visual aparece abaixo. A seção e o vão permanecem nas proporções reais na vista inicial; cargas e apoios são esquemáticos. Trata-se da representação espacial do modelo de viga 1D, sem cálculo de sólidos 3D.
7. Em **Tensões e rotações elásticas**, confira área, módulo resistente, EI, tensões da seção bruta e rotações. A memória mostra fórmulas e valores. Não há comparação de tensão com resistência, verificação de fissuração ou armaduras.
8. Em **Casos de referência**, carregue um dos dez cenários ou baixe a conferência completa. O arquivo de projeto permanece compatível com a versão 1: nenhum novo parâmetro de entrada foi introduzido.

## Conferência independente

`npm run validate` executa a comparação e grava JSON, CSV e relatório em `artifacts/validation/`. Para atualizar os resultados publicados: `python3 scripts/validate_calculations.py --output docs/validacao`.

A referência em `verification/fem.py` não importa o núcleo analítico. Monta elementos de Euler–Bernoulli, dois graus de liberdade por nó, carregamento distribuído consistente e carga pontual aplicada exatamente em um nó; resolve a rigidez por Cholesky e interpola deslocamentos por Hermite. A malha regular é ajustada perto da carga para evitar elementos quase nulos. São 32 ou 33 elementos nos dez casos publicados.

São comparadas nove grandezas por caso: RA, RB, momento, flecha, cortante, rotações em A e B e tensões de flexão e cisalhamento. Critério por grandeza: erro absoluto ≤ `1e-8 + 3e-6 × |referência|`, nas unidades da saída. Há 26 testes, incluindo soluções fechadas, refinamento da referência, simetria, superposição, unidades e 24 casos gerados com semente fixa para comparar reações, momentos e deslocamentos ao longo do vão. A concordância entre métodos verifica a implementação deste modelo linear, não as hipóteses físicas ou o dimensionamento normativo.

## Modelo e unidades

- Euler–Bernoulli, seção retangular constante, material homogêneo, EI constante e pequenos deslocamentos.
- A articulado e B móvel. Carga uniformemente distribuída em todo o vão e uma carga pontual, ambas positivas para baixo.
- Não inclui automaticamente o peso próprio: acrescente sua parcela à carga distribuída quando necessário.
- Interface: vão/posição em m, seção em cm, E em GPa, cargas em kN e kN/m. API/arquivo: seção em m; saídas em kN, kN·m e mm.
- Momento positivo sagente e flecha positiva para baixo. Cortante obtido por `V(x) = RA − qx − P·H(x−a)`; na carga pontual são preservados os dois lados do salto. Valores nos apoios representam o limite interno do vão.
- Área em m² e módulo resistente em m³ na API; interface também mostra cm² e cm³. Tensões em MPa e rotações em mrad, sendo rotação a derivada da flecha positiva para baixo.

Com `L` em m, `b` e `h` em m e `E` convertido de GPa para kN/m²:

```text
I = b h³ / 12                 EI = (E_GPa × 10⁶) I
RA = qL/2 + P(L−a)/L         RB = qL/2 + Pa/L
M(x) = RA x − qx²/2 − P〈x−a〉
δ(x) = [C x − RA x³/6 + qx⁴/24 + P〈x−a〉³/6] / EI
C = [RA L³/6 − qL⁴/24 − P(L−a)³/6] / L
θ(x) = [C − RA x²/2 + qx³/6 + P〈x−a〉²/2] / EI
A = bh                       W = I/(h/2)
σmáx (MPa) = Mmáx/W/1000      τmáx (MPa) = 1,5|Vmáx|/A/1000
```

`〈z〉 = max(z, 0)`. A constante C impõe deslocamento nulo em B; em A a condição é satisfeita diretamente. Os extremos de momento são avaliados nos apoios, na carga pontual e nas raízes válidas de V. A máxima flecha é encontrada na raiz de δ′ por bisseção, aproveitando a monotonicidade para as cargas não negativas admitidas.

### Caso de referência

Vão de 6 m, seção 20 × 50 cm, E = 30 GPa e q = 12 kN/m, sem carga pontual:

| Resultado | Valor analítico |
| --- | --- |
| RA e RB | 36 kN cada |
| Momento máximo | 54 kN·m em x = 3 m |
| Flecha máxima | 3,24 mm em x = 3 m |
| Tensão máxima de flexão | 6,48 MPa |
| Tensão máxima de cisalhamento | 0,54 MPa |
| Rotações em A e B | +1,728 e −1,728 mrad |

Os testes também cobrem carga pontual central (`PL³/48EI`), excêntrica, superposição, cargas nos apoios, equilíbrio, salto de cortante e variação de rigidez.

## API

`GET /api/health` retorna o estado do processo. `POST /api/calculate`, com `Content-Type: application/json`, recebe os sete campos de `model` do arquivo de exemplo e retorna reações, inércia, rigidez, máximas, resíduos de equilíbrio e amostras para os diagramas. Entradas inválidas retornam HTTP 422 com `error`. JSON inválido retorna 400; tipo de conteúdo incorreto, 415; corpo ausente ou superior a 16 KiB, 413.

A resposta também inclui `section` (área e módulo resistente), `elastic_results` (carga total, tensões e rotações nos apoios) e `rotation_mrad` nas amostras. `GET /api/validation` retorna a comparação dos dez cenários; o resultado é calculado uma vez por processo e guardado em cache. Para recalcular após alterar o código, reinicie o servidor.

## Limites e próximos módulos

Esta versão faz análise elástica, sem dimensionamento normativo, armaduras, fissuração, fluência, flambagem, combinações de ações ou verificações de segurança. Os limites numéricos de entrada evitam dados inválidos; não comprovam a validade física das hipóteses. A flecha não considera cisalhamento. Não há recuperação de código-fonte nem compatibilidade com arquivos proprietários do Eberick.

Próximos incrementos: múltiplas cargas, pórticos planos por rigidez, combinações de ações e, em etapa separada, dimensionamento com critérios normativos explícitos e validação técnica.

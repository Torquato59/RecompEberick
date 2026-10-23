# Estrutura · Laboratório de vigas

[Imagens e PDF do primeiro protótipo](docs/prototipo/README.md)

Primeiro módulo do projeto RecompEberick: um aplicativo independente para explorar o comportamento de uma viga biapoiada. Núcleo de cálculo em Python, interface em TypeScript e SVG. Não usa código, bibliotecas ou executáveis extraídos do instalador AltoQi. REA permanece como ferramenta separada de análise.

## Executar

Requisitos: Python 3.10 ou superior e Node.js 22 ou superior com npm. O servidor Python não precisa de pacotes externos. A compilação usa a versão de TypeScript fixada no lockfile.

```sh
cd /workspace/RecompEberick
npm ci --cache /workspace/.cache/npm
npm run build
npm test
npm start
```

O servidor usa a porta 8000 e escuta apenas na interface local por padrão. Para executar em outro endereço ou porta, use `python3 -m backend.server --host ENDERECO --port PORTA`. É um servidor de desenvolvimento, sem autenticação ou infraestrutura de publicação. A interface compilada é servida pelo mesmo processo que oferece a API. Após alterar TypeScript, HTML ou CSS, execute `npm run build` e recarregue a página. Após alterar Python, reinicie o servidor.

`npm run check` verifica os tipos. `npm test` executa os casos analíticos, a validação de entradas e as requisições HTTP reais, incluindo os arquivos compilados; execute o build antes. Os testes HTTP iniciam e encerram um servidor próprio em uma porta livre.

Teste opcional de interface: com Playwright (`requirements-browser.txt`), Chromium e o servidor ativo, execute `npm run test:browser`. O teste cobre cálculo, edição, importação/exportação, resposta atrasada, impressão e tela móvel; grava imagens e um PDF de exemplo na pasta ignorada `artifacts/`. Se não houver Chromium do sistema, instale o navegador com `python3 -m playwright install chromium`.

## Usar o protótipo

1. Informe o vão, a seção retangular e o módulo de elasticidade.
2. Defina a carga distribuída em todo o vão e/ou uma carga pontual. A posição é medida a partir de A. Use zero para remover uma carga.
3. Selecione **Calcular estrutura**. Os diagramas mostram valores amostrados ao passar o cursor. As máximas de momento e flecha são obtidas independentemente da malha de desenho.
4. **Salvar projeto** exporta os dados em JSON; **Abrir projeto** valida e recalcula o arquivo. O exemplo está em `examples/viga-distribuida.json`.
5. **Imprimir relatório** usa a impressão do navegador, com layout próprio para papel/PDF. Mudanças nos dados invalidam os resultados anteriores até um novo cálculo.

## Modelo e unidades

- Euler–Bernoulli, seção retangular constante, material homogêneo, EI constante e pequenos deslocamentos.
- A articulado e B móvel. Carga uniformemente distribuída em todo o vão e uma carga pontual, ambas positivas para baixo.
- Não inclui automaticamente o peso próprio: acrescente sua parcela à carga distribuída quando necessário.
- Interface: vão/posição em m, seção em cm, E em GPa, cargas em kN e kN/m. API/arquivo: seção em m; saídas em kN, kN·m e mm.
- Momento positivo sagente e flecha positiva para baixo. Cortante obtido por `V(x) = RA − qx − P·H(x−a)`; na carga pontual são preservados os dois lados do salto. Valores nos apoios representam o limite interno do vão.

Com `L` em m, `b` e `h` em m e `E` convertido de GPa para kN/m²:

```text
I = b h³ / 12                 EI = (E_GPa × 10⁶) I
RA = qL/2 + P(L−a)/L         RB = qL/2 + Pa/L
M(x) = RA x − qx²/2 − P〈x−a〉
δ(x) = [C x − RA x³/6 + qx⁴/24 + P〈x−a〉³/6] / EI
C = [RA L³/6 − qL⁴/24 − P(L−a)³/6] / L
```

`〈z〉 = max(z, 0)`. A constante C impõe deslocamento nulo em B; em A a condição é satisfeita diretamente. Os extremos de momento são avaliados nos apoios, na carga pontual e nas raízes válidas de V. A máxima flecha é encontrada na raiz de δ′ por bisseção, aproveitando a monotonicidade para as cargas não negativas admitidas.

### Caso de referência

Vão de 6 m, seção 20 × 50 cm, E = 30 GPa e q = 12 kN/m, sem carga pontual:

| Resultado | Valor analítico |
| --- | --- |
| RA e RB | 36 kN cada |
| Momento máximo | 54 kN·m em x = 3 m |
| Flecha máxima | 3,24 mm em x = 3 m |

Os testes também cobrem carga pontual central (`PL³/48EI`), excêntrica, superposição, cargas nos apoios, equilíbrio, salto de cortante e variação de rigidez.

## API

`GET /api/health` retorna o estado do processo. `POST /api/calculate`, com `Content-Type: application/json`, recebe os sete campos de `model` do arquivo de exemplo e retorna reações, inércia, rigidez, máximas, resíduos de equilíbrio e amostras para os diagramas. Entradas inválidas retornam HTTP 422 com `error`. JSON inválido retorna 400; tipo de conteúdo incorreto, 415; corpo ausente ou superior a 16 KiB, 413.

## Limites e próximos módulos

Esta versão faz análise elástica, sem dimensionamento normativo, armaduras, fissuração, fluência, flambagem, combinações de ações ou verificações de segurança. Os limites numéricos de entrada evitam dados inválidos; não comprovam a validade física das hipóteses. A flecha não considera cisalhamento. Não há recuperação de código-fonte nem compatibilidade com arquivos proprietários do Eberick.

Próximos incrementos: múltiplas cargas, pórticos planos por rigidez, combinações de ações e, em etapa separada, dimensionamento com critérios normativos explícitos e validação técnica.

# Versão 0.2 · visualização 3D e conferência elástica

A vista espacial foi acrescentada ao lado do esquema 2D existente. É possível girar, aproximar, restaurar a câmera e exibir a deformada com fator visual informado. O cálculo continua sendo de uma viga de Euler–Bernoulli 1D; o volume não representa uma análise por elementos sólidos.

- [Modelos 2D e 3D lado a lado](modelos-2d-3d.png)
- [Deformada com ampliação indicada](modelos-deformada.png)
- [Interface completa para computador](prototipo-3d-desktop.png)
- [Interface para celular](prototipo-3d-mobile.png)
- [Relatório de exemplo em PDF](relatorio-3d-exemplo.pdf)
- [Dez casos com comparação independente por elementos finitos](../validacao/README.md)
- [Comparações completas em CSV](../validacao/comparacoes.csv)
- [Parâmetros e resultados sem arredondamento em JSON](../validacao/resultados.json)

Os novos resultados usam os mesmos sete parâmetros de entrada: área e módulo resistente da seção, rigidez EI, tensões elásticas de flexão/cisalhamento, carga total e rotações nos apoios. A memória de cálculo fica disponível na interface. A classe de resistência, armaduras e detalhamentos foram deixados para etapas posteriores.

## Evidência desta versão

- Instalação pelo lockfile, verificação de tipos e build concluídos.
- 26 testes de cálculo, unidades, condições nos apoios e API aprovados. A suíte inclui 24 combinações geradas com semente fixa, soluções analíticas conhecidas e refinamento da referência.
- 10 casos e 90 comparações aprovadas entre o núcleo analítico e uma implementação independente de rigidez de vigas.
- Testes reais no Chromium: renderização, mudanças de imagem após rotação e zoom, deformada, atualização de dimensões, casos de referência, projetos JSON, resposta atrasada, impressão e tela de 390 px sem transbordamento horizontal da página. A tabela possui rolagem própria.
- Cálculos e esquema 2D conferidos também com WebGL indisponível.

As imagens e o PDF representam o exemplo de vão 6 m, seção 20 × 50 cm, E = 30 GPa e q = 12 kN/m. A vista deformada é apenas ilustrativa e indica seu fator de ampliação. As tensões usam seção bruta homogênea, sem resistência de cálculo, fissuração ou dimensionamento normativo.

Para executar e reproduzir os testes, consulte o [README principal](../../README.md). Os [arquivos do primeiro protótipo](../prototipo/README.md) permanecem disponíveis.

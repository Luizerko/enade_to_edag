# Overview

Nesta seção é apresentado o processo de mineração de dados, criação do banco de dados da plataforma, geração automática de novas questões, desenvolvimento do dashboard interativo para análise histórica do ENADE, e também a descrição técnica do projeto para replicabilidade em outras áreas do exame. A ideia é facilitar que professores e instituições criem questões no estilo ENADE, e também oferecer uma ferramenta útil para alunos estudarem e se prepararem para as provas.

## Mineração de Dados

O primeiro passo do projeto foi construir um banco de dados contendo todas as informações essenciais para gerar questões e, futuramente, realizar análises históricas das provas. Para isso, foi desenvolvido o script `py_scripts/enade_content_mining.py`.

### Mineração dos Editais

O `Chromium` foi utilizado para simular interações automáticas nas páginas dos editais e provas do ENADE. O script acessa automaticamente cada ano da prova e navega até as páginas ou PDFs específicas dos editais. Apesar das inconsistências em nomes de cursos (como “engenharia DE computação” e “engenharia DA computação”), foi possível criar padrões eficazes com parsing HTML usando `BeautifulSoup` ou diretamente pelo `Chromium`.

O principal desafio dessa etapa foi lidar com as variações de formato e estrutura dos editais ao longo dos anos. Em 2023, por exemplo, o edital estava disponível em HTML, enquanto anteriormente eram digitalizações PDF do Diário Oficial. Foi preciso adaptar padrões específicos para diferentes intervalos de tempo (pré-2017, entre 2017 e 2020, etc.).

Após identificar esses padrões, a extração foi feita utilizando `BeautifulSoup` e `Chromium` para HTML, e `fitz` (wrapper de `PyMuPDF`) para PDFs. Os resultados foram armazenados inicialmente em um dicionário, posteriormente convertido em CSV. Embora o exemplo apresentado seja para Engenharia da Computação, o método pode ser facilmente adaptado para outros cursos com mínimas modificações.

### Mineração das Provas

Essa fase foi mais complexa devido às dificuldades técnicas enfrentadas na extração de questões. A coleta dos PDFs das provas foi similar à anterior, usando `Chromium` para automação. O problema real surgiu na extração precisa das questões contidas nos PDFs.

Inicialmente, tentou-se usar o Opitcal Character Recognition (OCR) padrão (`pytesseract`), que apresentou dificuldades significativas devido à presença de caracteres especiais gregos (comuns em questões de exatas), imagens, tabelas e diagramas. Essa abordagem resultou em erros frequentes e perda de conteúdo.

A solução encontrada foi o uso de um modelo OCR mais avançado, o [LayoutLMv3 Large](https://huggingface.co/microsoft/layoutlmv3-large). Esse modelo reconhece o layout da página, permitindo identificar cada questão com precisão por meio de bounding boxes. Essa solução resolveu os problemas anteriores e forneceu resultados consistentes para uso nas etapas seguintes.

## Geração de Questões

Para gerar novas questões automaticamente, foi utilizada uma LLM open-source, acessada através da API gratuita oferecida pelo [Groq](https://groq.com/) devido à indisponibilidade inicial de uma GPU dedicada. Atualmente, o limite é de aproximadamente 15 a 20 questões geradas por minuto, adequado para a fase atual do projeto considerando o número de pessoas gerando questões e o tempo que natural que se espera para leitura e avaliação da qualidade de uma questão.

Após diversos testes com diferentes modelos, o que melhor atendeu às necessidades do projeto foi o [Llama-4-Maverick-17B-128E](https://huggingface.co/meta-llama/Llama-4-Maverick-17B-128E-Original), com uma temperatura de 0.8. Essa configuração mostrou-se ideal para gerar questões criativas, porém consistentes com o formato e instruções dadas.

O sistema oferece flexibilidade na criação das questões, permitindo escolher formatos (dentro das possibilidades em `data/edag_question_formats/`), tópicos específicos, prompts adicionais do usuário, anexação de imagens (interpretadas pelo modelo para composição das questões) e uso de questões anteriores do ENADE como referência para criação de novas versões.

Atualmente, esse modelo está sendo utilizado para criar um banco experimental de questões. Se o desempenho continuar positivo, futuros passos incluirão a escalabilidade e expansão do projeto.

## Análise Histórica do ENADE

Nesta etapa do projeto, desenvolvemos um modal no aplicativo que direciona o usuário para dois gráficos interativos utilizando a biblioteca `Plotly`. O primeiro gráfico apresenta uma visualização geral do perfil das provas ao longo dos anos por meio de um gráfico de barras empilhadas. Nele, cada cor representa um tópico distinto (baseado nos tópicos selecionados do SENAI CIMATEC) e as barras indicam, em termos percentuais, a importância relativa de cada tópico em cada edição da prova. A visualização conta com interações via hover: ao passar o mouse sobre uma das seções da barra, o usuário pode ver qual é o tópico e o percentual correspondente àquele ano. Isso facilita a análise comparativa da estrutura temática das provas ao longo do tempo, permitindo identificar mudanças na ênfase dos conteúdos abordados.

Além disso, o gráfico oferece uma funcionalidade adicional de filtragem por tópico. Ao clicar em um tópico específico na legenda, o gráfico se transforma, deixando de ser empilhado e exibindo apenas barras de uma cor (uma por ano), representando exclusivamente o percentual que aquele tópico ocupou em cada edição da prova. Essa interatividade permite uma análise mais seletiva e aprofundada da evolução de um único tópico ao longo dos anos. Por exemplo, ao clicar no tópico “Inteligência Artificial”, é possível observar o crescimento das barras com o passar do tempo, o que indica o aumento da relevância desse tema nas provas analisadas.

O segundo gráfico oferece uma análise mais detalhada de cada prova individualmente. Acima dele, há um slider interativo que permite ao usuário selecionar o ano da prova que deseja examinar. Uma vez escolhido o ano, o gráfico exibe barras lado a lado (não empilhadas), no qual cada barra representa o número absoluto de questões associadas a cada tópico naquela edição da prova. Essa visualização, ao focar em um único ano por vez, permite observar a distribuição temática interna de cada prova com mais precisão. Ao navegar pelos anos com o slider, é possível comparar a evolução do perfil das provas a partir da contagem direta de questões por tópico.

É importante observar que, embora todas as provas do ENADE (nos anos analisados para Engenharia de Computação) contenham 40 questões, o somatório de questões por tópico apresentado no gráfico pode ultrapassar esse número. Isso ocorre porque é comum que uma mesma questão aborde mais de um tópico, sendo assim contabilizada para cada um deles.

Por fim, para visualizar esses gráficos e suas interatividades, consulte a [documentação inicial](https://github.com/Luizerko/enade_to_edag/blob/main/README.md) e veja, até o final, o GIF demonstrando a navegação pelo aplicativo.
# Análise e Geração de Questões para o EDAG com base no ENADE

Este projeto tem como objetivo minerar e analisar o conteúdo dos editais e das provas do ENADE (Exame Nacional de Desempenho dos Estudantes), com foco inicial no curso de Engenharia de Computação.

A partir desses dados, queremos:

- Construir um dashboard interativo com visualizações que nos permitam entender como o conteúdo do exame evoluiu ao longo do tempo.
- Desenvolver uma pipeline automatizada com o uso de LLMs para gerar novas questões no estilo do ENADE, que possam ser utilizadas no Exame de Desempenho Acadêmico Geral (EDAG) do SENAI CIMATEC.

## Etapas do Projeto

1. **Mineração de Dados**
   - Raspagem dos editais do ENADE (portarias oficiais) para extração do conteúdo teórico da prova.
   - Raspagem das provas aplicadas do ENADE por ano para extração e categorização automática das questões com base no conteúdo programático.

3. **Dashboard Interativo**
   - Visualizações da evolução dos conteúdos e questões ao longo dos anos.
   - Comparações por áreas temáticas e complexidade das perguntas.

4. **Geração de Questões com IA**
   - Uso de LLMs para sugerir novas questões estilo ENADE (com a formatação do EDAG).
   - Foco no conteúdo mais recente e relevante.

## Status Atual

Raspagem e extração dos conteúdos teóricos dos editais concluída.  
Em andamento: extração e classificação das questões das provas.  
Em breve: construção do dashboard interativo.  
Fase futura: geração automática de novas questões com LLMs.

---

Projeto de pesquisa acadêmica vinculado ao SENAI CIMATEC, com foco em avaliação educacional automatizada e análise de currículos desenvolvido por **Luis Vitor Zerkowski**.
# Análise e Geração de Questões para o EDAG com base no ENADE

Este projeto tem como objetivo minerar e analisar o conteúdo dos editais e das provas do ENADE (Exame Nacional de Desempenho dos Estudantes), com foco inicial no curso de Engenharia de Computação, para geração de questões do EDAG (Exame de Desempenho Acadêmico Geral do Senai CIMATEC).

A partir desses dados, queremos:

- Construir um dashboard interativo com visualizações que nos permitam entender como o conteúdo do exame evoluiu ao longo do tempo.
- Desenvolver uma pipeline automatizada com o uso de LLMs para gerar novas questões baseadas no conteúdo do ENADE, mas no formato do EDAG.

## Etapas do Projeto

1. **Mineração de Dados**
   - Raspagem dos editais do ENADE (portarias oficiais) para extração do conteúdo teórico da prova.
   - Raspagem das provas aplicadas do ENADE por ano para extração e categorização automática das questões com base no conteúdo programático.

3. **Dashboard Interativo**
   - Visualizações da evolução dos conteúdos e questões ao longo dos anos.
   - Comparações quantitativas por áreas temáticas.

4. **Geração de Questões com IA**
   - Uso de LLMs para sugerir novas questões baseadas no ENADE e com a formatação do EDAG.

## Status Atual

- Raspagem e extração dos conteúdos teóricos dos editais **concluída**.
- Raspagem de questões das provas **em andamento**.
- Desenvolvimento do dashboard interativo para conteúdo **no futuro**.
- Classificação das questões das provas nas áreas temáticas **no futuro**.
- Geração automática de novas questões com LLMs **em andamento**.

---

Projeto desenvolvido por **Luis Vitor Zerkowski**.
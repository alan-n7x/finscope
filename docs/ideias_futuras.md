# 💡 Ideias para o Futuro (Finscope)

Este documento serve como um repositório central para rastrear ideias, melhorias contínuas e potenciais issues para o projeto Finscope. À medida que o sistema cresce, você pode usar este arquivo ou migrá-lo para o GitHub Issues/Trello.

## 🔄 Sincronização e Automação
- **Integração Automática (Open Banking/APIs):** Atualmente, os extratos são processados via PDF ou OFX. No futuro, plugar diretamente nas APIs dos bancos (como Pluggy) de forma automática eliminaria o trabalho manual de envio de PDFs e reconciliação.
- **Detecção de Duplicatas:** Melhorar o algoritmo do `import_engine.py` para identificar transações que já foram lançadas manualmente com nomes parecidos e sugerir um *merge*.

## 📊 Dashboard e UI
- **Gráficos de Tendência (Burn Rate):** Adicionar um gráfico que mostre como o seu saldo cai ao longo do mês para ajudar a prever se o dinheiro vai durar até o próximo salário.
- **Visualização de Contas Fantasmas:** Criar um alerta no dashboard se alguma conta "não identificada" começar a acumular saldos ou receber transações perdidas.

## 🗄 Banco de Dados
- **Limpeza de Histórico:** Implementar uma rotina para arquivar transações muito antigas (mais de 2 anos), focando o dashboard apenas nos *Snapshots* para garantir que consultas SQL sejam super rápidas.

## 📥 Importação
- **Parser do extrato em PDF do Mercado Livre/Pay** (adiado): hoje a conta só se mantém correta via registro manual de saldo (issue #9). Formato do arquivo mapeado para quando for implementado:
  - Cabeçalho: `EXTRATO DE CONTA`, `Periodo: De DD-MM-YYYY al DD-MM-YYYY`, `Entradas: R$ ...`, `Saidas: R$ -...`, `Saldo inicial: R$ ... Saldo final: R$ ...` (o *saldo final* é o melhor snapshot) e `Data de geração: DD-MM-YYYY`.
  - Tabela: `Data Descrição ID da operação Valor Saldo`, com uma linha por movimentação no formato `DD-MM-YYYY <descrição> <id> R$ <valor> R$ <saldo>` — a coluna `Saldo` permite snapshots diários sem depender do cabeçalho.
  - **Armadilha:** a descrição quebra em múltiplas linhas (ex.: `Pix recebido ALAN DOS` / `SANTOS OLIVEIRA`); o parser precisa unir a continuação com a linha seguinte.
  - Movimentações típicas: `Rendimentos` (crédito mínimo), `Pix recebido <próprio>` / `Pix enviado <próprio>`, `Saque TECBAN` + `Custo de saque TECBAN` (saque da carteira para a conta corrente).
  - Reconciliação: o "Pix recebido" de 14-10 (R\$ 100,00) e o de 19-10 (R\$ 12,73) já existem como pernas no Itaú/Inter — a conciliação por conta evita duplicar.
- **Cartões de crédito:** os extratos de fatura (Santander, Visa) ainda não são importados; o saldo do cartão é o da fatura, não o saldo bancário.

## 🧾 Qualidade de Dados e Código (descobertas dos PRs #27 e #28)
- **Direção explícita de transferência:** o dashboard infere o sinal de `TRANSFER` por sniffing de "recebido" na descrição (`finance_repository.py`). Migrar para campo de direção/montante explícito e converter os lançamentos existentes.
- **Backfill de `external_id` legados:** linhas antigas (`extrato:...`, uuids aleatórios) não são reconhecidas pelos ids estáveis novos; mapear uma vez para idempotência total do histórico.
- **TSDoc no frontend:** aplicar nos hooks/componentes o mesmo rigor das docstrings Google do backend.
- **Teste `test_cash_balance` instável:** `test_api_realized_matches_dashboard_and_projection` falha no `main` (pré-existente, sem relação com import); investigar a divergência realizado×projeção.

---
> [!TIP]
> **Fluxo de Trabalho Git:** Continue usando *commits* atômicos (como o que acabamos de fazer para corrigir a lógica de transferências) e branchs separadas quando for desenvolver novas *features* do zero!

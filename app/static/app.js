document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const kpiTotalBalance = document.getElementById("kpi-total-balance");
  const kpiIncome = document.getElementById("kpi-income");
  const kpiExpense = document.getElementById("kpi-expense");
  const kpiFree = document.getElementById("kpi-free");
  const kpiIncomeSub = document.getElementById("kpi-income-sub");
  const kpiExpenseSub = document.getElementById("kpi-expense-sub");

  const accountsGrid = document.getElementById("accounts-grid");
  const transactionsBody = document.getElementById("transactions-body");
  const debtsList = document.getElementById("debts-list");

  // Filters
  const inputSearch = document.getElementById("input-search");
  const selectMonth = document.getElementById("select-month");
  const selectCategory = document.getElementById("select-category");
  const selectStatus = document.getElementById("select-status");

  // Modal & Form
  const btnOpenModal = document.getElementById("btn-open-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnCancelForm = document.getElementById("btn-cancel-form");
  const modalTransaction = document.getElementById("modal-transaction");
  const formTransaction = document.getElementById("form-transaction");

  const formDate = document.getElementById("form-date");
  const formType = document.getElementById("form-type");
  const formCategory = document.getElementById("form-category");
  const formDesc = document.getElementById("form-desc");
  const formAmount = document.getElementById("form-amount");
  const formAccount = document.getElementById("form-account");
  const formPayment = document.getElementById("form-payment");
  const formPaid = document.getElementById("form-paid");
  const formEssential = document.getElementById("form-essential");
  const formObs = document.getElementById("form-obs");

  const toast = document.getElementById("toast");

  // Formatters
  const formatCurrency = (val) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(val || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return dateStr;
  };

  // State
  let currentMonth = "";

  // 1. Fetch Options (Categories, Accounts, Months)
  async function loadOptions() {
    try {
      const res = await fetch("/api/options");
      if (!res.ok) return;
      const data = await res.json();

      // Populate Months Filter
      selectMonth.innerHTML = '<option value="">Todos os Meses</option>';
      data.months.forEach((m) => {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m;
        if (m === "2026-08") opt.selected = true;
        selectMonth.appendChild(opt);
      });
      if (selectMonth.value) currentMonth = selectMonth.value;

      // Populate Categories
      selectCategory.innerHTML = '<option value="">Todas Categorias</option>';
      formCategory.innerHTML = "";
      data.categories.forEach((cat) => {
        const optFilter = document.createElement("option");
        optFilter.value = cat;
        optFilter.textContent = cat;
        selectCategory.appendChild(optFilter);

        const optForm = document.createElement("option");
        optForm.value = cat;
        optForm.textContent = cat;
        formCategory.appendChild(optForm);
      });

      // Populate Accounts
      formAccount.innerHTML = "";
      data.accounts.forEach((acc) => {
        const opt = document.createElement("option");
        opt.value = acc;
        opt.textContent = acc;
        formAccount.appendChild(opt);
      });

      // Populate Payment Methods
      formPayment.innerHTML = "";
      data.payment_methods.forEach((pm) => {
        const opt = document.createElement("option");
        opt.value = pm;
        opt.textContent = pm;
        formPayment.appendChild(opt);
      });
    } catch (err) {
      console.error("Erro ao carregar opções:", err);
    }
  }

  // 2. Fetch Dashboard Summary
  async function loadDashboard() {
    try {
      const monthParam = selectMonth.value ? `?month=${selectMonth.value}` : "";
      const res = await fetch(`/api/dashboard${monthParam}`);
      if (!res.ok) return;
      const data = await res.json();

      kpiTotalBalance.textContent = formatCurrency(data.total_balance);
      kpiIncome.textContent = `+${formatCurrency(data.income_month)}`;
      kpiExpense.textContent = `-${formatCurrency(data.expense_month)}`;
      kpiFree.textContent = formatCurrency(data.free_after_reserve);

      const monthName = data.month || "Mês Selecionado";
      kpiIncomeSub.textContent = `Entradas em ${monthName}`;
      kpiExpenseSub.textContent = `Saídas em ${monthName}`;

      // Accounts Grid
      accountsGrid.innerHTML = "";
      data.accounts.forEach((acc) => {
        const card = document.createElement("div");
        card.className = "account-card";
        card.innerHTML = `
          <span class="account-name">${acc.name} (${acc.type})</span>
          <span class="account-balance">${formatCurrency(acc.balance)}</span>
        `;
        accountsGrid.appendChild(card);
      });
    } catch (err) {
      console.error("Erro ao carregar dashboard:", err);
    }
  }

  // 3. Fetch Transactions
  async function loadTransactions() {
    try {
      const params = new URLSearchParams();
      if (selectMonth.value) params.append("month", selectMonth.value);
      if (selectCategory.value) params.append("category", selectCategory.value);
      if (selectStatus.value) params.append("status", selectStatus.value);
      if (inputSearch.value.trim()) params.append("search", inputSearch.value.trim());

      const res = await fetch(`/api/transactions?${params.toString()}`);
      if (!res.ok) return;
      const transactions = await res.json();

      transactionsBody.innerHTML = "";
      if (transactions.length === 0) {
        transactionsBody.innerHTML = `
          <tr>
            <td colspan="8" class="loading-cell">Nenhum lançamento encontrado.</td>
          </tr>
        `;
        return;
      }

      transactions.forEach((tx) => {
        const tr = document.createElement("tr");

        let typeClass = "badge-type-despesa";
        let amountClass = "amount-expense";
        let prefix = "-";

        if (tx.type === "Receita") {
          typeClass = "badge-type-receita";
          amountClass = "amount-income";
          prefix = "+";
        } else if (tx.type === "Transferência") {
          typeClass = "badge-type-transferência";
          amountClass = "amount-transfer";
          prefix = "";
        }

        const isPaid = tx.paid.toLowerCase() === "sim";
        const statusBadge = isPaid
          ? '<span class="badge badge-status-paid">Pago</span>'
          : '<span class="badge badge-status-pending">Pendente</span>';

        tr.innerHTML = `
          <td>${formatDate(tx.date)}</td>
          <td><span class="badge ${typeClass}">${tx.type}</span></td>
          <td><strong>${tx.description}</strong></td>
          <td>${tx.category}</td>
          <td>${tx.account}</td>
          <td>${tx.payment_method}</td>
          <td class="${amountClass}">${prefix}${formatCurrency(tx.amount)}</td>
          <td>${statusBadge}</td>
        `;

        transactionsBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Erro ao carregar transações:", err);
    }
  }

  // 4. Fetch Debts
  async function loadDebts() {
    try {
      const res = await fetch("/api/debts");
      if (!res.ok) return;
      const debts = await res.json();

      debtsList.innerHTML = "";
      if (debts.length === 0) {
        debtsList.innerHTML = '<p class="subtitle">Nenhuma dívida cadastrada.</p>';
        return;
      }

      debts.forEach((d) => {
        const card = document.createElement("div");
        card.className = "debt-card";
        card.innerHTML = `
          <div class="debt-header">
            <span class="debt-title">${d.creditor}</span>
            <span class="badge ${d.status === 'Ativa' ? 'badge-type-despesa' : 'badge-status-pending'}">${d.status}</span>
          </div>
          <div class="debt-balance">${formatCurrency(d.balance)}</div>
          <div class="debt-meta">
            <span>Parcela: ${formatCurrency(d.installment)}/mês</span>
            <span>Vencimento: ${formatDate(d.due_date)}</span>
          </div>
        `;
        debtsList.appendChild(card);
      });
    } catch (err) {
      console.error("Erro ao carregar dívidas:", err);
    }
  }

  // Toast Function
  function showToast(msg) {
    toast.textContent = msg;
    toast.hidden = false;
    setTimeout(() => {
      toast.hidden = true;
    }, 4000);
  }

  // Event Listeners
  selectMonth.addEventListener("change", () => {
    loadDashboard();
    loadTransactions();
  });

  selectCategory.addEventListener("change", loadTransactions);
  selectStatus.addEventListener("change", loadTransactions);

  let searchTimeout;
  inputSearch.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadTransactions, 300);
  });

  // Modal Open/Close
  btnOpenModal.addEventListener("click", () => {
    formDate.value = new Date().toISOString().split("T")[0];
    modalTransaction.hidden = false;
  });

  const closeModal = () => {
    modalTransaction.hidden = true;
    formTransaction.reset();
  };

  btnCloseModal.addEventListener("click", closeModal);
  btnCancelForm.addEventListener("click", closeModal);

  // Form Submit
  formTransaction.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      date: formDate.value,
      type: formType.value,
      category: formCategory.value,
      description: formDesc.value,
      payment_method: formPayment.value,
      amount: parseFloat(formAmount.value),
      essential: formEssential.checked,
      paid: formPaid.checked,
      obs: formObs.value,
      account: formAccount.value,
    };

    try {
      const res = await fetch("/api/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        alert(`Erro: ${errData.detail || "Falha ao gravar"}`);
        return;
      }

      closeModal();
      showToast("✨ Lançamento gravado no OneDrive com sucesso!");

      // Refresh UI
      await loadDashboard();
      await loadTransactions();
    } catch (err) {
      alert("Erro ao conectar com o servidor.");
    }
  });

  // Initial Load
  async function init() {
    await loadOptions();
    await loadDashboard();
    await loadTransactions();
    await loadDebts();
  }

  init();
});

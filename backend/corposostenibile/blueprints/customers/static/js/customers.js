/* ---------------------------------------------------------------------------
   customers.js
   ---------------------------------------------------------------------------
   Behaviour JS “leggero” per il feature-package *customers*.

   Funzioni incluse
   ----------------
   • Auto-inizializza i date-picker sugli <input data-picker="date">
   • Memorizza la TAB attiva (Bootstrap) in localStorage
   • Validazioni rapide lato-client su importi numerici (> 0)
   • Utility conferma-submit (data-confirm="…")
   • UX timeline:
        – scorciatoia “Espandi / Comprimi tutto” sugli accordion history
        – pulsante “Ripristina questa versione” (POST fetch + reload)
   • Live-updates via WebSocket:
        – ascolta “/ws/customers” e mostra badge “Modificato da …” sul
          dettaglio cliente se l’oggetto viene aggiornato da qualcun altro
----------------------------------------------------------------------------- */
(() => {
  "use strict";

  /* ------------------------------------------------------------------ utils */
  const qs     = (sel, el = document) => el.querySelector(sel);
  const qsa    = (sel, el = document) => [...el.querySelectorAll(sel)];
  const csrf   = () => qs('meta[name="csrf-token"]')?.getAttribute("content") || "";
  const reload = () => window.location.reload();

  const jsonPost = (url, payload = {}) =>
    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),           // compatibile con Flask-WTF / CSRFProtect
      },
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });

  const alertToast = (msg, color = "primary", delay = 4000) => {
    /* mini-toast bootstrap 5 */
    const tpl = `
      <div class="toast align-items-center text-bg-${color} border-0" role="alert">
        <div class="d-flex">
          <div class="toast-body">${msg}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto"
                  data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>`;
    const wrap = document.createElement("div");
    wrap.innerHTML = tpl.trim();
    const toastEl = wrap.firstElementChild;
    qs("body").appendChild(toastEl);
    const t = new bootstrap.Toast(toastEl, { delay });
    t.show();
  };

  /* ----------------------------- date-picker ------------------------------ */
  const initDatePickers = () => {
    if (!window.flatpickr) return;
    qsa("input[data-picker='date']").forEach((el) => {
      if (el._flatpickr) return;              // evita doppia init
      window.flatpickr(el, {
        dateFormat: "d/m/Y",
        allowInput: true,
        locale: "it",
        altInput: true,
        altFormat: "d/m/Y",
      });
    });
  };

  /* --------------------- conserva TAB attiva fra refresh ------------------ */
  const persistTabs = () => {
    const TAB_KEY = "cs:customers:activeTab";
    qsa('[data-bs-toggle="tab"]').forEach((toggle) => {
      /* restore */
      const stored = localStorage.getItem(TAB_KEY);
      if (stored && toggle.getAttribute("data-bs-target") === stored) {
        new bootstrap.Tab(toggle).show();
      }
      /* save */
      toggle.addEventListener("shown.bs.tab", (ev) => {
        localStorage.setItem(TAB_KEY, ev.target.getAttribute("data-bs-target"));
      });
    });
  };

  /* -------------------------- validazione importi ------------------------- */
  const validateAmounts = () => {
    document.addEventListener("input", (ev) => {
      const el = ev.target;
      if (!el.matches("input[data-amount]")) return;
      const val = parseFloat(el.value.replace(",", "."));
      el.classList.toggle("is-invalid", isNaN(val) || val < 0);
    });
  };

  /* --------------------------- conferma submit ---------------------------- */
  const bindConfirms = () => {
    document.addEventListener("submit", (ev) => {
      const form = ev.target;
      const msg  = form.dataset.confirm;
      if (msg && !window.confirm(msg)) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
      }
    });
  };

  /* --------------------- bootstrap alert auto-dismiss --------------------- */
  const autoDismissAlerts = () => {
    qsa(".alert[data-dismiss-timeout]").forEach((el) => {
      const ms = parseInt(el.dataset.dismissTimeout, 10) || 5000;
      setTimeout(() => {
        el.classList.remove("show");
        el.addEventListener("transitionend", () => el.remove());
      }, ms);
    });
  };

  /* ------------------------- timeline accordion UX ------------------------ */
  const historyAccordionHelpers = () => {
    const wrapper = qs("#historyAccordion");
    if (!wrapper) return;

    /* ——— pulsante Espandi / Comprimi tutto ——— */
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-outline-secondary btn-sm mb-2";
    btn.innerHTML = '<i class="bi bi-arrows-expand"></i> Espandi tutto';
    wrapper.parentElement.insertBefore(btn, wrapper);

    let expanded = false;
    btn.addEventListener("click", () => {
      expanded = !expanded;
      btn.innerHTML = expanded
        ? '<i class="bi bi-arrows-collapse"></i> Comprimi tutto'
        : '<i class="bi bi-arrows-expand"></i> Espandi tutto';

      qsa(".accordion-collapse", wrapper).forEach((c) => {
        const acc = bootstrap.Collapse.getOrCreateInstance(c);
        expanded ? acc.show() : acc.hide();
      });
    });

    /* ——— handler “Ripristina questa versione” ——— */
    wrapper.addEventListener("click", (ev) => {
      const btnRestore = ev.target.closest("button[data-action='restore-version']");
      if (!btnRestore) return;

      const clienteId = btnRestore.dataset.clienteId;
      const txId      = btnRestore.dataset.txId;
      if (!clienteId || !txId) return;

      if (!window.confirm("Confermi il ripristino di questa versione?")) return;

      btnRestore.disabled = true;
      btnRestore.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

      jsonPost(`/clients/${clienteId}/history/${txId}/restore`)
        .then((resp) => {
          if (!resp.ok) throw new Error("Rollback fallito");
          alertToast("Versione ripristinata con successo", "success");
          setTimeout(reload, 1500);
        })
        .catch(() => {
          alertToast("Errore nel ripristino versione", "danger", 6000);
          btnRestore.disabled = false;
          btnRestore.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> Ripristina';
        });
    });
  };

  /* ----------------------------- live-updates ----------------------------- */
  const initLiveUpdates = () => {
    /* Connette al WS /ws/customers e gestisce badge “Modificato da …” */
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${proto}://${window.location.host}/ws/customers`;
    let socket;

    const connect = () => {
      socket = new WebSocket(wsUrl);

      socket.addEventListener("open", () => {
        console.debug("[WS] connected:", wsUrl);
      });

      socket.addEventListener("message", (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.event !== "customer_updated") return;
          handleCustomerUpdated(msg.payload || {});
        } catch (err) {
          console.error("WS message parse error", err);
        }
      });

      socket.addEventListener("close", () => {
        console.warn("[WS] closed, retrying in 5s");
        setTimeout(connect, 5000);
      });

      socket.addEventListener("error", (err) => {
        console.error("[WS] error:", err);
        socket.close();
      });
    };

    const handleCustomerUpdated = ({ cliente_id, user_id }) => {
      const m = window.location.pathname.match(/\/clients\/(\d+)/);
      if (!m) return;                       // non siamo su detail-view
      const currentId = parseInt(m[1], 10);
      if (currentId !== cliente_id) return; // evento di un altro cliente

      /* se l’update arriva dall’utente corrente → ignora */
      const curUser = document.body.dataset.currentUserId;
      if (curUser && parseInt(curUser, 10) === user_id) return;

      showUpdateBadge(user_id);
    };

    const showUpdateBadge = (userId) => {
      const hdr = qs("h1 .text-muted")?.parentElement; // <h1> container
      if (!hdr) return;

      if (!qs("#liveUpdateBadge", hdr)) {
        const badge = document.createElement("span");
        badge.id = "liveUpdateBadge";
        badge.className = "badge text-bg-warning ms-2";
        badge.innerHTML = `Modificato da utente #${userId}`;
        hdr.appendChild(badge);
        setTimeout(() => badge.remove(), 10000);
      }
    };

    connect();
  };

  /* -------------------------------- init ---------------------------------- */
  document.addEventListener("DOMContentLoaded", () => {
    initDatePickers();
    persistTabs();
    validateAmounts();
    bindConfirms();
    autoDismissAlerts();
    historyAccordionHelpers();
    initLiveUpdates();
  });
})();

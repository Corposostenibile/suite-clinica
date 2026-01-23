/* static/js/kanban.js
   Drag-&-drop + chiamata API /status */
   $(function () {
    $("#sortable-wrapper").sortable({ cancel: ".overflow-hidden" });
  
    $(".connectedSortable").sortable({
      connectWith: ".connectedSortable",
      items: ".kanban-card",
      placeholder: "ui-sortable-placeholder",
      start: function (e, ui) { ui.placeholder.height(ui.item.outerHeight()); },
      update: function (e, ui) {
        const card   = ui.item;
        const taskId = card.data("id");
        const status = card.closest(".connectedSortable").data("status");
  
        /* PATCH → /api/tasks/<id>/status */
        fetch(`/api/tasks/${taskId}/status`, {
          method : "PATCH",
          headers: { "Content-Type": "application/json" },
          body   : JSON.stringify({ status })
        }).then(r => {
          if (!r.ok) console.error("Errore aggiornamento status");
        });
      }
    }).disableSelection();
  });
  
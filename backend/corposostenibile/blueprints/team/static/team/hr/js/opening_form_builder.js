/* --------------------------------------------------------------------
 *  Mini-form-builder “vanilla”  (nessuna dipendenza esterna)
 * ------------------------------------------------------------------*/
document.addEventListener('DOMContentLoaded', () => {

  // dom riferimenti -------------------------------------------------
  const questionsOL = document.getElementById('questions');
  const hiddenField = document.getElementById('form_schema');
  const btnAdd      = document.getElementById('btnAdd');
  const btnClear    = document.getElementById('btnClear');

  // nomi 5 campi anagrafici fissi (servono al backend)
  const stdNames = ['full_name','last_name','email','phone','cv_file'];

  // helper mostra/nasconde btnClear
  const toggleClear = () =>
    btnClear.classList.toggle('d-none', questionsOL.children.length === 0);

  // aggiungi domanda ------------------------------------------------
  btnAdd.addEventListener('click', () => {
    const li = document.createElement('li');
    li.className =
      'list-group-item d-flex justify-content-between align-items-start gap-2';
    li.innerHTML = `
      <input type="text" class="form-control form-control-sm flex-grow-1"
             placeholder="Testo della domanda…" required>
      <button type="button" class="btn btn-sm btn-outline-danger">
        <i class="ri-close-line"></i>
      </button>`;
    li.querySelector('button').onclick = () => { li.remove(); toggleClear(); };
    questionsOL.appendChild(li);
    toggleClear();
  });

  // svuota elenco ---------------------------------------------------
  btnClear.addEventListener('click', () => {
    questionsOL.innerHTML = '';
    toggleClear();
  });

  // serializza prima del submit ------------------------------------
  document.querySelector('form').addEventListener('submit', () => {
    const extras = Array.from(questionsOL.children)
      .map(li => li.querySelector('input').value.trim())
      .filter(Boolean);                                   // elimina vuoti

    /* struttura compatibile con _wtform_from_schema():
       {
         fields: [
           {name:'q1', label:'Domanda…', type:'text', required:false},
           …
         ]
       }
    */
    const fields = extras.map((label, i) => ({
      name:  `q${i+1}`,
      label: label,
      type:  'text',
      required: false
    }));
    hiddenField.value = JSON.stringify({fields});
  });
});

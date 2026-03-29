(function () {
  const form = document.getElementById("expense-filters-form");
  if (!form) return;
  form.querySelectorAll("select.expense-filter-select").forEach(function (sel) {
    sel.addEventListener("change", function () {
      form.submit();
    });
  });
})();

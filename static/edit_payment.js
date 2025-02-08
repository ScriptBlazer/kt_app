document.addEventListener("DOMContentLoaded", () => {
  function showModal(errorMessage) {
    const modal = document.getElementById("error-modal");
    const modalMessage = document.getElementById("modal-message");
    if (modal && modalMessage) {
      modalMessage.textContent = errorMessage;
      modal.style.display = "flex";
    }
  }

  function closeModal() {
    const modal = document.getElementById("error-modal");
    if (modal) {
      modal.style.display = "none";
    }
  }
  window.closeModal = closeModal;

  const paymentSection = document.getElementById("payment-section");
  const addPaymentButton = document.getElementById("add-payment");
  const totalFormsInput = document.querySelector(
    "input[name='payment-TOTAL_FORMS']"
  );
  const basePaymentEntry = document.querySelector(".payment-entry");
  let usedPaymentNumbers = [];

  function updateTotalForms() {
    const totalFormsInput = document.querySelector(
      "input[name='payment-TOTAL_FORMS']"
    );
    if (!totalFormsInput) {
      console.error(
        "Error: totalFormsInput is null. Ensure the hidden input exists in the form."
      );
      return;
    }

    const visiblePayments = paymentSection.querySelectorAll(
      ".payment-entry:not(.hidden)"
    );
    totalFormsInput.value = visiblePayments.length;
  }

  function getNextPaymentNumber() {
    let num = 1;
    while (usedPaymentNumbers.includes(num)) {
      num += 1;
    }
    usedPaymentNumbers.push(num);
    return num;
  }

  function createPaymentSection() {
    if (!basePaymentEntry) return;

    const newPayment = basePaymentEntry.cloneNode(true);
    newPayment.classList.remove("hidden");
    newPayment.style.display = "block";

    const newPaymentNumber = getNextPaymentNumber();
    newPayment.setAttribute("data-payment-number", newPaymentNumber);

    newPayment.querySelectorAll("input, select").forEach((input) => {
      const name = input
        .getAttribute("name")
        .replace(/\d+/, newPaymentNumber - 1);
      input.setAttribute("name", name);
      input.setAttribute("id", `id_${name}`);
      input.value = "";
    });

    let headline = newPayment.querySelector("h4");
    if (!headline) {
      headline = document.createElement("h4");
      newPayment.prepend(headline);
    }
    headline.textContent = `Payment ${newPaymentNumber}`;

    const removeButton = newPayment.querySelector(".remove-payment");
    if (removeButton) {
      removeButton.addEventListener("click", () =>
        handleRemovePayment(newPayment)
      );
    }

    paymentSection.insertBefore(newPayment, addPaymentButton);
    updateTotalForms();
  }

  function handleRemovePayment(paymentElement) {
    const paymentNumber = parseInt(
      paymentElement.getAttribute("data-payment-number"),
      10
    );
    const fields = paymentElement.querySelectorAll(
      "input:not([type='hidden']), select"
    );

    const allFieldsEmpty = Array.from(fields).every((field) => {
      const fieldValue = field.value ? field.value.trim() : "";
      const fieldName = field.getAttribute("name") || "";
      return (
        fieldName.endsWith("-DELETE") ||
        fieldValue === "" ||
        fieldValue.toLowerCase() === "none"
      );
    });

    if (!allFieldsEmpty) {
      showModal("You can't remove a payment until all fields are empty.");
      return;
    }

    let deleteInput = paymentElement.querySelector("input[name$='-DELETE']");
    if (!deleteInput) {
      deleteInput = document.createElement("input");
      deleteInput.type = "hidden";
      deleteInput.name = `${paymentElement.dataset.paymentNumber}-DELETE`;
      deleteInput.value = "on";
      paymentElement.appendChild(deleteInput);
    } else {
      deleteInput.checked = true;
    }

    paymentElement.style.display = "none";
    usedPaymentNumbers = usedPaymentNumbers.filter(
      (num) => num !== paymentNumber
    );
    updateTotalForms();
  }

  paymentSection
    .querySelectorAll(".payment-entry")
    .forEach((paymentEntry, index) => {
      const paymentNumber = index + 1;
      usedPaymentNumbers.push(paymentNumber);
      paymentEntry.setAttribute("data-payment-number", paymentNumber);

      const removeButton = paymentEntry.querySelector(".remove-payment");
      if (removeButton) {
        removeButton.addEventListener("click", () =>
          handleRemovePayment(paymentEntry)
        );
      }

      let headline = paymentEntry.querySelector("h4");
      if (!headline) {
        headline = document.createElement("h4");
        paymentEntry.prepend(headline);
      }
      headline.textContent = `Payment ${paymentNumber}`;
    });

  if (addPaymentButton) {
    addPaymentButton.addEventListener("click", createPaymentSection);
  }

  updateTotalForms();
});


document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("barber-reschedule-form");
    if (!form) return;

    const dateInput = document.getElementById("date");
    const slotsContainer = document.getElementById("time-slots");
    const slotMessage = document.getElementById("slot-message");
    const selectedTime = document.getElementById("selected-time");
    const saveButton = document.getElementById("save-changes");

    const today = new Date();
    dateInput.min = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    let requestNumber = 0;

    async function loadAvailableTimes() {
        const currentRequest = ++requestNumber;

        slotsContainer.replaceChildren();
        selectedTime.value = "";
        saveButton.disabled = true;

        if (!dateInput.value) {
            slotMessage.textContent = "Choose a date first.";
            return;
        }

        slotMessage.textContent = "Checking availability...";

        const params = new URLSearchParams({
            date: dateInput.value
        });

        try {
            const response = await fetch(
                `${form.dataset.availabilityUrl}?${params}`
            );

            if (!response.ok) {
                throw new Error("Unable to load available times.");
            }

            const data = await response.json();

            if (currentRequest !== requestNumber) return;

            if (!data.slots.length) {
                slotMessage.textContent =
                    "No available times for this date.";
                return;
            }

            slotMessage.textContent = "Choose a new time:";

            data.slots.forEach(slot => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "time-slot";
                button.textContent = slot.label;

                button.addEventListener("click", () => {
                    slotsContainer.querySelectorAll(".time-slot")
                        .forEach(item => item.classList.remove("selected"));

                    button.classList.add("selected");

                    // Backend expects HH:MM, not a full ISO datetime.
                    const timePart = slot.value.split("T")[1];
                    selectedTime.value = timePart.slice(0, 5);

                    saveButton.disabled = false;
                });

                slotsContainer.appendChild(button);
            });

        } catch (error) {
            if (currentRequest !== requestNumber) return;

            slotMessage.textContent =
                "Could not load available times. Please try again.";

            console.error(error);
        }
    }

    dateInput.addEventListener("change", loadAvailableTimes);

    // Load slots for the appointment's current date.
    loadAvailableTimes();

    form.addEventListener("submit", event => {
        if (!selectedTime.value) {
            event.preventDefault();
            slotMessage.textContent =
                "Please select an available time.";
        }
    });
});


document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("booking-form");
    const dateInput = document.getElementById("appointment-date");
    const slotsContainer = document.getElementById("time-slots");
    const slotMessage = document.getElementById("slot-message");
    const selectedTime = document.getElementById("selected-time");
    const summary = document.getElementById("booking-summary");
    const submitButton = document.getElementById("book-button");
    const formMessage = document.getElementById("form-message");
    const bookingSuccess = document.getElementById("booking-success");
    const cancelButton = document.getElementById("cancel-appointment-btn");
    const rescheduleButton = document.getElementById(
        "reschedule-appointment-btn"
    );

    // Use the customer's local date for the input minimum.
    const today = new Date();
    const localToday = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    dateInput.min = localToday;

    function getSelection(name) {
        return form.querySelector(`input[name="${name}"]:checked`);
    }

    function updateSummary() {
        const barber = getSelection("barber");
        const service = getSelection("service");

        if (!barber || !service || !selectedTime.value) {
            summary.textContent = "Select your appointment details above.";
            return;
        }

        const barberName = barber.closest("label")
            .querySelector("h3").textContent.trim();

        const serviceName = service.closest("label")
            .querySelector("h3").textContent.trim();

        const duration = Number(service.dataset.duration);
        const start = new Date(selectedTime.value);
        const end = new Date(start.getTime() + duration * 60000);

        const formatTime = value => value.toLocaleTimeString(
            "en-US",
            {hour: "numeric", minute: "2-digit"}
        );

        summary.textContent =
            `${barberName} • ${serviceName} • ` +
            `${formatTime(start)}–${formatTime(end)}`;
    }

    let requestNumber = 0;

    async function loadAvailableTimes() {
        const currentRequest = ++requestNumber;
        const barber = getSelection("barber");
        const service = getSelection("service");
        const date = dateInput.value;

        slotsContainer.replaceChildren();
        selectedTime.value = "";
        formMessage.textContent = "";
        updateSummary();

        if (!barber || !service || !date) {
            slotMessage.textContent =
                "Select a barber, service, and date.";
            return;
        }

        slotMessage.textContent = "Checking availability...";

        const params = new URLSearchParams({
            barber: barber.value,
            service: service.value,
            date: date
        });

        try {
            const response = await fetch(
                `${form.dataset.availabilityUrl}?${params}`
            );

            if (!response.ok) {
                throw new Error("Unable to load available times.");
            }

            const data = await response.json();

            // Ignore results from outdated requests.
            if (currentRequest !== requestNumber) return;

            if (!data.slots.length) {
                slotMessage.textContent =
                    "No available times for this date.";
                return;
            }

            slotMessage.textContent = "Select an available time:";

            data.slots.forEach(slot => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "time-slot";
                button.textContent = slot.label;

                button.addEventListener("click", () => {
                    document.querySelectorAll(".time-slot")
                        .forEach(item => item.classList.remove("selected"));

                    button.classList.add("selected");
                    selectedTime.value = slot.value;
                    updateSummary();
                });

                slotsContainer.appendChild(button);
            });

        } catch (error) {
            if (currentRequest !== requestNumber) return;
            slotMessage.textContent =
                "Could not load times. Please try again.";
            console.error(error);
        }
    }

    form.querySelectorAll('input[name="barber"], input[name="service"]')
        .forEach(input => input.addEventListener(
            "change", loadAvailableTimes
        ));

    dateInput.addEventListener("change", loadAvailableTimes);

    
    form.addEventListener("submit", async event => {
        event.preventDefault();

        if (!selectedTime.value) {
            formMessage.textContent =
                "Please select an appointment time.";
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = "Booking...";
        formMessage.textContent = "";

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error || "Unable to book appointment."
                );
            }

            formMessage.textContent = data.message;

            // Show the cancellation button for the new appointment.
            console.log("Booking response:", data);
            if (data.success) {
                if (data.cancellation_url) {
                    cancelButton.href = data.cancellation_url;
                }
            
                if (data.reschedule_url) {
                    rescheduleButton.href = data.reschedule_url;
                }
            
                bookingSuccess.hidden = false;
            }

            // Clear the form after successful booking.
            form.reset();
            selectedTime.value = "";
            slotsContainer.replaceChildren();
            slotMessage.textContent =
                "Select a barber, service, and date.";
            updateSummary();

        } catch (error) {
            // Refresh availability if a slot was taken.
            await loadAvailableTimes();

            formMessage.textContent = error.message;

        } finally {
            submitButton.disabled = false;
            submitButton.textContent =
                "Confirm Appointment →";
        }
    });
});

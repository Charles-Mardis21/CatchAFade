
document.addEventListener("DOMContentLoaded", () => {
    const slides = document.querySelectorAll(".slide");
    const nextButton = document.querySelector(".next");
    const previousButton = document.querySelector(".previous");

    // Change this selector if your dots container
    // has a different class in your HTML.
    const dotsContainer = document.querySelector(".carousel-dots");

    if (!slides.length) return;

    let currentSlide = 0;
    let autoPlay;

    // Automatically generate one dot per slide.
    if (dotsContainer) {
        dotsContainer.replaceChildren();

        slides.forEach((slide, index) => {
            const dot = document.createElement("button");

            dot.type = "button";
            dot.className = "dot";
            dot.setAttribute(
                "aria-label",
                `Go to slide ${index + 1}`
            );

            dot.addEventListener("click", () => {
                showSlide(index);
                resetAutoPlay();
            });

            dotsContainer.appendChild(dot);
        });
    }

    const dots = dotsContainer
        ? dotsContainer.querySelectorAll(".dot")
        : [];

    function showSlide(index) {
        currentSlide =
            (index + slides.length) % slides.length;

        slides.forEach((slide, i) => {
            slide.classList.toggle(
                "active",
                i === currentSlide
            );
        });

        dots.forEach((dot, i) => {
            dot.classList.toggle(
                "active",
                i === currentSlide
            );
        });
    }

    function nextSlide() {
        showSlide(currentSlide + 1);
    }

    function previousSlide() {
        showSlide(currentSlide - 1);
    }

    function startAutoPlay() {
        if (slides.length <= 1) return;

        autoPlay = setInterval(nextSlide, 5000);
    }

    function resetAutoPlay() {
        clearInterval(autoPlay);
        startAutoPlay();
    }

    nextButton?.addEventListener("click", () => {
        nextSlide();
        resetAutoPlay();
    });

    previousButton?.addEventListener("click", () => {
        previousSlide();
        resetAutoPlay();
    });

    showSlide(0);
    startAutoPlay();
});

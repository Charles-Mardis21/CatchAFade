const slides = document.querySelectorAll(".slide");
const dots = document.querySelectorAll(".dot");

const nextButton = document.querySelector(".next");
const previousButton = document.querySelector(".previous");

let currentSlide = 0;
let autoPlay;


/*
    Displays whichever slide number we give it.
*/
function showSlide(index) {

    slides.forEach(slide => {
        slide.classList.remove("active");
    });

    dots.forEach(dot => {
        dot.classList.remove("active");
    });

    slides[index].classList.add("active");
    dots[index].classList.add("active");

}


/*
    Move forward one slide.
*/
function nextSlide() {

    currentSlide++;

    if (currentSlide >= slides.length) {
        currentSlide = 0;
    }

    showSlide(currentSlide);
}


/*
    Move backward one slide.
*/
function previousSlide() {

    currentSlide--;

    if (currentSlide < 0) {
        currentSlide = slides.length - 1;
    }

    showSlide(currentSlide);
}


/*
    Automatically move every 5 seconds.
*/
function startAutoPlay() {

    autoPlay = setInterval(nextSlide, 5000);

}


/*
    Reset timer when the user manually
    changes the picture.
*/
function resetAutoPlay() {

    clearInterval(autoPlay);

    startAutoPlay();

}


nextButton.addEventListener("click", () => {

    nextSlide();

    resetAutoPlay();

});


previousButton.addEventListener("click", () => {

    previousSlide();

    resetAutoPlay();

});


dots.forEach((dot, index) => {

    dot.addEventListener("click", () => {

        currentSlide = index;

        showSlide(currentSlide);

        resetAutoPlay();

    });

});


startAutoPlay();
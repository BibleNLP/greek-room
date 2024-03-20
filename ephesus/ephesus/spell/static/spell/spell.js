// Spell checker UI functions

// Interactive chapter navigation
const books = document.querySelector("#details-pane .bcv-nav:first-child");
const chapters = document.querySelector("#details-pane .bcv-nav:nth-child(2)");
books.addEventListener("click", (event) => {
  // Clear existing chapters
  while (chapters.hasChildNodes()) {
    chapters.removeChild(chapters.firstChild);
  }

  event.target.dataset.chapters.split("|").forEach((chapter) => {
    const chapterSpan = document.createElement("span");
    chapterSpan.textContent = chapter;
    chapters.appendChild(chapterSpan);
  });
});

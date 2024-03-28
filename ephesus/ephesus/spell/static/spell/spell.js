// Spell checker UI functions
import {
  getDataFromElementURL,
  setInnerHtml,
} from "../../static/home/greekroom.js";

const detailsPane = document.getElementById("details-pane");

// Redefine the parent event listener for the spell checker
detailsPane.addEventListener("click", (event) => {
  const booksPane = document.querySelector(
    "#details-pane .bcv-nav:first-child"
  );
  const chapters = document.querySelector(
    "#details-pane .bcv-nav:nth-child(2)"
  );

  // Interactive Book navigation
  const bookSpan = event.target.closest("span[data-chapters]");
  if (bookSpan) {
    // Show selected book

    const previouslySelectedBook = booksPane.querySelector(
      'span[class~="bold"]'
    );
    previouslySelectedBook !== null
      ? previouslySelectedBook.classList.remove("bold")
      : true;
    event.target.classList.add("bold");

    // Clear existing chapters, if any
    while (chapters.hasChildNodes()) {
      chapters.removeChild(chapters.firstChild);
    }

    event.target.dataset.chapters.split("|").forEach((chapter) => {
      const chapterSpan = document.createElement("span");
      chapterSpan.classList.add("bcv-nav-item");
      chapterSpan.textContent = chapter;
      chapterSpan.dataset.url = `${event.target.dataset.url}?ref=${event.target.dataset.bookCode} ${chapter}`;
      chapterSpan.dataset.chapterLabel = chapter;
      chapters.appendChild(chapterSpan);
    });
  }

  // Interactive Chapter navigation
  const chapterSpan = event.target.closest("span[data-chapter-label]");
  if (chapterSpan) {
    const verses = document.querySelector('div[role="main"]');
    const chapters = document.querySelector(
      "#details-pane .bcv-nav:nth-child(2)"
    );

    // Clear existing verses, if any
    const existingContent = document.querySelector('div[id="verses-content"]');
    if (existingContent !== undefined) {
      existingContent.remove();
    }

    // Show selected chapter
    const previouslySelectedChapter = chapters.querySelector(
      'span[class~="bold"]'
    );
    previouslySelectedChapter !== null
      ? previouslySelectedChapter.classList.remove("bold")
      : true;
    event.target.classList.add("bold");

    // Get verse content
    getDataFromElementURL(event.target).then(
      (content) => {
        setInnerHtml(verses, content);
      },
      (reason) => {
        setInnerHtml(
          verses,
          "There was an error while fetching the content. Try again."
        );
      }
    );
  }
});

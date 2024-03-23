// Spell checker UI functions
import {
  getDataFromElementURL,
  setInnerHtml,
} from "../../static/home/greekroom.js";

const books = document.querySelector("#details-pane .bcv-nav:first-child");
const chapters = document.querySelector("#details-pane .bcv-nav:nth-child(2)");
const verses = document.querySelector('div[role="main"]');

// Interactive Book navigation
books.addEventListener("click", (event) => {
  // Handle cases where the click is not
  // exactly on a book name
  if (event.target.dataset.chapters === undefined) {
    // noop
    return;
  }

  // Show selected book
  const previouslySelectedBook = books.querySelector('span[class~="bold"]');
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
    chapters.appendChild(chapterSpan);
  });
});

// Interactive Chapter navigation
chapters.addEventListener("click", (event) => {
  // Handle cases where the click is not
  // exactly on a chapter number
  if (event.target.dataset.url === undefined) {
    // noop
    return;
  }

  // Clear existing verses, if any
  const existingContent = document.querySelector('div[name="verses-content"]');
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
});

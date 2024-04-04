// Spell checker UI functions
import {
  getDataFromElementURL,
  setInnerHtml,
} from "../../static/home/greekroom.js";

// Setup mutation observer
const observer = new MutationObserver(() => {
  console.log("callback that runs when observer is triggered");
});

const detailsPane = document.getElementById("details-pane");

// Mouseover interaction for words/tokens
const wordDetailsTemplate = document.querySelector("#word-details-template");
const spellSuggestionsTemplate = document.querySelector(
  "#spell-suggestions-template"
);
function detailsPaneMouseoverHandler(event) {
  // Show word/token details
  const tokenSpan = event.target.closest('span[class~="token"]');
  if (tokenSpan) {
    // Update details pane
    const wordDetails = JSON.parse(tokenSpan.dataset.details);
    const wordDetailsDiv = wordDetailsTemplate.content.cloneNode(true);
    wordDetailsDiv.querySelector("div b").textContent = wordDetails["count"];
    document.querySelector("#suggestions div").replaceWith(wordDetailsDiv);

    // Update spell suggestions pane, if any
    if ("spellSuggestions" in wordDetails) {
      const spellSuggestions = spellSuggestionsTemplate.content.cloneNode(true);
      const spellSuggestionsList = spellSuggestions.querySelector("ul");
      wordDetails["spellSuggestions"].forEach((suggestion) => {
        const suggestionEntry = document.createElement("li");
        suggestionEntry.setAttribute("title", `${JSON.stringify(suggestion)}`);
        suggestionEntry.classList.add("spell-suggestion", "blue");
        suggestionEntry.textContent = suggestion["alternativeSpelling"];
        spellSuggestionsList.appendChild(suggestionEntry);
      });
      document.querySelector("#suggestions div").append(spellSuggestions);
    }
    return;
  }
}
detailsPane.addEventListener("mouseover", detailsPaneMouseoverHandler);

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
    return;
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

        // Start/reset observing for text edits.
        observer.observe(document.querySelector("#verses-content"), {
          childList: true,
          subtree: true,
          characterData: true,
        });
      },
      (reason) => {
        setInnerHtml(
          verses,
          "There was an error while fetching the content. Try again."
        );
      }
    );

    // Reset the mouseover listener,
    // incase it was disabled from a previous interaction
    detailsPane.removeEventListener("mouseover", detailsPaneMouseoverHandler);
    detailsPane.addEventListener("mouseover", detailsPaneMouseoverHandler);

    return;
  }

  // Handle token click
  const tokenSpan = event.target.closest('span[class~="token"]');
  if (tokenSpan) {
    // If already clicked on a token, ignore
    if (document.querySelector("span.token.highlight") !== null) {
      //noop
      return;
    }
    detailsPane.removeEventListener("mouseover", detailsPaneMouseoverHandler);
    tokenSpan.classList.add("highlight");
    document.querySelector("#suggestions div small").classList.remove("hide");
    return;
  }

  // Handle clear word details/suggestions
  const clearTokenDetails = event.target.closest(
    'small[class~="clear-suggestions"]'
  );
  if (clearTokenDetails) {
    document
      .querySelector("span.token.highlight")
      .classList.remove("highlight");
    const spellDetailsPlaceholder = document
      .querySelector("#spell-details-placeholder-template")
      .content.cloneNode(true);
    document
      .querySelector("#suggestions div")
      .replaceWith(spellDetailsPlaceholder);

    // Reactivate mouseover action for tokens
    detailsPane.addEventListener("mouseover", detailsPaneMouseoverHandler);
    return;
  }

  // Handle spell suggestion selection
  const spellSuggestionLi = event.target.closest("li.spell-suggestion");
  if (spellSuggestionLi) {
    console.log(spellSuggestionLi.innerHTML);
    document.querySelector("span.token.highlight").innerHTML =
      spellSuggestionLi.innerHTML;

    // // Refresh verse data
    // document
    //   .querySelector(
    //     `span.bcv-nav-item[data-url*="${
    //       document.querySelector("span.token.highlight").closest("div.verse")
    //         .dataset.ref
    //     }"]`
    //   )
    //   .click();
  }
});

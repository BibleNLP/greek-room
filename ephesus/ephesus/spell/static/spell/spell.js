// Spell checker UI functions
import {
  getDataFromElementURL,
  setInnerHtml,
} from "../../static/home/greekroom.js";

// Refresh verse data from the backend
function reloadVerses() {
  document
    .querySelector("#details-pane .bcv-nav:nth-child(2) span.bcv-nav-item.bold")
    .click();
}

// Refresh a single verse from the backend
function reloadVerse(verseDiv) {
  if (!verseDiv) {
    return;
  }
  getVerseSuggestions(verseDiv.innerText, verseDiv.dataset.suggestionsUrl).then(
    (suggestionContent) => {
      verseDiv.parentElement.outerHTML = suggestionContent;
    },
    (reason) => {
      console.log(reason);
    }
  );
}

// Method to persist verse content in the backend
async function saveVerse(verse, url) {
  const response = await fetch(url, {
    method: "POST",
    headers: new Headers({
      Accept: "application/json",
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ verse: verse }),
  });
  if (response.status === 200) {
    return Promise.resolve(await response.json());
  } else if (response.status === 500) {
    let data = undefined;
    if (response.headers.get("content-type") === "application/json") {
      data = await response.json();
    } else {
      data = {
        detail:
          "There was an error while processing this request. Please try again.",
      };
    }
    return Promise.reject(data);
  } else {
    return Promise.reject(
      "There was an error while processing this request. Please try again."
    );
  }
}

// Method to get a single verse's suggestions
async function getVerseSuggestions(verse, url) {
  const response = await fetch(url, {
    method: "PUT",
    headers: new Headers({
      Accept: "text/html",
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ verse: verse }),
  });
  if (response.status === 200) {
    return Promise.resolve(await response.text());
  } else if (response.status === 500) {
    let data = undefined;
    if (response.headers.get("content-type") === "application/json") {
      data = await response.json();
    } else {
      data = {
        detail:
          "There was an error while processing this request. Please try again.",
      };
    }
    return Promise.reject(data);
  } else {
    return Promise.reject(
      "There was an error while processing this request. Please try again."
    );
  }
}

// Handle verse commit event
function verseCommitHandler(commitIcon) {
  // Save updated verse on commit
  const verseDiv = commitIcon.previousElementSibling;
  saveVerse(verseDiv.innerText, verseDiv.dataset.saveUrl).then(
    (content) => {
      // reload the single verse
      reloadVerse(verseDiv);
    },
    (reason) => {
      console.log(reason);
      reloadVerses();
    }
  );
}

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
    const spellSuggestions = spellSuggestionsTemplate.content.cloneNode(true);

    // Update spell suggestions, if any
    if (wordDetails != null && wordDetails.length > 0) {
      // const spellSuggestions = spellSuggestionsTemplate.content.cloneNode(true);
      const spellSuggestionsList = spellSuggestions.querySelector("ul");
      wordDetails.forEach((suggestion) => {
        const suggestionEntry = document.createElement("li");
        // suggestionEntry.setAttribute("title", `${JSON.stringify(suggestion)}`);
        suggestionEntry.classList.add("spell-suggestion", "blue");
        suggestionEntry.textContent = `${suggestion["word"]} (n:${suggestion["count"]}, c:${suggestion["cost"]})`;
        suggestionEntry.dataset.word = `${suggestion["word"]}`;
        spellSuggestionsList.appendChild(suggestionEntry);
      });
    }

    document.querySelector("#suggestions div").replaceWith(spellSuggestions);
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
      chapterSpan.dataset.ref = `${bookSpan.dataset.bookCode} ${chapter}`;
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

    // Clear existing verses and suggestions, if any
    const existingContent = document.querySelector("#verses-content");
    if (existingContent != null) {
      existingContent.remove();
    }
    const existingSuggestions = document.querySelector("#suggestions");
    if (existingSuggestions != null) {
      existingSuggestions.remove();
    }

    // Show selected chapter
    const previouslySelectedChapter = chapters.querySelector(
      'span[class~="bold"]'
    );
    previouslySelectedChapter !== null
      ? previouslySelectedChapter.classList.remove("bold")
      : true;
    event.target.classList.add("bold");

    // Show loader
    document.querySelector('#details-pane img[src*="loader"]').style.display =
      "";

    // Get verse content
    getDataFromElementURL(event.target).then(
      (content) => {
        // Hide loader
        document.querySelector(
          '#details-pane img[src*="loader"]'
        ).style.display = "none";

        setInnerHtml(verses, content);
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
    // Ignore suggestion selection when word not selected
    if (document.querySelector("span.token.highlight") == null) {
      return;
    }
    document.querySelector("span.token.highlight").innerHTML =
      spellSuggestionLi.dataset.word;

    // Save updated verse
    const verseDiv = document
      .querySelector("span.token.highlight")
      .closest("div.verse");

    saveVerse(verseDiv.innerText, verseDiv.dataset.saveUrl).then(
      (content) => {
        // reload verses
        reloadVerse(verseDiv);
        // getVerseSuggestions(
        //   verseDiv.innerText,
        //   verseDiv.dataset.suggestionsUrl
        // ).then((suggestionContent) => {
        //   verseDiv.parentElement.outerHTML = suggestionContent;
        // });
      },
      (reason) => {
        console.log(reason);
        reloadVerses();
      }
    );
  }

  // Handle verse commit icon click
  const commitIcon = event.target.closest("div.commit-icon");
  if (commitIcon) {
    verseCommitHandler(commitIcon);
    return;
  }
});

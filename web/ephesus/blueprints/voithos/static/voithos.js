// Javascript for the Voithos page

import { Cursor, debounce } from "./utils.js";

// Method to get formatted scripture content from the backend
async function getScriptureContent(element, formatted = true) {
  var URL = window.location.origin + element.dataset.url;
  if (formatted) {
    URL += "?formatted=true";
  }

  const response = await fetch(URL);
  if (response.ok) {
    let data = undefined;

    if (formatted) {
      data = await response.text();
    } else {
      data = await response.json();
    }
    return Promise.resolve(data);
  } else {
    return Promise.reject("Unable to retrieve data.");
  }
}

// Method to persist (POST) scriptural content to backend
async function setScriptureContent(contentState) {
  const URL =
    window.location.origin +
    document.getElementsByClassName("link underline")[0].dataset.url;

  const response = await fetch(URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(contentState),
  });

  if (response.ok) {
    let data = await response.json();
    return Promise.resolve(data);
  } else {
    return Promise.reject("Error while persisting data.");
  }
}

// Method to get suggestions data for a resource
// `filters` is the `dirtyState` variable which
// provides the subset of {book:Set(chapter)}
// that were edited and thus need recomputation.
async function getSuggestions(resourceId, filters) {
  let filterParams = "";
  for (let bookId in filters) {
    filterParams += `?filter=${bookId}_${Array.from(
      filters[bookId].chapters
    ).join(`&filter=${bookId}_`)}`;
  }
  let URL = `${window.location.origin}/voithos/api/v1/suggestions/${resourceId}${filterParams}`;

  const response = await fetch(URL);
  if (response.ok) {
    let data = await response.json();
    return Promise.resolve(data);
  } else {
    return Promise.reject("Unable to retrieve data.");
  }
}

// Method to highlight (underline) flaggedTokens in the UI
// and add capability to show context menu with suggestions
function highlightTokens(suggestions, contentState, isRestoreCursor = false) {
  let tokenPattern = undefined;
  Object.entries(suggestions).forEach(([flaggedTokenId, suggestion], index) => {
    // The regex is a concatenation of all flaggedTokens
    // separated by word boundaries (\b). Also, each
    // match is within a named capture group that is
    // derived from its flaggedToken ID (taken from DB).
    // e.g. `index_1` means the match has the
    // flagged_token_id=1 in DB.
    if (index === 0) {
      tokenPattern = `\\b(?<index_${flaggedTokenId}>${suggestion.flaggedToken})\\b`;
    } else {
      tokenPattern += `|\\b(?<index_${flaggedTokenId}>${suggestion.flaggedToken})\\b`;
    }
  });

  // Return early if no suggestions found
  if (tokenPattern === undefined) {
    return null;
  }

  const tokenRegExp = new RegExp(tokenPattern, "ig");

  const verses = document.getElementsByClassName("verse");

  // Logic to keep the cursor in the same place
  let offset = undefined;
  let anchorVerseElement = undefined;
  if (isRestoreCursor && window.getSelection().type !== "None") {
    anchorVerseElement = window
      .getSelection()
      .getRangeAt(0)
      .startContainer.parentElement.closest("span.verse");
    offset = Cursor.getCurrentCursorPosition(anchorVerseElement);
  }

  [].forEach.call(verses, (verseElement) => {
    // This function gets called repeatedly for
    // every successful match
    const { book, chapter, verse } = verseElement.dataset;
    verseElement.innerHTML = contentState[book][chapter][verse]
      .trim()
      .replaceAll(tokenRegExp, (...args) => {
        // Get last element which is an object
        // with named capture groups: args.pop()
        // See: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/replace#specifying_a_function_as_the_replacement
        const [tokenId, flaggedToken] = Object.entries(args.pop()).find(
          ([tokenId, flaggedToken]) => flaggedToken !== undefined
        );
        return `<span data-flagged-token-id=${tokenId
          .split("_")
          .at(-1)} class="underline flag-red">${flaggedToken}</span>`;
      });
  });

  if (
    isRestoreCursor &&
    offset !== undefined &&
    anchorVerseElement !== undefined &&
    anchorVerseElement !== null
  ) {
    Cursor.setCurrentCursorPosition(offset, anchorVerseElement);
    anchorVerseElement.focus();
  }

  // Add context menu
  const suggestionsMenu = document.getElementById("suggestions-menu");
  const underlinedNodes = document.querySelectorAll(
    "#scripture-content .underline"
  );

  underlinedNodes.forEach((underlinedNode) => {
    underlinedNode.addEventListener("contextmenu", (menuEvent) => {
      menuEvent.preventDefault();

      suggestionsMenu.style.top = `${menuEvent.layerY}px`;
      suggestionsMenu.style.left = `${menuEvent.layerX}px`;

      // Setup and show the menu
      // Clean-up any existing `li` tags in the suggestions-menu
      suggestionsMenu
        .querySelectorAll("li")
        .forEach((liElement) => liElement.remove());

      // Replace flaggedToken with suggestion
      function replaceWithSuggestion(event) {
        menuEvent.target.dataset.replacementToken = event.target.innerText;
        // menuEvent.target.parentNode.replaceChild(
        //   document.createTextNode(event.target.innerText.trim()),
        //   menuEvent.target
        // );
        suggestionsMenu.classList.add("hidden");
      }

      // Add the relevant suggestions to the suggestions-menu
      suggestions[menuEvent.target.dataset.flaggedTokenId].suggestions.forEach(
        (suggestionItem) => {
          const liElement = document.createElement("li");
          liElement.classList.add("menu-item");
          liElement.innerHTML = suggestionItem.suggestion;
          suggestionsMenu.append(liElement);
          liElement.addEventListener("click", replaceWithSuggestion);
        }
      );

      suggestionsMenu.classList.remove("hidden");

      // Hide the suggestionsMenu when clicking outside of it
      function hideMenu(element) {
        const isClickOutsideMenu = !suggestionsMenu.contains(element.target);
        if (isClickOutsideMenu) {
          suggestionsMenu.classList.add("hidden");
        }
      }

      document.addEventListener("click", hideMenu);

      if (suggestionsMenu.classList.contains("hidden")) {
        document.removeEventListener("click", hideMenu);
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  // Initialize state
  let contentState = undefined;
  let suggestions = undefined;
  let resourceId = undefined;

  // Used to hold the chapters for the
  // content that was edited by the user
  let dirtyState = undefined;

  let scriptureContent = document.getElementById("scripture-content");

  // MutationObserver setup

  // MutationObserver 1
  // Observer for handling selected suggestions
  function suggestionsSelectionHandler(mutationList) {
    mutationList.forEach((mutation) => {
      switch (mutation.type) {
        case "attributes":
          switch (mutation.attributeName) {
            // Check if anytime this attribute is set
            // and use it to replace underlined nodes
            // with the user-selected suggestions.
            case "data-replacement-token":
              mutation.target.parentNode.replaceChild(
                document.createTextNode(
                  mutation.target.dataset.replacementToken
                ),
                mutation.target
              );
              updateContent();
              break;
          }
          break;
      }
    });
  }
  new MutationObserver(suggestionsSelectionHandler).observe(scriptureContent, {
    attributeFilter: ["data-replacement-token"],
    attributeOldValue: true,
    subtree: true,
  });

  // MutationObserver 2
  // Options for the observer for keyboard based char edits
  const charEditObserverConfig = {
    characterData: true,
    characterDataOldValue: true,
    subtree: true,
  };

  // Handler for setting dirtyState based on edits
  const setDirtyState = (mutationList, observer) => {
    mutationList.forEach((mutation) => {
      if (mutation.type === "characterData") {
        // Find the closest verse span to get
        // current chapter and verse number
        const { book, chapter, verse } =
          mutation.target.parentElement.closest("span.verse").dataset;
        if (dirtyState === undefined) {
          dirtyState = {};
          dirtyState[book] = { chapters: new Set() };
        }
        dirtyState[book].chapters.add(chapter);
      }
    });
  };

  // Create an observer instance
  const charEditObserver = new MutationObserver(setDirtyState);

  // Method to save the current state of the scripture on screen
  // to the backend. Then refresh and re-render suggestions.
  function updateContent() {
    const verses = document.getElementsByClassName("verse");
    [].forEach.call(verses, (verse) => {
      contentState[verse.dataset.book][verse.dataset.chapter][
        verse.dataset.verse
      ] = verse.innerText.trim();
    });

    // Persist edited data to backend
    setScriptureContent(contentState);

    // Get updated suggestions
    getSuggestions(resourceId, dirtyState).then((updatedSuggestions) => {
      // Merge in the updated
      // suggestions into current state
      suggestions = {
        ...suggestions,
        ...updatedSuggestions,
      };
      // `true` to restore cursor position after highlighting
      highlightTokens(suggestions, contentState, true);

      // Reset dirtyState
      dirtyState = undefined;
    });
  }

  // Apply onclick listener for each of the resource links on the left pane
  const resourceLinks = document.getElementsByClassName("link");
  [].forEach.call(resourceLinks, (link) => {
    link.addEventListener("click", (event) => {
      // Set resourceId state
      resourceId = event.target.dataset.resourceId;

      // Unselect any existing and highlight selected link
      Array.from(document.getElementsByClassName("link underline")).forEach(
        (el) => el.classList.remove("underline")
      );

      // Underline selected resource link
      event.target.classList.add("underline");

      // Get JSON content for internal state management
      // Send formatted=`false` for returning JSON
      getScriptureContent(event.target, false).then((content) => {
        contentState = content;
      });

      // Get HTML scripture content to display on right pane
      getScriptureContent(event.target)
        .then((content) => {
          scriptureContent.innerHTML = content;

          // Start observing the content for
          // text edits to set dirtyState
          charEditObserver.observe(scriptureContent, charEditObserverConfig);

          // Get the suggestions for the text
          return getSuggestions(resourceId);
        })
        .then((suggestionsData) => {
          // Set state
          suggestions = suggestionsData;
          highlightTokens(suggestions, contentState);

          if (!scriptureContent.hasAttribute("inputListener")) {
            scriptureContent.addEventListener(
              "input",
              debounce(updateContent, 3000)
            );
            scriptureContent.setAttribute("inputListener", "true");
          }
        })
        .catch((err) => {
          scriptureContent.innerHTML = err;
        });
    });
  });
});

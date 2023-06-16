// Javascript for the Voithos page

import { debounce } from "./utils.js";

import {
  getScriptureContent,
  setScriptureContent,
  getSuggestions,
  highlightTokens,
} from "./helpers.js";

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

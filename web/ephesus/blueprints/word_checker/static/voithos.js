// Javascript for the Voithos page

function getCursorPosition(editor) {
  if (window.getSelection()) {
    var sel = window.getSelection();
    if (sel.getRangeAt) {
      var pos = sel.getRangeAt(0).startOffset;
      var endPos =
        pos +
        Array.from(editor.innerHTML.slice(0, pos)).length -
        editor.innerHTML.slice(0, pos).split("").length;
      return endPos;
    }
  }
  return null;
}

// Method to get formatted scripture content from the backend
async function getScriptureContent(element, formatted = true) {
  var URL = window.location.origin + element.dataset.url;
  if (formatted) {
    URL += "?formatted=true";
  }

  const response = await fetch(URL);
  if (response.ok) {
    let body = undefined;

    if (formatted) {
      body = await response.text();
    } else {
      body = await response.json();
    }
    return Promise.resolve(body);
  } else {
    return Promise.reject("Unable to retrieve data.");
  }
}

// Method to persist (POST) scriptural content to backend
async function setScriptureContent(contentState) {
  const URL =
    window.location.origin +
    document.getElementsByClassName("link underline")[0].dataset.url;
  console.log(URL);

  const response = await fetch(URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(contentState),
  });

  if (response.ok) {
    body = await response.json();
    return Promise.resolve(body);
  } else {
    return Promise.reject("Error while persisting data.");
  }
}

// Method to serialize HTML to JSON for scripture content
function serializeHTMLToJSON() {
  const verses = document.getElementsByClassName("verse");
  let serializedData = {};
  [].forEach.call(verses, (verse) => {
    // console.log(verse.dataset);
    if (!(verse.dataset.book in serializedData)) {
      serializedData[verse.dataset.book] = {};
    }
    if (!(verse.dataset.chapter in serializedData[verse.dataset.book])) {
      serializedData[verse.dataset.book][verse.dataset.chapter] = {};
    }
    if (
      !(
        verse.dataset.verse in
        serializedData[verse.dataset.book][verse.dataset.chapter]
      )
    ) {
      serializedData[verse.dataset.book][verse.dataset.chapter][
        verse.dataset.verse
      ] = verse.innerHTML;
    }
  });
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
  let URL = `${window.location.origin}/word_checker/api/v1/suggestions/${resourceId}${filterParams}`;

  const response = await fetch(URL);
  if (response.ok) {
    let body = await response.json();
    return Promise.resolve(body);
  } else {
    return Promise.reject("Unable to retrieve data.");
  }
}

// Debounce input
function debounce(task, ms) {
  let t = { promise: null, cancel: (_) => void 0 };
  return async (...args) => {
    try {
      t.cancel();
      t = deferred(ms);
      await t.promise;
      await task(...args);
    } catch (_) {
      //console.log("cleaning up cancelled promise");
    }
  };
}

function deferred(ms) {
  let cancel,
    promise = new Promise((resolve, reject) => {
      cancel = reject;
      setTimeout(resolve, ms);
    });
  return { promise, cancel };
}

// Method to highlight (underline) flaggedTokens in the UI
// and add capability to show context menu with suggestions
function highlightTokens(suggestions, contentState) {
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
  // console.log(tokenPattern);
  tokenRegExp = new RegExp(tokenPattern, "ig");

  const verses = document.getElementsByClassName("verse");
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
        [tokenId, flaggedToken] = Object.entries(args.pop()).find(
          ([tokenId, flaggedToken]) => flaggedToken !== undefined
        );
        return `<span data-flagged-token-id=${tokenId
          .split("_")
          .at(-1)} class="underline flag-red">${flaggedToken}</span>`;
      });
  });

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
      ////  Clean-up any existing `li` tags in the suggestions-menu
      suggestionsMenu
        .querySelectorAll("li")
        .forEach((liElement) => liElement.remove());
      //// Add the relevant suggestions to the suggestions-menu
      suggestions[menuEvent.target.dataset.flaggedTokenId].suggestions.forEach(
        (suggestionItem) => {
          liElement = document.createElement("li");
          liElement.classList.add("menu-item");
          liElement.innerHTML = suggestionItem.suggestion;
          suggestionsMenu.append(liElement);
        }
      );

      suggestionsMenu.classList.remove("hidden");

      // Hide the suggestionsMenu when clicking outside of it
      document.addEventListener("click", (element) => {
        const isClickedOutside = !suggestionsMenu.contains(element.target);
        if (isClickedOutside) {
          suggestionsMenu.classList.add("hidden");
          document.removeEventListener("click", arguments.callee);
        }
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  // Initialize state
  let contentState = undefined;
  let suggestions = undefined;
  let resourceId = undefined;

  // Used to hold the chapters and verses for
  // the content that were edited by the user
  let dirtyState = undefined;

  let scriptureContent = document.getElementById("scripture-content");

  // Options for the observer (which mutations to observe)
  const observerConfig = {
    characterData: true,
    characterDataOldValue: true,
    subtree: true,
  };

  // Callback function to execute when mutations are observed
  const callback = (mutationList, observer) => {
    console.log(mutationList);
    mutationList.forEach((mutation) => {
      console.log(
        getCursorPosition(mutation.target.parentElement.closest("span.verse"))
      );
      // Find the closest verse span to get
      // current chapter and verse number
      const { book, chapter, verse } =
        mutation.target.parentElement.closest("span.verse").dataset;
      if (dirtyState === undefined) {
        dirtyState = {};
        dirtyState[book] = { chapters: new Set() };
      }
      dirtyState[book].chapters.add(chapter);
    });
    // for (const mutation of mutationList) {
    //   if (mutation.type === "childList") {
    //     console.log("Spotted an underline.");
    //     // console.log(mutation.addedNodes[1]);
    //     for (const node of mutation.addedNodes) {
    //       addContextMenu(node, "confidint");
    //       // if (node instanceof Element) {
    //       //   addContextMenu(node, "jesus christ");
    //       // }
    //     }
    //   }
    //}
  };

  // Create an observer instance linked to the callback function
  const observer = new MutationObserver(callback);

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
      getScriptureContent(event.target, false)
        .then((content) => {
          contentState = content;
        })
        .then(() => {
          console.log(contentState);
        });

      // Get HTML scripture content to display on right pane
      getScriptureContent(event.target)
        .then((content) => {
          scriptureContent.innerHTML = content;

          // Start observing the target node for configured mutations
          observer.observe(scriptureContent, observerConfig);

          return getSuggestions(resourceId);
        })
        .then((suggestionsData) => {
          suggestions = suggestionsData;
          console.log(suggestions);
          highlightTokens(suggestions, contentState);

          // Apply onblur listeners for each verse for writing to backend

          document.getElementById("scripture-content").addEventListener(
            "input",
            debounce((event) => {
              const verses = document.getElementsByClassName("verse");
              [].forEach.call(verses, (verse) => {
                contentState[verse.dataset.book][verse.dataset.chapter][
                  verse.dataset.verse
                ] = verse.innerText.trim();
              });

              // Persist data to backend
              setScriptureContent(contentState);

              getSuggestions(resourceId, dirtyState).then(
                (updatedSuggestionsData) => {
                  suggestions = {
                    ...suggestionsData,
                    ...updatedSuggestionsData,
                  };
                  console.log(suggestions);
                  highlightTokens(suggestions, contentState);

                  // Reset dirtyState
                  dirtyState = undefined;
                }
              );
            }, 3000)
          );
        })
        .catch((err) => {
          scriptureContent.innerHTML = err;
        });
    });
  });
});

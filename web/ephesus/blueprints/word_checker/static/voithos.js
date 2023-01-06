// Javascript for the Voithos page

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
async function getSuggestions(element) {
  var URL = window.location.origin + "/word_checker/api/v1/suggestions/" + element.dataset.resourceId;
  //var URL = window.location.origin + element.dataset.url;

  const response = await fetch(URL);
  if (response.ok) {
    let body = await response.json();
    return Promise.resolve(body);
  } else {
    return Promise.reject("Unable to retrieve data.");
  }
}

async function getSpellingSuggestions(resourceId) {
  let url = "api/v1/spell-checker";

  try {
    let res = await fetch(url);
    return await res.json();
  } catch (error) {
    console.log(error);
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

document.addEventListener("DOMContentLoaded", () => {
  // Initialize state
  let contentState = undefined;

  // Apply onclick listener for each of the resource links on the left pane
  const resourceLinks = document.getElementsByClassName("link");
  [].forEach.call(resourceLinks, (link) => {
    link.addEventListener("click", (event) => {
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
        .then(content => {
          let scriptureContent = document.getElementById("scripture-content");
          scriptureContent.innerHTML = content;
          return getSuggestions(event.target);
        })
        .then(suggestions => {

          console.log(suggestions);

          // Apply onblur listeners for each verse for writing to backend
          const verses = document.getElementsByClassName("verse");
          [].forEach.call(verses, (verse) => {
            verse.addEventListener(
              "input",
              debounce((event) => {
                contentState[event.target.dataset.book][
                  event.target.dataset.chapter
                ][event.target.dataset.verse] = event.target.innerHTML.trim();

                // Persist data to backend
                setScriptureContent(contentState);
              }, 3000)
            );
          });
        })
        .catch((err) => {
          let scriptureContent = document.getElementById("scripture-content");
          scriptureContent.innerHTML = err;
        });
    });
  });
});

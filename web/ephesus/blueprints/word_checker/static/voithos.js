// Method to get formatted scripture content from the backend
async function getScriptureContent(element) {
  const baseURL = window.location.origin;
  const URL = baseURL + element.dataset.url;

  const response = await fetch(URL);
  if (response.ok) {
    const body = await response.text();
    return Promise.resolve(body);
  } else {
    return Promise.reject("Unable to retrieve data.");
  }
}

// Method to serialize HTML to JSON for scripture content
function serializeHTMLToJSON(rootElement) {
  const verses = rootElement.getElementsByClassName("verse");
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

  console.log(serializedData);
}

document.addEventListener("DOMContentLoaded", () => {
  // Apply onclick listener for each of the resource links on the left pane
  resourceLinks = document.getElementsByClassName("link");
  [].forEach.call(resourceLinks, (link) => {
    link.addEventListener("click", (event) => {
      getScriptureContent(event.target)
        .then((content) => {
          let scriptureContent = document.getElementById("scripture-content");
          scriptureContent.innerHTML = content;

          serializeHTMLToJSON(scriptureContent);
        })
        .catch((err) => {
          let scriptureContent = document.getElementById("scripture-content");
          scriptureContent.innerHTML = err;
        });
    });
  });
});

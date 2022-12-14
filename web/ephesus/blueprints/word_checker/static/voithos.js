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

document.addEventListener("DOMContentLoaded", () => {
  // Apply onclick listener for each of the resource links on the left pane
  resourceLinks = document.getElementsByClassName("link");
  [].forEach.call(resourceLinks, (link) => {
    link.addEventListener("click", (event) => {
      getScriptureContent(event.target)
        .then((content) => {
          let scriptureContent = document.getElementById("scripture-content");
          scriptureContent.innerHTML = content;
        })
        .catch((err) => {
          let scriptureContent = document.getElementById("scripture-content");
          scriptureContent.innerHTML = err;
        });
    });
  });
});

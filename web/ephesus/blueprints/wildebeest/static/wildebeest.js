console.log("Welcome to the wildebeest blueprint!");

// Method to get formatted Wildebeest analysis output from the backend
export async function getWildebeestAnalysis(element, formatted = true) {
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
    return Promise.reject("Unable to retrieve wildebeest analaysis data.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  let analysisContent = document.getElementById("analysis-content");
  // Apply onclick listener for each of the resource links on the left pane
  const resourceLinks = document.getElementsByClassName("link");
  [].forEach.call(resourceLinks, (link) => {
    link.addEventListener("click", (event) => {
      console.log(event.target.dataset);
      // Set resourceId state
      const resourceId = event.target.dataset.resourceId;

      // Unselect any existing and highlight selected link
      Array.from(document.getElementsByClassName("link underline")).forEach(
        (el) => el.classList.remove("underline")
      );

      // Underline selected resource link
      event.target.classList.add("underline");

      // Get HTML Wildebeest analysis content to display on right pane
      getWildebeestAnalysis(event.target).then((content) => {
        analysisContent.innerHTML = content;
      });
    });
  });
});

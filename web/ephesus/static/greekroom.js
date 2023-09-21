console.log("καλωσορίσατε στο ελληνικό δωμάτιο!");

// Method to get formatted Wildebeest analysis output from the backend
export async function getDataFromElementURL(element, params) {
  var URL =
    params === undefined
      ? window.location.origin + element.dataset.url
      : window.location.origin + element.dataset.url + params;

  const response = await fetch(URL);
  if (response.ok) {
    let data = undefined;

    data = await response.text();
    return Promise.resolve(data);
  } else {
    return Promise.reject("Unable to retrieve project overview data.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const projectsListing = document.querySelector(".listing");
  const detailsPane = document.getElementById("details-pane");

  // Parent event listener for the left pane
  projectsListing.addEventListener("click", (event) => {
    // Apply onclick listener for the project links in the left pane
    const linkTarget = event.target.closest(".link");
    if (linkTarget) {
      // Set resourceId state
      const resourceId = linkTarget.dataset.resourceId;

      // Unselect any existing and highlight selected link
      Array.from(document.getElementsByClassName("link underline")).forEach(
        (el) => el.classList.remove("underline")
      );

      // Underline selected resource link
      linkTarget.classList.add("underline");

      // Get HTML Wildebeest analysis content to display on right pane
      getDataFromElementURL(linkTarget).then((content) => {
        detailsPane.innerHTML = content;
      });
    }
  });

  // Parent even listener for the right pane
  detailsPane.addEventListener("click", (event) => {
    // Apply onclick listener for the analysis results links in the right pane
    const linkTarget = event.target.closest(".link");
    if (linkTarget) {
      console.log(linkTarget.dataset);
      // Set resourceId state
      const resourceId = linkTarget.dataset.resourceId;

      // Get HTML Wildebeest analysis content to display on right pane
      getDataFromElementURL(linkTarget).then((content) => {
        detailsPane.innerHTML = content;
      });
    }
  });
});

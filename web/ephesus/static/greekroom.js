console.log("Welcome to the Greek Room!");

// Method to get formatted Wildebeest analysis output from the backend
export async function getProjectOverview(element) {
  var URL = window.location.origin + element.dataset.url;

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
  let detailsPane = document.getElementById("details-pane");

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
      getProjectOverview(event.target).then((content) => {
        detailsPane.innerHTML = content;
      });
    });
  });
});

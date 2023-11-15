console.log("καλωσορίσατε στο ελληνικό δωμάτιο!");

// Method to get formatted Wildebeest analysis output from the backend
export async function getDataFromElementURL(element, params) {
  var URL =
    params === undefined ? element.dataset.url : element.dataset.url + params;

  const response = await fetch(URL);
  if (response.ok) {
    let data = undefined;

    data = await response.text();
    return Promise.resolve(data);
  } else {
    return Promise.reject("Unable to retrieve project overview data.");
  }
}

// Method to post data to backend
export async function postForm(formElement) {
  const response = await fetch(formElement.action, {
    method: "POST",
    body: new FormData(formElement),
  });
  if (response.status === 201) {
    let data = undefined;
    data = await response.json();
    return Promise.resolve(data);
  } else if (response.status === 500) {
    let data = undefined;
    data = await response.json();
    return Promise.reject(data);
  } else {
    return Promise.reject(
      "There was an error while processing this request. Please try again."
    );
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

  // Parent event listener for the right pane
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

  // Event listener for create project form submission
  document
    .querySelector("#createPopup form")
    .addEventListener("submit", (event) => {
      event.preventDefault();
      // TODO do something here to show user that form is being submitted
      document.querySelector("input.create").style.display = "none";
      document.querySelector("img.create").style.display = "";
      // Post form
      postForm(event.target).then((responseData) => {
        console.log(responseData);
        document.querySelector("img.create").style.display = "none";
        // Show response
        document.querySelector("#form-notification > b").innerHTML =
          responseData.message;
        document.querySelector("#form-notification").style.display = "";
        // Refresh page
        setTimeout(() => {
          location.replace(location.pathname);
        }, 3000);
      });
    });
});

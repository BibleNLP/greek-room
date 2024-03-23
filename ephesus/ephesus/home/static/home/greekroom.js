console.log("καλωσορίσατε στο ελληνικό δωμάτιο!");

// Generic method to callout to the backend and return results
export async function getDataFromElementURL(element, params) {
  var URL =
    params === undefined
      ? element.dataset.url
      : `${element.dataset.url}?${params}`;

  const response = await fetch(URL);
  if (response.ok) {
    let data = undefined;

    data = await response.text();
    return Promise.resolve(data);
  } else {
    return Promise.reject("Unable to retrieve data.");
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
    if (response.headers.get("content-type") === "application/json") {
      data = await response.json();
    } else {
      data = {
        detail:
          "There was an error while processing this request. Please try again.",
      };
    }
    return Promise.reject(data);
  } else {
    return Promise.reject(
      "There was an error while processing this request. Please try again."
    );
  }
}

// Method to setInnerHTML but with <script> tags
// that actually run on the page
export function setInnerHtml(elm, html) {
  elm.innerHTML = html;
  Array.from(elm.querySelectorAll("script")).forEach((oldScript) => {
    const newScript = document.createElement("script");
    Array.from(oldScript.attributes).forEach((attr) =>
      newScript.setAttribute(attr.name, attr.value)
    );
    newScript.appendChild(document.createTextNode(oldScript.innerHTML));
    oldScript.parentNode.replaceChild(newScript, oldScript);
  });
}

export async function showInfoPopup(title, message) {
  const infoPopup = document.getElementById("info-popup");
  document.querySelector('#info-popup h3[role="title"]').innerHTML = title;
  document.querySelector('#info-popup p[role="message"]').innerHTML = message;
  infoPopup.showModal();

  // "OK" button closes the dialog
  document
    .querySelector('#info-popup button[role="confirm"]')
    .addEventListener("click", () => {
      infoPopup.close();
    });
}

export async function closeInfoPopup() {
  const infoPopup = document.getElementById("info-popup");
  infoPopup.close();
}

// Method to send delete request
export async function deleteRequest(url) {
  const response = await fetch(url, {
    method: "DELETE",
  });
  if (response.status === 200) {
    let data = undefined;
    data = await response.json();
    return Promise.resolve(data);
  } else if (response.status === 500 || response.status === 403) {
    let data = undefined;
    if (response.headers.get("content-type") === "application/json") {
      data = await response.json();
    } else {
      data = {
        detail:
          "There was an error while processing this request. Please try again.",
      };
    }
    return Promise.reject(data);
  } else {
    return Promise.reject({
      detail:
        "There was an error while processing this request. Please try again.",
    });
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

      // Get project overview content to display on right pane
      getDataFromElementURL(linkTarget).then(
        (content) => {
          setInnerHtml(detailsPane, content);
          // detailsPane.innerHTML = content;
        },
        (reason) => {
          detailsPane.innerHTML =
            "There was an error while fetching the project data. Try again.";
        }
      );
    }
  });

  // Handle delete popup actions
  const deletePopup = document.getElementById("deletePopup");
  const deleteCancelButton = document.querySelector(
    '#deletePopup button[role="close"]'
  );
  const deleteConfirmButton = document.querySelector(
    '#deletePopup button[role="confirm"]'
  );
  var deleteEndpoint = {};

  // Function to handle the results after DeleteProject
  function handleDeleteProjectResult(responseData) {
    document.querySelector("#deletePopup .flex").style.display = "none";
    // Show response
    document.querySelector(
      '#deletePopup p[role="notification"] > b'
    ).innerHTML = responseData.detail;
    document.querySelector(
      '#deletePopup p[role="notification"]'
    ).style.display = "";

    // Refresh page
    setTimeout(() => {
      location.replace(location.pathname);
    }, 3000);
  }

  deleteCancelButton.addEventListener("click", (event) => {
    deletePopup.close();
  });

  deleteConfirmButton.addEventListener("click", (event) => {
    if ("deleteEndpoint" in deleteEndpoint) {
      document.querySelector(
        '#deletePopup button[role="close"]'
      ).style.display = "none";
      document.querySelector(
        '#deletePopup button[role="confirm"]'
      ).style.display = "none";
      document.querySelector('#deletePopup img[role="loader"]').style.display =
        "";
      deleteRequest(deleteEndpoint.deleteEndpoint).then(
        (responseData) => {
          handleDeleteProjectResult(responseData);
        },
        (reason) => {
          handleDeleteProjectResult(reason);
        }
      );
    }
  });

  // Parent event listener for the right pane
  detailsPane.addEventListener("click", (event) => {
    // Apply onClick listener for the analysis results links in the right pane
    const linkTarget = event.target.closest(".link");
    if (linkTarget) {
      // Set resourceId state
      const resourceId = linkTarget.dataset.resourceId;

      // Show loader
      detailsPane.classList.add("cursor-wait");
      linkTarget.classList.add("hide");
      linkTarget.nextElementSibling.classList.remove("hide");

      // - Get HTML Wildebeest analysis content
      // - Get HTML Spell checking analysis content
      getDataFromElementURL(linkTarget).then(
        (content) => {
          detailsPane.classList.remove("cursor-wait");
          setInnerHtml(detailsPane, content);
        },
        (reason) => {
          detailsPane.classList.remove("cursor-wait");
          detailsPane.innerHTML =
            "There was an error while processing the request. Try again.";
        }
      );
      return;
    }

    // Apply onClick listener for delete button
    const deleteIcon = event.target.closest('img[role="delete-project"]');
    if (deleteIcon) {
      deleteEndpoint = { deleteEndpoint: deleteIcon.dataset.url };
      deletePopup.showModal();

      return;
    }

    // Apply onClick listener for Wildebeest download button
    const wildebeestDownloadIcon = event.target.closest(
      'img[role="wildebeest-download"]'
    );
    if (wildebeestDownloadIcon) {
      const downloadHandle = window.open(
        wildebeestDownloadIcon.dataset.url,
        "GreekRoomContext"
      );
      if (!downloadHandle) {
        // Handle download error
        showInfoPopup(
          "Wildebeest Download Error",
          "There was an error while attempting to download the Wildebeest analysis report. Please try again."
        );
      } else {
        // noop if download was successful
      }
      return;
    }
  });

  // Function to handle the results after CreateProject
  function handleCreateProjectFormResult(responseData) {
    document.querySelector("img.create").style.display = "none";
    // Show response
    document.querySelector("#form-notification > b").innerHTML =
      responseData.detail;
    document.querySelector("#form-notification").style.display = "";
    // Refresh page
    setTimeout(() => {
      location.replace(location.pathname);
    }, 4000);
  }

  // Event listener for create project form submission
  document
    .querySelector("#createPopup form")
    .addEventListener("submit", (event) => {
      event.preventDefault();
      // Show loader
      document.querySelector("input.create").style.display = "none";
      document.querySelector("img.create").style.display = "";
      // Post form
      postForm(event.target).then(
        (responseData) => {
          handleCreateProjectFormResult(responseData);
        },
        (reason) => {
          handleCreateProjectFormResult(reason);
        }
      );
    });
});

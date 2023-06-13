// Check if the re-entered passwords match
function isPasswordMatched(reenterPassword) {
  password1 = document.getElementsByName("password")[0].value;
  password2 = document.getElementsByName("reenter-password")[0].value;

  if (password1 === password2) {
    reenterPassword.setCustomValidity("");
  } else {
    reenterPassword.setCustomValidity("Passwords do not match.");
  }
  reenterPassword.reportValidity();
}

// Configure and show edit roles popup
const editRolesLink = document.getElementsByClassName("link");

[].forEach.call(editRolesLink, (link) => {
  link.addEventListener("click", (event) => {
    document.querySelector("#edit-roles label > b").innerText =
      event.target.dataset.username;
    document.querySelector("#edit-roles input[name=name]").value =
      event.target.dataset.roles;

    document.querySelector(
      "#edit-roles .submit"
    ).dataset.url = `${window.location.origin}${window.location.pathname}/${event.target.dataset.username}/roles`;

    window.location.hash = "edit-roles";
    return false;
  });
});

// Async call to update user role
async function updateRoles(URL, roles) {
  const response = await fetch(URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: roles,
  });

  if (response.status === 204) {
    return Promise.resolve();
  } else if (response.ok) {
    let data = await response.json();
    return Promise.resolve(data);
  } else {
    return Promise.reject("Error while persisting data.");
  }
}

// Update user role button press
const updateRoleButton = document.getElementsByClassName("submit")[0];

updateRoleButton.addEventListener("click", (event) => {
  updateRoles(
    event.target.dataset.url,
    document.querySelector("#edit-roles input[name=name]").value
  )
    .then((response) => {
      window.location.href = `${window.location.origin}${window.location.pathname}?showRolesSuccess=true`;
    })
    .catch((err) => {
      console.log(err);
      window.location.href = `${window.location.origin}${window.location.pathname}?showRolesFailure=true`;
    });
});

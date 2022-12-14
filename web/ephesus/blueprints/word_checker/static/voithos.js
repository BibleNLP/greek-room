async function getScriptureContent(formatted = true) {
  const baseURL =
    window.location.origin +
    "/" +
    window.location.pathname.slice(1).split("/")[0];
  let URL = baseURL + "/api/v1/scripture/9Qvsvb27";
  if (formatted) {
    URL += "?formatted=true";
  }

  const response = await fetch(URL);
  if (response.ok) {
    const body = await response.text();
    return Promise.resolve(body);
  } else {
    return Promise.reject("Unable to retrieve data.");
  }
}

document.addEventListener("DOMContentLoaded", function () {
  getScriptureContent()
    .then((content) => {
      let scriptureContent = document.getElementById("scripture-content");
      scriptureContent.innerHTML = content;
    })
    .catch((err) => {
      let scriptureContent = document.getElementById("scripture-content");
      scriptureContent.innerHTML = err;
    });
});

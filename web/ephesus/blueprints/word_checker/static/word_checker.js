async function getSpellingSuggestions() {
  let url = "api/v1/spell-checker";

  try {
    let res = await fetch(url);
    return await res.json();
  } catch (error) {
    console.log(error);
  }
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function underlineText(text, tokens, color = "red") {
  escaped_tokens = escapeRegExp(tokens);
  const regexp = new RegExp("\\b" + `${escaped_tokens}` + "\\b", "gi");
  let matches = text.matchAll(regexp);
  let underlinedText = "";
  let startIndices = Array.from(matches, (match) => match.index);

  if (startIndices.length == 0 || startIndices.includes(undefined)) {
    return undefined;
  }

  const original_tokens = text.substring(
    startIndices[0],
    startIndices[0] + tokens.length
  );

  for (let j = 0; j < startIndices.length; j++) {
    if (j === startIndices.length - 1) {
      underlinedText +=
        '<span class="underline ' +
        `${color}` +
        '">' +
        original_tokens +
        "</span>" +
        text.substring(startIndices[j] + tokens.length);
    } else {
      underlinedText +=
        '<span class="underline ' +
        `${color}` +
        '">' +
        original_tokens +
        "</span>" +
        text.substring(startIndices[j] + tokens.length, startIndices[j + 1]);
    }
  }
  underlinedText = text.substring(0, startIndices[0]) + underlinedText;
  return underlinedText;
}

// const ele = document.getElementById('element');
const menu = document.getElementById("menu");

// Hide the menu when clicking outside of it
const documentClickHandler = function (e) {
  const isClickedOutside = !menu.contains(e.target);
  if (isClickedOutside) {
    menu.classList.add("hidden");
    document.removeEventListener("click", documentClickHandler);
  }
};

function addContextMenu(node, tokens) {
  if (!(node instanceof Element)) {
    return undefined;
  }

  console.log(node);
  let text = node.innerText || node.textContent;
  if (text.toLowerCase() === tokens.toLowerCase()) {
    node.addEventListener("contextmenu", function (e) {
      e.preventDefault();

      menu.style.top = `${e.layerY}px`;
      menu.style.left = `${e.layerX}px`;

      // Show the menu
      menu.classList.remove("hidden");

      document.addEventListener("click", documentClickHandler);
    });
  }
}

// Taken from https://htmldom.dev/show-a-custom-context-menu-at-clicked-position/
document.addEventListener("DOMContentLoaded", function () {
  let scriptureContent = document.getElementById("scripture-content");

  // Options for the observer (which mutations to observe)
  const observerConfig = { childList: true, subtree: true };

  // Callback function to execute when mutations are observed
  const callback = (mutationList, observer) => {
    for (const mutation of mutationList) {
      if (mutation.type === "childList") {
        console.log("Spotted an underline.");
        // console.log(mutation.addedNodes[1]);
        for (const node of mutation.addedNodes) {
          addContextMenu(node, "jesus christ");
          // if (node instanceof Element) {
          //   addContextMenu(node, "jesus christ");
          // }
        }
      }
    }
  };

  // Create an observer instance linked to the callback function
  const observer = new MutationObserver(callback);

  // Start observing the target node for configured mutations
  observer.observe(scriptureContent, observerConfig);

  // Later, you can stop observing
  // observer.disconnect();

  let verseElements = document.getElementsByClassName("verse");
  for (let i = 0; i < verseElements.length; i++) {
    // console.log(verseElements[i].innerHTML);

    let text = verseElements[i].innerText || element.textContent;
    // underlineText(text, 'of')

    replacement = underlineText(text, "jesus christ");
    if (replacement !== undefined) {
      verseElements[i].innerHTML = replacement;
    }
  }

  async function Suggestions() {
    suggestions = await getSpellingSuggestions();
    console.log(suggestions);
  }

  // logSuggestions();
  // // Url for the request
  //   var url = 'api/v1/spell-checker';

  // // Making our request
  // fetch(url, { method: 'GET' })
  //   .then(Result => { Result.json() })
  //   .then(string => {

  //     // Printing our response
  //     console.log(string);

  //     // Printing our field of our response
  //     //console.log(`Title of our response :  ${string.title}`);
  //   })
  //   .catch(errorMsg => { console.log(errorMsg); });
});

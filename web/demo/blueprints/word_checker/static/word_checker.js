

async function getSpellingSuggestions() {
  let url = 'api/v1/spell-checker';

  try {
    let res = await fetch(url);
    return await res.json();
  } catch (error) {
    console.log(error);
  }
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function underlineText(text, tokens, color="red") {
  escaped_tokens = escapeRegExp(tokens);
  const regexp = new RegExp('\\b'+`${escaped_tokens}` + '\\b', 'gi');
  let matches = text.matchAll(regexp);
  let underlinedText = '';
  let startIndices = Array.from(matches, (match) => match.index);

  if (startIndices.length == 0 || startIndices.includes(undefined)) {
    return text;
  }

  for (let j=0; j<startIndices.length; j++) {
    if (j===startIndices.length-1) {
      underlinedText += '<span class="underline ' + `${color}` + '">' + tokens + '</span>' + text.substring(startIndices[j]+tokens.length);
    } else {
      underlinedText += '<span class="underline ' + `${color}` + '">' + tokens + '</span>' + text.substring(startIndices[j]+tokens.length, startIndices[j+1]);
    }
  }
  underlinedText = text.substring(0, startIndices[0]) + underlinedText;
  return underlinedText;
}

// Taken from https://htmldom.dev/show-a-custom-context-menu-at-clicked-position/
document.addEventListener('DOMContentLoaded', function () {
  let elements = document.getElementsByClassName("verse");

  for (let i = 0; i < elements.length; i++) {
    // console.log(elements[i].innerHTML);

    let text = elements[i].innerText || element.textContent;
    // underlineText(text, 'of')

    elements[i].innerHTML = underlineText(text, 'jesus christ');

    elements[i].addEventListener('contextmenu', function (e) {
      e.preventDefault();

      const rect = elements[i].getBoundingClientRect();
      const x = e.clientX - rect.left;
      // const y = e.clientY - rect.top;

      // Set the position for menu
      menu.style.top = `${e.layerY}px`;
      menu.style.left = `${x}px`;

      // Show the menu
      menu.classList.remove('hidden');

      document.addEventListener('click', documentClickHandler);


    });
  }

  // const ele = document.getElementById('element');
  const menu = document.getElementById('menu');

  // Hide the menu when clicking outside of it
  const documentClickHandler = function (e) {
    const isClickedOutside = !menu.contains(e.target);
    if (isClickedOutside) {
      menu.classList.add('hidden');
      document.removeEventListener('click', documentClickHandler);
    }
  };

  async function Suggestions() {
    suggestions = await getSpellingSuggestions();
    console.log(suggestions)
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

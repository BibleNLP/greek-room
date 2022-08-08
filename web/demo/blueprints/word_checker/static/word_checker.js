// Taken from https://htmldom.dev/show-a-custom-context-menu-at-clicked-position/
document.addEventListener('DOMContentLoaded', function () {
  let elements = document.getElementsByClassName("verse");

  for (let i = 0; i < elements.length; i++) {
    // console.log(elements[i].innerHTML);
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
});

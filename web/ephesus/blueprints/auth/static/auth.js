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

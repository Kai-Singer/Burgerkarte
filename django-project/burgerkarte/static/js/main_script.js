document.addEventListener("DOMContentLoaded", () => {
  const navbarImgs = document.querySelectorAll('.navbar .navbar_item img');
  if (navbarImgs.length != 0) {
    const navbarImgsAmount = navbarImgs.length;
  
    navbarImgs.forEach((img, index) => {
      img.src = `${staticHamburgerPrefix}hamburger_${navbarImgsAmount}${index + 1}.png`;
    });
  
    const navbarHideButton = document.querySelector(".navbar_hide_button");
    const navbarShowButton = document.querySelector(".navbar_show_button");
    const navbar = document.querySelector(".navbar");
  
    if (window.innerWidth <= 768) {
      navbar.classList.add("hidden");
      navbar.classList.remove("shown");
    } else {
      navbar.classList.remove("hidden");
      navbar.classList.add("shown");
    }
  
    navbarHideButton.addEventListener("click", () => {
      navbar.classList.remove("hover_effect");
      navbar.classList.add("hidden");
      navbar.classList.remove("shown");
    });
  
    navbarShowButton.addEventListener("click", () => {
      navbar.classList.remove("hidden");
      navbar.classList.add("shown");
      setTimeout(() => {
        navbar.classList.add("hover_effect");
      }, 500);
    });
  
    const usermenuButton = document.querySelector('.usermenu_show_button');
    const usermenu = document.querySelector('.usermenu');
  
    usermenuButton.addEventListener('click', () => {
      usermenu.classList.toggle('shown');
    });
  }
  const messages = document.getElementsByClassName("message");
  for (let i = 0; i < messages.length; i++) {
    messages[i].classList.remove("hidden");
    setTimeout(() => {
      messages[i].classList.add("hidden");
      setTimeout(() => messages[0].remove(), 500);
    }, 5000);
  }
});

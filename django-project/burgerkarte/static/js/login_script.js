function updateBurger() {
  const layersData = [
    { field: document.getElementById('vorname').value, object: document.getElementById('bottom-bun') },
    { field: document.getElementById('nachname').value, object: document.getElementById('top-bun') },
    { field: document.getElementById('email').value, object: document.getElementById('patty') },
    { field: document.getElementById('password').value, object: document.getElementById('kaese') },
    { field: document.getElementById('geburtsdatum').value, object: document.getElementById('salat') },
    { field: document.getElementById('strasse').value, object: document.getElementById('tomate') },
    { field: document.getElementById('hausnummer').value, object: document.getElementById('tomate') },
    { field: document.getElementById('plz').value, object: document.getElementById('tomate') },
    { field: document.getElementById('ort').value, object: document.getElementById('tomate') },
  ];

  layersData.forEach(layerInfo => {
    if (layerInfo.field && !layerInfo.object.classList.contains('burger_shown')) {
      layerInfo.object.classList.add('burger_shown');
    } else if (!layerInfo.field && layerInfo.object.classList.contains('burger_shown')) {
      layerInfo.object.classList.remove('burger_shown');
    }
  });
}

function resetRegisterForm() {
  document.getElementById('register-form').reset();
  updateBurger();
}
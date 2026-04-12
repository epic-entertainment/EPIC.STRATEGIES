const PAGE_BACKGROUNDS = [
  "/assets/backgrounds/11.png",
  "/assets/backgrounds/22.png",
  "/assets/backgrounds/33.png",
  "/assets/backgrounds/44.png"
];

function pickRandomBackground() {
  const index = Math.floor(Math.random() * PAGE_BACKGROUNDS.length);
  return PAGE_BACKGROUNDS[index];
}

function applyPageBackground() {
  const bg = pickRandomBackground();

  document.body.style.backgroundImage = `url('${bg}')`;
  document.body.style.backgroundSize = "cover";
  document.body.style.backgroundPosition = "center";
  document.body.style.backgroundRepeat = "no-repeat";
}

function applyGameSessionBackground() {
  let savedBg = sessionStorage.getItem("gameSessionBackground");

  if (!savedBg) {
    savedBg = pickRandomBackground();
    sessionStorage.setItem("gameSessionBackground", savedBg);
  }

  document.body.style.backgroundImage = `url('${savedBg}')`;
  document.body.style.backgroundSize = "cover";
  document.body.style.backgroundPosition = "center";
  document.body.style.backgroundRepeat = "no-repeat";
}

document.addEventListener("DOMContentLoaded", () => {
  const mode = document.body.dataset.bgMode;

  if (mode === "game-session") {
    applyGameSessionBackground();
  } else {
    applyPageBackground();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("games-container");

  // Если на странице нет нужного контейнера, прекращаем выполнение
  if (!container) return;

  fetch("playtime/games.json")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Err: ${response.status}`);
      }
      return response.json();
    })
    .then((games) => {
      games.sort((a, b) => b.playtime - a.playtime);

      container.innerHTML = games
        .map((game) => {
          const bannerUrl = game.appid
            ? `https://cdn.cloudflare.steamstatic.com/steam/apps/${game.appid}/header.jpg`
            : "https://via.placeholder.com/460x215?text=No+Cover";

          return `
            <div class="game-card" id="game-${game.id}">
              <img 
                class="game-banner" 
                src="${bannerUrl}" 
                alt="${game.name}" 
                loading="lazy"
              />
              <div class="game-info">
                <span class="game-title" title="${game.name}">${game.name}</span>
                <span class="game-hours">${game.playtime} hrs</span>
                <span class="game-description">${game.description}</span>
              </div>
            </div>
          `;
        })
        .join("");
    })
    .catch((error) => {
      console.error("Err:", error);
      container.innerHTML = `<p class="games-error">Err</p>`;
    });
});
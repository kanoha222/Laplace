/**
 * Laplace Demo — App Logic
 *
 * 加载预处理的从者 JSON 数据，
 * 实现客户端筛选/搜索并渲染从者卡片。
 */

const DATA_URL = "data/servants_np_charge.json";

// === State ===
let allServants = [];
let filteredServants = [];
let classOptions = new Set();

// === DOM References ===
const countDisplay = document.getElementById("count-display");
const cardsGrid = document.getElementById("cards-grid");
const loading = document.getElementById("loading");
const noResults = document.getElementById("no-results");
const filterClass = document.getElementById("filter-class");
const filterRarity = document.getElementById("filter-rarity");
const filterSearch = document.getElementById("filter-search");

// === Class Display Names ===
const CLASS_NAMES = {
  saber: "Saber",
  archer: "Archer",
  lancer: "Lancer",
  rider: "Rider",
  caster: "Caster",
  assassin: "Assassin",
  berserker: "Berserker",
  ruler: "Ruler",
  avenger: "Avenger",
  moonCancer: "Moon Cancer",
  alterEgo: "Alter Ego",
  foreigner: "Foreigner",
  pretender: "Pretender",
  shielder: "Shielder",
  beast: "Beast",
};

// === Initialize ===
async function init() {
  try {
    const resp = await fetch(DATA_URL);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const data = await resp.json();
    allServants = data.servants || [];

    // Collect unique classes
    allServants.forEach((s) => classOptions.add(s.className));
    populateClassFilter();

    // Initial render
    applyFilters();

    loading.style.display = "none";
  } catch (err) {
    console.error("Failed to load data:", err);
    loading.innerHTML = `<p style="color:#ff6b6b;">数据加载失败: ${err.message}</p>`;
  }
}

// === Populate Class Filter ===
function populateClassFilter() {
  const sorted = [...classOptions].sort((a, b) => {
    const order = Object.keys(CLASS_NAMES);
    return order.indexOf(a) - order.indexOf(b);
  });

  sorted.forEach((cls) => {
    const opt = document.createElement("option");
    opt.value = cls;
    opt.textContent = CLASS_NAMES[cls] || cls;
    filterClass.appendChild(opt);
  });
}

// === Filter Logic ===
function applyFilters() {
  const classVal = filterClass.value;
  const rarityVal = filterRarity.value;
  const searchVal = filterSearch.value.toLowerCase().trim();

  filteredServants = allServants.filter((s) => {
    if (classVal !== "all" && s.className !== classVal) return false;
    if (rarityVal !== "all" && s.rarity !== parseInt(rarityVal)) return false;
    if (searchVal && !s.name.toLowerCase().includes(searchVal)) return false;
    return true;
  });

  countDisplay.textContent = filteredServants.length;
  renderCards();
}

// === Render Cards ===
function renderCards() {
  cardsGrid.innerHTML = "";

  if (filteredServants.length === 0) {
    noResults.style.display = "block";
    return;
  }
  noResults.style.display = "none";

  filteredServants.forEach((servant, index) => {
    const card = createCard(servant, index);
    cardsGrid.appendChild(card);
  });
}

function createCard(servant, index) {
  const card = document.createElement("div");
  card.className = `servant-card rarity-${servant.rarity}`;
  card.style.animationDelay = `${Math.min(index * 30, 600)}ms`;

  const stars = getStars(servant.rarity);
  const className = CLASS_NAMES[servant.className] || servant.className;

  card.innerHTML = `
    <div class="card-top">
      <div class="card-face">
        <img src="${servant.faceUrl}" alt="${servant.name}" loading="lazy" 
             onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 56 56%22><rect fill=%22%23191c3a%22 width=%2256%22 height=%2256%22/><text x=%2228%22 y=%2232%22 text-anchor=%22middle%22 fill=%22%235c5a6e%22 font-size=%2214%22>?</text></svg>'">
        <div class="card-face-border"></div>
      </div>
      <div class="card-info">
        <div class="card-name" title="${servant.name}">${servant.name}</div>
        <div class="card-class">${className}</div>
        <div class="card-stars">${stars}</div>
      </div>
      <div class="card-collection">No.${servant.collectionNo}</div>
    </div>
    <div class="card-bottom">
      <div class="skill-name" title="${servant.skillName}">S${servant.skillNum}: ${servant.skillName}</div>
      <div class="charge-badge">${servant.chargePercent}%</div>
    </div>
  `;

  return card;
}

function getStars(rarity) {
  if (rarity === 0) return "☆";
  return "★".repeat(rarity);
}

// === Event Listeners ===
filterClass.addEventListener("change", applyFilters);
filterRarity.addEventListener("change", applyFilters);
filterSearch.addEventListener("input", applyFilters);

// === Start ===
document.addEventListener("DOMContentLoaded", init);

// Текущий год в подвале страницы.
const yearElement = document.getElementById("current-year");

if (yearElement) {
    yearElement.textContent = new Date().getFullYear();
}

// Подсветка пункта навигации, соответствующего открытой странице:
// выбирается ссылка с самым длинным подходящим адресом.
const currentPath = window.location.pathname;
let currentLink = null;

document.querySelectorAll(".site-nav a").forEach((link) => {
    const linkPath = link.getAttribute("href");
    const matches = linkPath === "/"
        ? currentPath === "/"
        : currentPath.startsWith(linkPath);

    if (
        matches
        && (!currentLink
            || linkPath.length > currentLink.getAttribute("href").length)
    ) {
        currentLink = link;
    }
});

if (currentLink) {
    currentLink.classList.add("active");
    currentLink.setAttribute("aria-current", "page");
}

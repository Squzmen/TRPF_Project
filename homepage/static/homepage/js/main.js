// Текущий год в подвале страницы.
const yearElement = document.getElementById("current-year");

if (yearElement) {
    yearElement.textContent = new Date().getFullYear();
}

// Подсветка пункта навигации, соответствующего открытой странице.
const currentPath = window.location.pathname;

document.querySelectorAll(".site-nav a").forEach((link) => {
    const linkPath = link.getAttribute("href");
    const isHome = linkPath === "/";
    const isCurrent = isHome
        ? currentPath === "/"
        : currentPath.startsWith(linkPath);

    if (isCurrent) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
    }
});

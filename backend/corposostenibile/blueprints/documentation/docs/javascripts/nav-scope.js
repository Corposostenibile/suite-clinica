function getScalarPathname() {
  try {
    return String(window.location.pathname || "");
  } catch (error) {
    return "";
  }
}

function parseDocVariant(pathname) {
  const match = pathname.match(
    /\/(lista|dettaglio|task|formazione|check_azienda)_(team_leader|professionista)(?:_(nutrizione|coaching|psicologia))?\/?$/
  );

  if (!match) {
    return null;
  }

  return {
    audience: match[2],
    specialty: match[3] || "all",
  };
}

function parseLinkVariant(href) {
  if (!href) {
    return null;
  }

  try {
    const url = new URL(href, window.location.origin);
    return parseDocVariant(url.pathname);
  } catch (error) {
    return null;
  }
}

function shouldHideLink(currentVariant, linkVariant) {
  if (!currentVariant || !linkVariant) {
    return false;
  }

  return (
    currentVariant.audience !== linkVariant.audience ||
    currentVariant.specialty !== linkVariant.specialty
  );
}

function filterPrimaryNav() {
  const currentVariant = parseDocVariant(getScalarPathname());
  if (!currentVariant) {
    return;
  }

  const navLinks = document.querySelectorAll(".md-nav--primary a[href]");
  navLinks.forEach((link) => {
    const linkVariant = parseLinkVariant(link.getAttribute("href"));
    if (!shouldHideLink(currentVariant, linkVariant)) {
      return;
    }

    const navItem = link.closest(".md-nav__item");
    if (navItem) {
      navItem.setAttribute("data-docs-hidden", "true");
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", filterPrimaryNav);
} else {
  filterPrimaryNav();
}

import { useId, useState, type MouseEvent, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router";

import { PAGES } from "../pages";
import { Author } from "./Author";
import { Footer } from "./Footer";

const MAIN_ID = "main";

export function Layout({ children }: { children: ReactNode }) {
  const navId = useId();
  const { pathname } = useLocation();
  // The menu (narrow screens) is open on the page it was opened on, so choosing a page closes it.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === pathname;

  return (
    <div className="shell">
      <a className="skip-link" href={`#${MAIN_ID}`} onClick={skipToMain}>
        Skip to content
      </a>
      <header className="sidebar">
        <div className="sidebar__bar">
          <NavLink to="/" className="brand">
            Well Operations
            <span className="brand__sub">Agent Platform</span>
          </NavLink>
          <button
            type="button"
            className="menu-button"
            aria-expanded={open}
            aria-controls={navId}
            onClick={() => {
              setOpenOn(open ? null : pathname);
            }}
          >
            {open ? "Close" : "Menu"}
          </button>
        </div>
        <div id={navId} className="nav-panel" data-open={open}>
          <Author className="author--nav" />
          <nav className="nav" aria-label="Main">
            <ul>
              {PAGES.map((page) => (
                <li key={page.path}>
                  <NavLink to={page.path} end={page.path === "/"} className="nav__link">
                    {page.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>
      <div className="page">
        <main id={MAIN_ID} tabIndex={-1} className="main">
          {children}
        </main>
        <Footer />
      </div>
    </div>
  );
}

// With hash routing, a plain #main link would change the route; move focus instead.
function skipToMain(event: MouseEvent<HTMLAnchorElement>) {
  event.preventDefault();
  const main = document.getElementById(MAIN_ID);
  main?.focus();
  main?.scrollIntoView();
}

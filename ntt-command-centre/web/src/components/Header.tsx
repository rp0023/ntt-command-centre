import { useEffect, useRef, useState } from "react";
import type { MetaPayload } from "../api/types";
import { useSession } from "../state/SessionContext";
import { auth } from "../api/client";
import { useTheme } from "../theme/ThemeProvider";
import { Icon, SIZE } from "./icons";
import { PersonaMark } from "./PersonaPicker";
import { useApp } from "../state/AppStateProvider";

export function Header({
  onToggleRail,
}: {
  meta: MetaPayload | null;
  onToggleRail?: () => void;
}) {
  const user = useSession();
  const { state } = useApp();
  const { theme, toggle } = useTheme();
  const [menu, setMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!menu) return;
    const onDown = (e: MouseEvent) => {
      if (
        !menuRef.current?.contains(e.target as Node) &&
        !triggerRef.current?.contains(e.target as Node)
      )
        setMenu(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMenu(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menu]);

  return (
    <header className="hdr">
      {onToggleRail && (
        <button
          type="button"
          className="ghost hdr-icon hdr-rail"
          onClick={onToggleRail}
          aria-label="Show or hide the menu"
        >
          <Icon name="menu" size={SIZE.control} />
        </button>
      )}

      <img
        className="hdr-logo"
        src={theme === "dark" ? "/ntt-logo-reversed.png" : "/ntt-logo.png"}
        alt="NTT DATA"
        width={92}
        height={33}
      />
      <span className="hdr-name">Deal Intelligence</span>

      <div className="hdr-right">
        {state.page === "tldr" && (
          <button type="button" className="hdr-overview" onClick={() => window.dispatchEvent(new Event("ntt:open-brief"))}>
            Overview
          </button>
        )}
        {/* The mark is the theme you would switch TO, matching the label:
            a moon on the light shell, a sun on the dark one. */}
        <button
          type="button"
          className="ghost hdr-icon"
          onClick={toggle}
          aria-label={theme === "light" ? "Use dark theme" : "Use light theme"}
        >
          <Icon name={theme === "light" ? "moon" : "sun"} size={SIZE.control} />
        </button>

        <div className="who-wrap">
          <button
            type="button"
            ref={triggerRef}
            className="who"
            aria-haspopup="dialog"
            aria-expanded={menu}
            onClick={() => setMenu((v) => !v)}
          >
            {/* The same isometric mark the picker uses, so the thing in the
                header is recognisably the thing you chose. The tile keeps its
                solid persona fill; persona.css knocks the mark out against it. */}
            <span className="who-avatar" aria-hidden="true">
              <PersonaMark persona={user.role} size={26} />
            </span>
            <span className="who-text">
              <span className="who-name">{user.name}</span>
              <span className="who-role">{user.roleLabel}</span>
            </span>
            <span className="who-caret" aria-hidden="true">▾</span>
          </button>

          {menu && (
            <div className="who-menu profile-menu" ref={menuRef} role="dialog" aria-label="Your profile">
              <strong>{user.name}</strong>
              <p className="profile-email">{user.email}</p>
              <p>{user.roleLabel} &middot; {user.scopeLabel}</p>
              {user.role === "manager" && <p className="profile-email">Pod membership is derived from the demo sales roster.</p>}
              <button type="button" onClick={() => auth.logout()}>Sign out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

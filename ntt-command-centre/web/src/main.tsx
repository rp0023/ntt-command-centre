import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { Gate } from "./components/Gate";
import { AppStateProvider } from "./state/AppStateProvider";
import { ThemeProvider } from "./theme/ThemeProvider";
import "./theme/tokens.css";
import "./styles/app.css";
// Loaded AFTER app.css on purpose: each of these is the last word on what it
// styles. density.css is the legibility pass; the rest are one component each.
import "./styles/density.css";
import "./styles/chart-ask.css";
import "./styles/persona.css";
import "./styles/ask-extras.css";
import "./styles/reps.css";
import "./styles/actions.css";
import "./styles/pages.css";
import "./styles/fab.css";
import "./styles/gate.css";
import "./styles/icons.css";
import "./styles/tags.css";
import "./styles/findings.css";
import "./styles/metric-banners.css";

// StrictMode stays ON deliberately: it double-invokes every effect, which is
// exactly the condition the chart repository's render/teardown contract has to
// survive (the render/teardown contract). If a chart leaks a tooltip or double-draws, it
// shows up here first rather than in front of the customer.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <Gate>
        <AppStateProvider>
          <App />
        </AppStateProvider>
      </Gate>
    </ThemeProvider>
  </StrictMode>,
);

import { createRoot } from "react-dom/client";
import { App } from "./App";
// Cardo (OFL), after Griffo's Aldine roman: the labels' face, served from the project (Latin only).
import "@fontsource/cardo/latin-400.css";
import "@fontsource/cardo/latin-400-italic.css";
import "./styles.css";
import { rig } from "./rig";

// Dev only: inspect the camera from the console / automated checks.
if (import.meta.env.DEV) Object.assign(window, { rig });

createRoot(document.getElementById("root")!).render(<App />);

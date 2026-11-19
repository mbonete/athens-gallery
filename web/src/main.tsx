import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";
import { rig } from "./rig";

// Dev only: inspect the camera from the console / automated checks.
if (import.meta.env.DEV) Object.assign(window, { rig });

createRoot(document.getElementById("root")!).render(<App />);

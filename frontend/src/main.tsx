import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "~/App";
import { AuthProvider } from "~/state/AuthProvider";
import "~/styles/base.css";

const container = document.getElementById("root");

if (container === null) {
  throw new Error("В разметке нет элемента #root");
}

createRoot(container).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
);

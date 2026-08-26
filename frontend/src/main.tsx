import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App.tsx";
import "./index.css";
import Board from "./pages/Board.tsx";
import FallDetail from "./pages/FallDetail.tsx";
import Postfach from "./pages/Postfach.tsx";
import Stammdaten from "./pages/Stammdaten.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<Board />} />
          <Route path="faelle/:fallId" element={<FallDetail />} />
          <Route path="postfach" element={<Postfach />} />
          <Route path="stammdaten" element={<Stammdaten />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);

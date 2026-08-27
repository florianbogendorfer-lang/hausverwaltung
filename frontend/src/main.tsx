import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App.tsx";
import { AuthProvider } from "./auth.tsx";
import "./index.css";
import Benutzer from "./pages/Benutzer.tsx";
import Board from "./pages/Board.tsx";
import FallDetail from "./pages/FallDetail.tsx";
import Login from "./pages/Login.tsx";
import Postfach from "./pages/Postfach.tsx";
import Stammdaten from "./pages/Stammdaten.tsx";
import Ticket from "./pages/Ticket.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Öffentliche Kundenansicht — bewusst außerhalb von <App />, ohne
              die interne Operator-Navigation und ohne Login. */}
          <Route path="ticket/:zugriffstoken" element={<Ticket />} />
          <Route path="login" element={<Login />} />
          <Route element={<App />}>
            <Route index element={<Board />} />
            <Route path="faelle/:fallId" element={<FallDetail />} />
            <Route path="postfach" element={<Postfach />} />
            <Route path="stammdaten" element={<Stammdaten />} />
            <Route path="benutzer" element={<Benutzer />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);

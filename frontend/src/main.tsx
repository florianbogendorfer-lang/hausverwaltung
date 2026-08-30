import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App.tsx";
import { AuthProvider } from "./auth.tsx";
import { ErrorBoundary } from "./ErrorBoundary.tsx";
import "./index.css";
import Benutzer from "./pages/Benutzer.tsx";
import Board from "./pages/Board.tsx";
import DienstleisterPortal from "./pages/DienstleisterPortal.tsx";
import FallDetail from "./pages/FallDetail.tsx";
import Login from "./pages/Login.tsx";
import NichtGefunden from "./pages/NichtGefunden.tsx";
import Postfach from "./pages/Postfach.tsx";
import Stammdaten from "./pages/Stammdaten.tsx";
import Ticket from "./pages/Ticket.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Öffentliche Kundenansicht — bewusst außerhalb von <App />, ohne
                die interne Operator-Navigation und ohne Login. */}
            <Route path="ticket/:zugriffstoken" element={<Ticket />} />
            <Route path="dienstleister-portal/:zugriffstoken" element={<DienstleisterPortal />} />
            <Route path="login" element={<Login />} />
            <Route element={<App />}>
              {/* faelle/:fallId ist eine verschachtelte Route unter Board
                  (nicht wie früher eine eigenständige Seite) — Board
                  rendert die Liste immer und zeigt FallDetail über ein
                  <Outlet/> als Split-View-Panel (bzw. auf schmalen
                  Screens als Vollbild-Popup) daneben an, siehe
                  Board.tsx. Die URL wechselt dabei ganz normal zu
                  /faelle/:id (Deep-Link, Zurück-Button, Neuladen
                  funktionieren weiterhin). */}
              <Route path="/" element={<Board />}>
                <Route path="faelle/:fallId" element={<FallDetail />} />
              </Route>
              <Route path="postfach" element={<Postfach />} />
              <Route path="stammdaten" element={<Stammdaten />} />
              <Route path="benutzer" element={<Benutzer />} />
              <Route path="*" element={<NichtGefunden />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);

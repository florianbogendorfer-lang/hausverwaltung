import { Component, type ErrorInfo, type ReactNode } from "react";
import { fehlerMelden } from "./sentry";

// React-Best-Practice: ohne Error Boundary führt ein Rendering-Fehler
// irgendwo im Baum zu einem komplett weißen Bildschirm ohne jede
// Rückmeldung — für ein internes Werkzeug, das Bearbeiter den ganzen Tag
// nutzen, ist "Seite neu laden" die brauchbarere Fehlerreaktion als ein
// unerklärliches Verschwinden der gesamten Oberfläche.
export class ErrorBoundary extends Component<{ children: ReactNode }, { fehler: Error | null }> {
  state: { fehler: Error | null } = { fehler: null };

  static getDerivedStateFromError(fehler: Error) {
    return { fehler };
  }

  componentDidCatch(fehler: Error, info: ErrorInfo) {
    console.error("Unerwarteter Rendering-Fehler:", fehler, info.componentStack);
    fehlerMelden(fehler, { componentStack: info.componentStack ?? undefined });
  }

  render() {
    if (this.state.fehler) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
          <div className="w-full max-w-sm rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-sm">
            <p className="text-lg font-semibold text-slate-900">Etwas ist schiefgelaufen</p>
            <p className="mt-2 text-sm text-slate-500">
              Die Seite ist auf einen unerwarteten Fehler gestoßen. Ein Neuladen behebt das meist.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-5 inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
            >
              Seite neu laden
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

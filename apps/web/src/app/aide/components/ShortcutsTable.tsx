import { Keyboard } from "lucide-react";
import type { Shortcut } from "../data";

export function ShortcutsTable({ shortcuts }: { shortcuts: Shortcut[] }) {
  return (
    <section id="raccourcis">
      <div className="flex items-center gap-2 mb-4">
        <Keyboard className="h-5 w-5 text-gray-600" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-gray-800">Raccourcis clavier</h2>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100">
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Raccourci</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody>
            {shortcuts.map((s, i) => (
              <tr key={i} className="border-b border-gray-50 last:border-0">
                <td className="px-6 py-3">
                  <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs font-mono text-gray-700">
                    {s.keys}
                  </kbd>
                </td>
                <td className="px-6 py-3 text-sm text-gray-700">{s.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

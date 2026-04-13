import { FileText, Globe, Mail, Phone, Shield } from "lucide-react";

export function DocumentationLinks() {
  return (
    <section>
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-blue-100 p-2">
            <FileText className="h-5 w-5 text-blue-600" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Documentation</h2>
            <p className="mt-1 text-sm text-gray-600">
              Consultez la documentation complète pour découvrir toutes les fonctionnalités d&apos;OptiFlow AI.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <a
                href="https://docs.optiflow.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Globe className="h-4 w-4" aria-hidden="true" />
                Documentation en ligne
              </a>
              <a
                href="/api/v1/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Shield className="h-4 w-4" aria-hidden="true" />
                API Swagger
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function SupportContact() {
  return (
    <section className="bg-blue-50 rounded-xl border border-blue-200 p-6">
      <div className="flex items-start gap-4">
        <Mail className="h-6 w-6 text-blue-600 mt-0.5" aria-hidden="true" />
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Besoin d&apos;aide supplémentaire ?</h2>
          <p className="mt-1 text-sm text-gray-600">
            Notre équipe support est disponible du lundi au vendredi, de 9h à 18h.
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            <a
              href="mailto:support@optiflow.ai"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Mail className="h-4 w-4" aria-hidden="true" />
              support@optiflow.ai
            </a>
            <a
              href="tel:+33123456789"
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-blue-200 text-blue-700 text-sm font-medium rounded-lg hover:bg-blue-50 transition-colors"
            >
              <Phone className="h-4 w-4" aria-hidden="true" />
              01 23 45 67 89
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

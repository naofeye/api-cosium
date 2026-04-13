# Accessibilité OptiFlow — état & roadmap

> Cible WCAG 2.1 niveau AA. Audit régulier avec axe DevTools + Lighthouse.

## État actuel (audit grep automatique)

| Critère | Coverage | État |
|---|---|---|
| Skip link "passer au contenu" | ✅ `app/layout.tsx:18-25` | DONE |
| `aria-hidden` sur icones décoratives | 82/171 fichiers utilisant lucide (~48%) | PARTIAL |
| `aria-label` sur icones seules | Présent dans Sidebar, Buttons icon-only | PARTIAL |
| `htmlFor` sur form labels | 17 fichiers (couvre forms principaux) | PARTIAL |
| `focus-visible:` ou `focus:ring` | 40 fichiers | GOOD |
| `role="alert"` + `aria-live` | FormField, Header, ErrorBoundary, Toast | DONE pour critique |
| Navigation clavier (Tab/Escape) | ConfirmDialog focus trap, Sidebar tab order | DONE pour critique |
| Contraste WCAG AA | Tokens design (gray-900 sur white = 21:1) | GOOD |

## Patterns adoptés

### Skip link (root layout)

```tsx
<a href="#main-content"
   className="sr-only focus:not-sr-only focus:absolute focus:top-2 ...">
  Aller au contenu principal
</a>
```

### Icones décoratives

```tsx
{/* Icone qui n'apporte pas d'info nouvelle */}
<Bell className="h-4 w-4" aria-hidden="true" />
<span>Notifications</span>

{/* Icone seule = bouton */}
<button aria-label="Supprimer">
  <Trash2 className="h-4 w-4" aria-hidden="true" />
</button>
```

### Form fields

```tsx
<FormField label="Email *" htmlFor="email" error={errors.email}>
  <Input id="email" type="email" {...register("email")} />
</FormField>
```

### Erreurs avec live region

```tsx
{error && (
  <div role="alert" className="text-red-700 text-sm">
    {error.message}
  </div>
)}

<ToastContainer aria-live="polite" />
```

### Focus trap (modales)

`ConfirmDialog.tsx` implémente :
- Capture focus à l'ouverture
- Trap Tab (boucle dans dialog)
- Escape ferme + restore focus trigger

### Navigation clavier DataTable

- Tab : navigue lignes
- Enter sur ligne : action click
- Escape : ferme menu actions

## TODO restant

Rangé par priorité d'impact utilisateur :

### Haute (P1 a11y)
- [ ] Audit complet `aria-label` sur 89 fichiers icon-only restants
- [ ] Form `htmlFor` sur 100% des inputs (CreateUserDialog, devis/new, autres)
- [ ] Test Lighthouse Accessibility ≥ 90 sur 5 pages clés (login, dashboard, clients, devis, settings)

### Moyenne (P2 a11y)
- [ ] `aria-hidden` sur 89 icones décoratives restantes
- [ ] Test contraste automatisé via axe-core en CI
- [ ] Navigation clavier audit complet (Tab order toutes pages)

### Basse (P3 a11y)
- [ ] Annonce des tabs filter (ARIA tablist confirmé)
- [ ] Localisation : `lang="fr"` partout (déjà sur `<html>`)
- [ ] Reduce-motion : respecter `prefers-reduced-motion`

## Outillage

```bash
# Audit local
cd apps/web
npx @axe-core/cli http://localhost:3000/dashboard

# Lighthouse CI (à configurer)
npx lhci autorun --collect.url=http://localhost:3000/dashboard

# Devtools : Chrome DevTools > Lighthouse > Accessibility
```

## Tests

`tests/components/ConfirmDialog.test.tsx` valide focus trap + Escape.
À ajouter : tests axe-core sur composants critiques.

# Audit Iteration 9 - Dead Code & Architecture

## Issues Found: 7

### DC-01: Unused frontend component AsyncSelect [INFO]
- `frontend/src/components/form/AsyncSelect.tsx` is defined but never imported by any page or component
- Likely created for future use (e.g., customer search in devis forms)
- **Decision**: Keep - useful component for upcoming features, documented as available

### DC-02: Unused frontend component FileUpload [INFO]
- `frontend/src/components/ui/FileUpload.tsx` is defined but never imported
- Upload functionality currently uses a different inline implementation
- **Decision**: Keep - required by CLAUDE.md component checklist, will be used in GED pages

### DC-03: Unused npm dependency `@tailwindcss/forms` [INFO]
- Listed in package.json but not referenced in any config or source file
- Tailwind v4 uses CSS-based configuration; this plugin is a v3 pattern
- Low impact (installed but tree-shaken, not in production bundle)
- **Decision**: Note for future cleanup, not removing to avoid risk

### DC-04: Unused npm dependency `class-variance-authority` (CVA) [INFO]
- Listed in package.json but `cva()` function never called anywhere
- shadcn/ui components may expect it; removing could break future additions
- **Decision**: Keep - part of shadcn/ui standard stack per CLAUDE.md

### DC-05: Unused npm dependency `@next/bundle-analyzer` [INFO]
- Listed in devDependencies but never configured in next.config.ts
- Useful dev tool but not wired up
- **Decision**: Keep in devDependencies, useful for manual analysis

### DC-06: No TODO/FIXME/HACK/XXX comments found [CLEAN]
- Full scan of backend/app/ and frontend/src/ found zero instances
- Project is clean of technical debt markers

### DC-07: No dead routes or unregistered routers [CLEAN]
- All 32 router files have active endpoints
- All 32 routers are registered in main.py
- No orphaned service/repository modules found

## Summary
- Issues found: 7
- Issues requiring fix: 0
- Informational items: 5
- Clean checks: 2
- All services, repositories, and integrations are actively imported and used
- No duplicate logic patterns detected
- No dead Python functions found in services/ or repositories/

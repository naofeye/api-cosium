/**
 * Constantes partagees frontend.
 *
 * Centralisation des valeurs reutilisees pour eviter la divergence
 * (ex: deux composants de recherche avec deux debounce differents).
 */

/** Delai de debounce pour les inputs de recherche (ms). */
export const SEARCH_DEBOUNCE_MS = 300;

/** Nombre de caracteres minimum avant declenchement d'une recherche. */
export const SEARCH_MIN_CHARS = 2;

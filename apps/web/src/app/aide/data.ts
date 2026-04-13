export interface FAQItem {
  question: string;
  answer: string;
}

export interface Shortcut {
  keys: string;
  description: string;
}

export const faqItems: FAQItem[] = [
  {
    question: "Comment créer un nouveau dossier client ?",
    answer:
      'Rendez-vous dans la section Dossiers via le menu latéral, puis cliquez sur le bouton "Nouveau dossier" en haut à droite. Remplissez les informations du client (nom, prénom, coordonnées) et validez. Le dossier sera automatiquement lié au client dans le CRM.',
  },
  {
    question: "Comment générer un devis ?",
    answer:
      'Depuis un dossier client, allez dans l\'onglet "Devis" et cliquez sur "Nouveau devis". Ajoutez les lignes de produits (montures, verres, options), les remises éventuelles, et le système calculera automatiquement les montants HT, TTC et le reste à charge. Vous pouvez ensuite envoyer le devis par email ou le télécharger en PDF.',
  },
  {
    question: "Comment importer des clients depuis un fichier CSV ?",
    answer:
      'Allez dans la section Clients, puis cliquez sur "Importer CSV". Le fichier doit contenir les colonnes : nom, prénom, email, téléphone. Un aperçu vous sera montré avant l\'import définitif. Les doublons potentiels seront détectés automatiquement.',
  },
  {
    question: "Comment rapprocher les paiements bancaires ?",
    answer:
      "Dans la section Rapprochement, importez votre relevé bancaire au format CSV. Le système proposera automatiquement des correspondances entre les transactions bancaires et les factures en attente. Vous pouvez valider ou corriger les suggestions, puis glisser-déposer manuellement les transactions non matchées.",
  },
  {
    question: "Qu'est-ce que le copilote IA ?",
    answer:
      "Le copilote IA est un assistant intelligent intégré à OptiFlow. Il peut analyser vos dossiers, suggérer des actions commerciales, vérifier la complétude documentaire, et répondre à vos questions sur les données financières. Accédez-y via l'icône IA dans la barre latérale ou avec le raccourci Ctrl+K.",
  },
  {
    question: "Comment fonctionne la synchronisation Cosium ?",
    answer:
      "OptiFlow se connecte à votre ERP Cosium en lecture seule pour récupérer les données clients, factures, paiements, ordonnances et rendez-vous. La synchronisation est déclenchée depuis la page Administration. Aucune donnée n'est modifiée dans Cosium : la synchronisation est unidirectionnelle (Cosium vers OptiFlow uniquement).",
  },
  {
    question: "Comment preparer une prise en charge (PEC) ?",
    answer:
      "Allez dans Assistance PEC via le menu latéral. Sélectionnez un client, puis lancez la préparation. Le système consolide automatiquement les données depuis toutes les sources (Cosium, documents, devis) et détecte les incohérences. Vérifiez chaque champ, corrigez si nécessaire, puis soumettez la PEC.",
  },
  {
    question: "Comment contacter le support ?",
    answer:
      "Pour toute question technique ou demande d'assistance, envoyez un email à support@optiflow.ai. Notre équipe répond sous 24h ouvrables. Pour les urgences (blocage complet), appelez le 01 23 45 67 89.",
  },
];

export const shortcuts: Shortcut[] = [
  { keys: "Ctrl + K", description: "Ouvrir la recherche globale / Copilote IA" },
  { keys: "Ctrl + N", description: "Nouveau client" },
  { keys: "Ctrl + D", description: "Aller au Dashboard" },
  { keys: "Ctrl + Shift + S", description: "Aller aux Statistiques" },
  { keys: "Escape", description: "Fermer la modale ou le panneau actif" },
  { keys: "?", description: "Afficher l'aide des raccourcis clavier" },
];

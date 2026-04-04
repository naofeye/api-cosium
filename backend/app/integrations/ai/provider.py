"""Abstract AI provider interface."""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Interface abstraite pour les fournisseurs IA."""

    @abstractmethod
    def query(self, prompt: str, context: str = "", system: str = "") -> str:
        """Envoie une requete au modele IA et retourne la reponse.

        Args:
            prompt: la question de l'utilisateur
            context: contexte metier (dossier, documents, etc.)
            system: instructions systeme pour le mode copilote

        Returns:
            La reponse textuelle du modele
        """
        ...

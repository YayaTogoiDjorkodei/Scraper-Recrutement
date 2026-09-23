"""Safe, local data used to develop and demonstrate the desktop workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Evidence:
    field: str
    value: str
    excerpt: str
    method: str = "exact"


@dataclass(frozen=True, slots=True)
class JobOffer:
    identifier: str
    title: str
    company: str
    location: str
    source: str
    posted: str
    skills: tuple[str, ...]
    experience: str
    contract: str
    description: str
    url: str
    description_status: str
    quality: str
    evidence: tuple[Evidence, ...]
    qualification: str = "matching"
    record_id: int | None = None
    education: str = ""
    contact_email: str = ""
    contact_status: str = "not_requested"
    contact_level: str = ""


def sample_offers() -> list[JobOffer]:
    """Return representative local records without making a network request."""
    return [
        JobOffer(
            identifier="linkedin-demo-001",
            title="Développeur Python",
            company="Atlas Digital",
            location="Rabat",
            source="LinkedIn",
            posted="Aujourd’hui",
            skills=("Python", "Django", "Docker", "PostgreSQL"),
            experience="3 ans",
            contract="CDI",
            description=("Nous recherchons un développeur Python pour renforcer notre équipe "
                         "produit. Maîtrise de Django, Docker et PostgreSQL requise. "
                         "Bac+5 ou expérience équivalente."),
            url="https://www.linkedin.com/jobs/view/example-python",
            description_status="Disponible",
            quality="Vérifiée",
            evidence=(
                Evidence("Compétence requise", "Python", "Maîtrise de Django, Docker et PostgreSQL requise."),
                Evidence("Expérience", "3 ans", "Nous recherchons un développeur Python pour renforcer notre équipe produit."),
                Evidence("Études", "Bac+5", "Bac+5 ou expérience équivalente."),
            ),
        ),
        JobOffer(
            identifier="indeed-demo-002",
            title="Technicien support IT",
            company="Maghreb Services",
            location="Casablanca",
            source="Indeed",
            posted="Il y a 2 jours",
            skills=("Windows", "Réseau", "Active Directory"),
            experience="1–2 ans",
            contract="CDI",
            description=("Assurer le support utilisateurs de niveau 1 et 2. Connaissance de "
                         "Windows, Active Directory et des réseaux indispensable. BTS informatique apprécié."),
            url="https://www.indeed.com/viewjob?jk=example-support",
            description_status="Disponible",
            quality="À revoir",
            evidence=(
                Evidence("Compétence requise", "Windows", "Connaissance de Windows, Active Directory et des réseaux indispensable."),
                Evidence("Diplôme préféré", "BTS informatique", "BTS informatique apprécié.", "pattern"),
            ),
        ),
        JobOffer(
            identifier="linkedin-demo-003",
            title="Ingénieur DevOps",
            company="Casablanca Cloud",
            location="Casablanca",
            source="LinkedIn",
            posted="Il y a 4 jours",
            skills=("Kubernetes", "AWS", "Terraform", "Linux"),
            experience="5 ans",
            contract="CDI",
            description=("Poste hybride à Casablanca. Vous industrialisez les déploiements avec "
                         "Kubernetes, Terraform et AWS. Cinq années d’expérience sont demandées."),
            url="https://www.linkedin.com/jobs/view/example-devops",
            description_status="Disponible",
            quality="Vérifiée",
            evidence=(
                Evidence("Compétence requise", "Kubernetes", "industrialisez les déploiements avec Kubernetes, Terraform et AWS."),
                Evidence("Expérience", "5 ans", "Cinq années d’expérience sont demandées.", "pattern"),
            ),
        ),
        JobOffer(
            identifier="indeed-demo-004",
            title="Data Analyst",
            company="Rabat Analytics",
            location="Rabat",
            source="Indeed",
            posted="Il y a 1 semaine",
            skills=("SQL", "Power BI", "Python"),
            experience="Non précisé",
            contract="CDD",
            description="La fiche détaillée sera collectée au prochain cycle si le budget le permet.",
            url="https://www.indeed.com/viewjob?jk=example-data",
            description_status="En attente",
            quality="Incomplète",
            evidence=(),
        ),
    ]


def suggested_study_name() -> str:
    return f"Marché IT Maroc — {date.today():%Y-%m-%d}"

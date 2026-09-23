"""The PySide6 desktop experience for Corporate Scraper v2."""

from __future__ import annotations

import sys
import json
from html import escape
from threading import Event
from collections import Counter
from collections.abc import Iterable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, QTimer, QUrl, QThread, Signal, QSettings
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QStackedWidget, QTableView, QTextBrowser, QToolButton,
    QVBoxLayout, QWidget, QFileDialog, QDialog, QDialogButtonBox, QProgressBar,
)

from .cities import City, MoroccoCityService
from .fixture_data import Evidence, JobOffer, sample_offers, suggested_study_name
from .exports import export_study
from .models import FilterSpec, RunSpec, TargetMode
from .paths import data_directory, study_database, results_directory, set_results_directory, default_export_path
from .references import TECHNOLOGY_REFERENCES
from .runner import CollectionRunner
from .sources import IndeedAdapter, LinkedInAdapter
from .store import StudyStore
from .transport import HttpTransport


STYLE = """
QMainWindow { background: #f4f7fb; color: #172033; }
QWidget { font-family: 'Segoe UI'; font-size: 10pt; color: #172033; }
QLabel { color: #172033; }
QFrame#sidebar { background: #13233f; }
QLabel#brand { color: white; font-size: 18pt; font-weight: 700; padding: 16px 12px 8px; }
QLabel#subtitle { color: #b9c7df; padding: 0 12px 16px; }
QListWidget#navigation { background: transparent; border: none; color: #dbe7ff; padding: 8px; }
QListWidget#navigation::item { border-radius: 6px; padding: 12px; margin: 2px 0; }
QListWidget#navigation::item:selected { background: #2b6de0; color: white; }
QListWidget#navigation::item:hover { background: #203b68; }
QFrame#card, QGroupBox { background: #ffffff; color: #172033; border: 1px solid #dbe3ef; border-radius: 8px; }
QGroupBox { font-weight: 600; margin-top: 12px; padding: 14px 10px 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
QPushButton { background: #e8eef8; color: #172033; border: 1px solid #ccd8eb; border-radius: 6px; padding: 8px 12px; }
QPushButton:hover { background: #dce7f8; }
QPushButton#primary { background: #1769e0; color: white; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #0959c6; }
QLineEdit, QComboBox, QSpinBox { background: #ffffff; color: #172033; border: 1px solid #7d91ad; border-radius: 5px; padding: 7px; min-height: 20px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 2px solid #1769e0; padding: 6px; }
QLineEdit::placeholder { color: #62708a; }
QComboBox QAbstractItemView { background: #ffffff; color: #172033; selection-background-color: #dce9ff; selection-color: #172033; }
QCheckBox { color: #172033; spacing: 8px; font-weight: 600; }
QCheckBox::indicator { width: 18px; height: 18px; background: #ffffff; border: 2px solid #62708a; border-radius: 4px; }
QCheckBox::indicator:hover { border-color: #1769e0; }
QCheckBox::indicator:checked { background: #1769e0; border-color: #1769e0; }
QProgressBar { background: #e8eef8; color: #172033; border: 1px solid #b9c9df; border-radius: 6px; min-height: 16px; text-align: center; font-weight: 600; }
QProgressBar::chunk { background: #1e9b62; border-radius: 5px; }
QTextBrowser, QListWidget { background: #ffffff; color: #172033; border: 1px solid #dbe3ef; border-radius: 6px; }
QListWidget::item { color: #172033; padding: 7px; }
QListWidget::item:selected { background: #dce9ff; color: #172033; }
QListWidget#navigation::item { color: #dbe7ff; border-radius: 6px; padding: 12px; margin: 2px 0; }
QListWidget#navigation::item:selected { background: #2b6de0; color: #ffffff; }
QListWidget#navigation::item:hover { background: #203b68; color: #ffffff; }
QTableView { background: #ffffff; color: #172033; alternate-background-color: #f6f9fe; border: 1px solid #dbe3ef; gridline-color: #edf1f7; selection-background-color: #2b6de0; selection-color: #ffffff; }
QHeaderView::section { background: #f6f8fb; border: none; border-bottom: 1px solid #dbe3ef; padding: 9px; font-weight: 600; }
QLabel#page-title { font-size: 20pt; font-weight: 700; }
QLabel#muted { color: #62708a; }
QLabel#metric { font-size: 20pt; font-weight: 700; color: #1769e0; }
QLabel#metric-label { color: #62708a; }
QFrame#stage-idle { background: #ffffff; border: 1px solid #dbe3ef; border-radius: 7px; }
QFrame#stage-active { background: #e7f7ee; border: 1px solid #45a875; border-radius: 7px; }
QFrame#stage-done { background: #eef3fb; border: 1px solid #93add0; border-radius: 7px; }
QLabel#stage-title { font-weight: 700; }
QLabel#stage-status { color: #46617d; font-size: 9pt; }
"""


class OffersModel(QAbstractTableModel):
    headers = ("Entreprise", "Poste", "Ville", "Source", "Publication", "Compétences", "Expérience", "Email", "Détail", "Cible", "Qualité", "Niveau / diplôme")

    def __init__(self, offers: Iterable[JobOffer], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._offers = list(offers)

    @property
    def offers(self) -> list[JobOffer]:
        return self._offers

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._offers)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: N802
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.ToolTipRole, Qt.ForegroundRole):
            return None
        offer = self._offers[index.row()]
        values = (offer.company, offer.title, offer.location, offer.source, offer.posted,
                  ", ".join(offer.skills), offer.experience, offer.contact_email or offer.contact_status, offer.description_status, offer.qualification, offer.quality, offer.education)
        if role == Qt.ForegroundRole and index.column() in (7, 8, 9):
            if values[index.column()] in ("En attente", "Incomplète", "À revoir", "unknown", "excluded"):
                return QColor("#a55a00")
            return QColor("#1e7a46")
        return values[index.column()]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return super().headerData(section, orientation, role)

    def offer_at(self, row: int) -> JobOffer:
        return self._offers[row]

    def replace_offers(self, offers: Iterable[JobOffer]) -> None:
        self.beginResetModel()
        self._offers = list(offers)
        self.endResetModel()


class OfferFilter(QSortFilterProxyModel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._query = ""
        self._source = "Toutes les sources"
        self._location = "Toutes les villes"
        self._qualification = "Toutes les qualifications"

    def set_query(self, query: str) -> None:
        self.beginFilterChange()
        self._query = query.casefold().strip()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_source(self, source: str) -> None:
        self.beginFilterChange()
        self._source = source
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_location(self, location: str) -> None:
        self.beginFilterChange()
        self._location = location
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_qualification(self, qualification: str) -> None:
        self.beginFilterChange()
        self._qualification = qualification
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        model = self.sourceModel()
        if not isinstance(model, OffersModel):
            return True
        offer = model.offer_at(source_row)
        if self._source != "Toutes les sources" and offer.source != self._source:
            return False
        if self._location != "Toutes les villes" and offer.location != self._location:
            return False
        if self._qualification != "Toutes les qualifications" and offer.qualification != self._qualification:
            return False
        searchable = " ".join((offer.title, offer.company, offer.location, offer.source, *offer.skills)).casefold()
        return not self._query or self._query in searchable


def page_header(title: str, description: str) -> QVBoxLayout:
    layout = QVBoxLayout()
    heading = QLabel(title)
    heading.setObjectName("page-title")
    layout.addWidget(heading)
    muted = QLabel(description)
    muted.setObjectName("muted")
    muted.setWordWrap(True)
    layout.addWidget(muted)
    return layout


class CityLoadThread(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, service: MoroccoCityService) -> None:
        super().__init__()
        self.service = service

    def run(self) -> None:
        try:
            self.loaded.emit(self.service.refresh())
        except Exception as error:  # The dialog keeps cached choices available.
            self.failed.emit(str(error))


class CityPickerDialog(QDialog):
    """Searchable, multi-select Moroccan city picker backed by a local cache."""

    def __init__(self, service: MoroccoCityService, selected: set[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.selected = selected
        self._thread: CityLoadThread | None = None
        self.setWindowTitle("Choisir les villes marocaines")
        self.resize(620, 560)
        layout = QVBoxLayout(self)
        heading = QLabel("Villes du Maroc")
        heading.setObjectName("page-title")
        layout.addWidget(heading)
        self.status = QLabel("Chargement du cache local…")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)
        self.search = QLineEdit(); self.search.setPlaceholderText("Rechercher une ville, un alias ou une région")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)
        self.cities = QListWidget(); self.cities.setAccessibleName("Liste des villes marocaines")
        layout.addWidget(self.cities, 1)
        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Actualiser depuis l’API")
        self.refresh_button.clicked.connect(self.refresh)
        self.select_all_button = QPushButton("Tout sélectionner")
        self.select_all_button.clicked.connect(self._select_visible)
        actions.addWidget(self.refresh_button); actions.addWidget(self.select_all_button); actions.addStretch()
        layout.addLayout(actions)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Appliquer")
        buttons.rejected.connect(self.reject); buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        cached = service.load_cached()
        if cached:
            self._populate(cached, "Villes disponibles hors ligne")
        else:
            self.refresh()

    def refresh(self) -> None:
        if self._thread and self._thread.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.status.setText("Téléchargement des villes marocaines…")
        self._thread = CityLoadThread(self.service)
        self._thread.loaded.connect(lambda cities: self._populate(cities, f"{len(cities)} villes chargées depuis l’API"))
        self._thread.failed.connect(self._failed)
        self._thread.start()

    def _failed(self, message: str) -> None:
        self.refresh_button.setEnabled(True)
        self.status.setText(f"API indisponible : {message}. Réessayez ou utilisez le cache local.")

    def _populate(self, cities: list[City], status: str) -> None:
        self.cities.clear()
        for city in cities:
            detail = " · ".join(value for value in (city.region, *city.aliases) if value)
            item = QListWidgetItem(f"{city.name}" + (f"  —  {detail}" if detail else ""))
            item.setData(Qt.UserRole, city.name)
            item.setData(Qt.UserRole + 1, " ".join((city.name, *city.aliases, city.region or "")).casefold())
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if city.name in self.selected else Qt.Unchecked)
            self.cities.addItem(item)
        self.refresh_button.setEnabled(True)
        self.status.setText(status)
        self._filter(self.search.text())

    def _filter(self, query: str) -> None:
        needle = query.casefold().strip()
        for row in range(self.cities.count()):
            item = self.cities.item(row)
            item.setHidden(bool(needle and needle not in str(item.data(Qt.UserRole + 1))))

    def _select_visible(self) -> None:
        for row in range(self.cities.count()):
            item = self.cities.item(row)
            if not item.isHidden():
                item.setCheckState(Qt.Checked)

    def selected_names(self) -> list[str]:
        return [str(self.cities.item(row).data(Qt.UserRole)) for row in range(self.cities.count())
                if self.cities.item(row).checkState() == Qt.Checked]


class SearchPage(QWidget):
    def __init__(self, start_run, city_service: MoroccoCityService | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.addLayout(page_header("Nouvelle recherche", "Configurez puis lancez une collecte locale. Les résultats et l’avancement sont sauvegardés sur cette machine."))

        scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)

        research = QGroupBox("Recherche")
        form = QFormLayout(research)
        self.study_name = QLineEdit(suggested_study_name())
        self.study_name.setAccessibleName("Nom de l’étude")
        self.terms = QLineEdit("développeur, support IT")
        self.terms.setAccessibleName("Termes de recherche")
        self.city_service = city_service or MoroccoCityService(data_directory() / "morocco-cities.json")
        self.cities = QLineEdit("Casablanca, Rabat")
        self.cities.setReadOnly(True)
        self.cities.setAccessibleName("Villes")
        city_selection = QWidget(); city_layout = QHBoxLayout(city_selection); city_layout.setContentsMargins(0, 0, 0, 0)
        city_layout.addWidget(self.cities, 1)
        choose_cities = QPushButton("Choisir les villes")
        choose_cities.clicked.connect(self._choose_cities)
        city_layout.addWidget(choose_cities)
        sources = QWidget()
        source_layout = QHBoxLayout(sources); source_layout.setContentsMargins(0, 0, 0, 0)
        self.linkedin = QCheckBox("LinkedIn — HTTP vérifié"); self.linkedin.setChecked(True)
        self.indeed = QCheckBox("Indeed — indisponible (HTTP 403)"); self.indeed.setChecked(False)
        source_layout.addWidget(self.linkedin); source_layout.addWidget(self.indeed); source_layout.addStretch()
        form.addRow("Nom de l’étude", self.study_name)
        form.addRow("Termes", self.terms)
        form.addRow("Sources", sources)
        form.addRow("Villes au Maroc", city_selection)
        layout.addWidget(research)

        objective = QGroupBox("Objectif")
        objective_form = QFormLayout(objective)
        self.target = QSpinBox(); self.target.setRange(1, 10_000); self.target.setValue(200); self.target.setAccessibleName("Objectif d’offres")
        self.target_mode = QComboBox(); self.target_mode.addItem("Offres avec description", "descriptions"); self.target_mode.addItem("Offres uniques", "listings")
        self.target_help = QLabel(); self.target_help.setObjectName("muted"); self.target_help.setWordWrap(True)
        self.target_mode.currentIndexChanged.connect(self._update_target_help)
        self._update_target_help()
        objective_form.addRow("Objectif", self.target)
        objective_form.addRow("Compter", self.target_mode)
        objective_form.addRow("", self.target_help)
        layout.addWidget(objective)

        requirements = QGroupBox("Exigences facultatives")
        requirements_form = QFormLayout(requirements)
        self.required_skills = QLineEdit(); self.required_skills.setPlaceholderText("Python, Docker, SQL")
        self.contract_filter = QComboBox(); self.contract_filter.addItems(("Tout contrat", "CDI", "CDD", "Freelance", "Stage", "Alternance"))
        self.education_filter = QLineEdit(); self.education_filter.setPlaceholderText("Ex. Bac+5, Master")
        self.experience_filter = QLineEdit(); self.experience_filter.setPlaceholderText("Ex. 3 ans")
        self.include_unknown = QCheckBox("Inclure les valeurs non précisées")
        self.find_contact_email = QCheckBox("Rechercher un email de contact public")
        self.find_contact_email.setChecked(True)
        self.find_contact_email.setToolTip("Vérifie l’offre, puis les pages publiques explicitement liées. Aucun email n’est deviné.")
        requirements_form.addRow("Compétences", self.required_skills)
        requirements_form.addRow("Contrat", self.contract_filter)
        requirements_form.addRow("Études", self.education_filter)
        requirements_form.addRow("Expérience", self.experience_filter)
        requirements_form.addRow("", self.include_unknown)
        requirements_form.addRow("", self.find_contact_email)
        layout.addWidget(requirements)

        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setText("Options avancées")
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.advanced_toggle.setArrowType(Qt.RightArrow)
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setAccessibleName("Afficher les options avancées")
        layout.addWidget(self.advanced_toggle)
        advanced = QGroupBox()
        advanced_layout = QFormLayout(advanced)
        self.pages = QSpinBox(); self.pages.setRange(1, 100); self.pages.setValue(20)
        self.attempts = QSpinBox(); self.attempts.setRange(1, 10_000); self.attempts.setValue(1_000)
        self.duration = QSpinBox(); self.duration.setRange(1, 12); self.duration.setValue(2)
        self.execution = QComboBox(); self.execution.addItems(("Équilibré — rythme standard", "Prudent — rythme ralenti"))
        advanced_layout.addRow("Pages maximum / recherche", self.pages)
        advanced_layout.addRow("Tentatives et navigations", self.attempts)
        advanced_layout.addRow("Durée maximale (heures)", self.duration)
        advanced_layout.addRow("Exécution", self.execution)
        advanced.setVisible(False)
        self.advanced_options = advanced
        self.advanced_toggle.toggled.connect(
            lambda visible: (advanced.setVisible(visible), self.advanced_toggle.setArrowType(Qt.DownArrow if visible else Qt.RightArrow))
        )
        layout.addWidget(advanced)

        summary = QLabel(); summary.setObjectName("muted"); summary.setWordWrap(True)
        summary.setText("Le moteur applique ces limites pendant la collecte. LinkedIn est vérifié sur cette machine ; Indeed reste désactivé tant que son accès public renvoie 403.")
        layout.addWidget(summary)
        start = QPushButton("Démarrer l’étude")
        start.setObjectName("primary")
        start.setAccessibleName("Démarrer l’étude")
        start.clicked.connect(lambda: start_run(self.run_spec()))
        layout.addWidget(start, alignment=Qt.AlignRight)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _choose_cities(self) -> None:
        selected = {part.strip() for part in self.cities.text().split(",") if part.strip()}
        dialog = CityPickerDialog(self.city_service, selected, self)
        if dialog.exec() == QDialog.Accepted:
            cities = dialog.selected_names()
            if cities:
                self.cities.setText(", ".join(cities))

    def _update_target_help(self) -> None:
        if self.target_mode.currentData() == "descriptions":
            self.target_help.setText("Compte les offres uniques dont la description complète a été récupérée. Les offres incomplètes restent visibles séparément.")
        else:
            self.target_help.setText("Arrête la découverte à l’objectif choisi, puis enrichit ces offres dans la limite du budget restant.")

    def run_spec(self) -> dict[str, object]:
        return {"name": self.study_name.text().strip(), "terms": self.terms.text().strip(),
                "cities": self.cities.text().strip(), "target": self.target.value(),
                "target_mode": self.target_mode.currentData(), "pages": self.pages.value(),
                "attempts": self.attempts.value(), "duration_hours": self.duration.value(),
                "balanced": self.execution.currentIndex() == 0,
                "sources": [name for name, enabled in (("LinkedIn", self.linkedin.isChecked()), ("Indeed", self.indeed.isChecked())) if enabled],
                "required_skills": self.required_skills.text().strip(), "contract": self.contract_filter.currentText(),
                "education": self.education_filter.text().strip(), "experience": self.experience_filter.text().strip(),
                "include_unknown": self.include_unknown.isChecked(), "find_contact_email": self.find_contact_email.isChecked()}


class CollectionThread(QThread):
    completed = Signal(object)
    progress = Signal(object)
    failed = Signal(str)

    def __init__(self, store: StudyStore, run_id: str, spec: RunSpec, stop_event: Event, pause_event: Event) -> None:
        super().__init__()
        self.store, self.run_id, self.spec = store, run_id, spec
        self.stop_event, self.pause_event = stop_event, pause_event

    def run(self) -> None:
        try:
            self._collect()
        except Exception as error:
            self.failed.emit(str(error))

    def _collect(self) -> None:
        adapters = {"linkedin": LinkedInAdapter(), "indeed": IndeedAdapter()}
        transports = {source: HttpTransport("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
                      for source in self.spec.sources if source in adapters}
        interval = 1.0 if self.spec.balanced else 2.5
        result = CollectionRunner(self.store, adapters, transports, TECHNOLOGY_REFERENCES,
                                  min_request_interval_seconds=interval,
                                  event_callback=self.progress.emit).run(
            self.run_id, self.spec, self.stop_event, self.pause_event
        )
        self.completed.emit(result)


class ExportThread(QThread):
    """Generate the default workbook away from the GUI event loop."""

    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, store: StudyStore, run_id: str, destination: str) -> None:
        super().__init__()
        self.store, self.run_id, self.destination = store, run_id, destination

    def run(self) -> None:
        try:
            export_study(self.store, self.run_id, self.destination, include_descriptions=True)
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.completed.emit(self.destination)


class CollectionPage(QWidget):
    results_requested = Signal(str)
    export_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spec: dict[str, object] | None = None
        self._state = "En attente"
        self._progress = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_demo)
        self._thread: CollectionThread | None = None
        self._stop_event = Event()
        self._pause_event = Event()
        self._store: StudyStore | None = None
        self._run_id: str | None = None
        self._run_spec: RunSpec | None = None
        self._auto_export = False
        self._export_thread: ExportThread | None = None
        self._export_path: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.addLayout(page_header("Collecte en cours", "Suivez les opérations réellement exécutées. Les compteurs ne changent qu’après sauvegarde locale."))
        self.state = QLabel("En attente d’une étude")
        self.state.setObjectName("muted")
        layout.addWidget(self.state)
        metrics = QGridLayout()
        self.metrics: dict[str, QLabel] = {}
        for column, (key, title) in enumerate((("found", "Trouvées"), ("unique", "Uniques"), ("details", "Descriptions récupérées"), ("target", "Cible qualifiée"))):
            card = QFrame(); card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            metric = QLabel("0"); metric.setObjectName("metric")
            label = QLabel(title); label.setObjectName("metric-label")
            card_layout.addWidget(metric); card_layout.addWidget(label)
            metrics.addWidget(card, 0, column)
            self.metrics[key] = metric
        layout.addLayout(metrics)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("En attente")
        self.progress.setAccessibleName("Progression vers l’objectif")
        layout.addWidget(self.progress)
        stages = QHBoxLayout()
        self.stage_cards: dict[str, tuple[QFrame, QLabel]] = {}
        for key, title in (("discovering", "1. Découverte"), ("describing", "2. Descriptions"),
                           ("qualifying", "3. Qualification"), ("complete", "4. Terminé")):
            card = QFrame(); card.setObjectName("stage-idle")
            card_layout = QVBoxLayout(card); card_layout.setContentsMargins(12, 9, 12, 9)
            heading = QLabel(title); heading.setObjectName("stage-title")
            status = QLabel("En attente"); status.setObjectName("stage-status")
            card_layout.addWidget(heading); card_layout.addWidget(status)
            stages.addWidget(card)
            self.stage_cards[key] = (card, status)
        layout.addLayout(stages)
        controls = QHBoxLayout()
        self.pause_button = QPushButton("Mettre en pause")
        self.pause_button.clicked.connect(self.pause_or_resume)
        self.stop_button = QPushButton("Arrêter et conserver")
        self.stop_button.clicked.connect(self.stop)
        self.results_button = QPushButton("Voir les résultats")
        self.results_button.setObjectName("primary")
        self.results_button.setEnabled(False)
        self.results_button.clicked.connect(self._open_results)
        self.export_button = QPushButton("Exporter Excel")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_results)
        self.open_excel_button = QPushButton("Ouvrir Excel")
        self.open_excel_button.setEnabled(False)
        self.open_excel_button.clicked.connect(self._open_excel)
        controls.addWidget(self.pause_button); controls.addWidget(self.stop_button)
        controls.addStretch(); controls.addWidget(self.results_button); controls.addWidget(self.export_button); controls.addWidget(self.open_excel_button)
        layout.addLayout(controls)
        activity = QGroupBox("Activité technique")
        activity_layout = QVBoxLayout(activity)
        self.activity = QTextBrowser(); self.activity.setPlainText("Les opérations validées apparaîtront ici. Les identifiants et mots de passe ne sont jamais affichés.")
        activity_layout.addWidget(self.activity)
        layout.addWidget(activity, 1)

    def start(self, spec: dict[str, object]) -> None:
        self._spec = spec; self._state = "En cours"; self._progress = 0
        self._auto_export = False
        self.pause_button.setText("Mettre en pause"); self.pause_button.setEnabled(True); self.stop_button.setEnabled(True)
        self.activity.setPlainText("Prototype local lancé. Le futur moteur y publiera les événements structurés.")
        self._render(); self._timer.start(350)

    def start_live(self, store: StudyStore, run_id: str, run_spec: RunSpec, display_spec: dict[str, object]) -> None:
        self._timer.stop(); self._spec = display_spec; self._state = "Collecte en cours"
        self._store, self._run_id, self._run_spec = store, run_id, run_spec
        self._auto_export = True
        self._export_path = None
        self.open_excel_button.setEnabled(False)
        self._stop_event.clear(); self._pause_event.clear()
        self.pause_button.setText("Mettre en pause"); self.pause_button.setEnabled(True); self.stop_button.setEnabled(True)
        self.results_button.setEnabled(False); self.export_button.setEnabled(False)
        self.activity.setPlainText("Préparation de la collecte HTTP. Les étapes et compteurs vont se mettre à jour ici.")
        self._reset_live_status()
        self._thread = CollectionThread(store, run_id, run_spec, self._stop_event, self._pause_event)
        self._thread.progress.connect(self._on_progress)
        self._thread.completed.connect(self._completed)
        self._thread.failed.connect(self._collection_failed)
        self._thread.start()

    def _collection_failed(self, message: str) -> None:
        self._state = "Collecte interrompue par une erreur"
        self.state.setText(self._state + " — les données déjà sauvegardées restent consultables.")
        self.activity.append(f"<b>Erreur de collecte :</b> {escape(message)}")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self._set_stage("", "")
        has_results = bool(self._store and self._run_id and self._store.offers(self._run_id))
        self.results_button.setEnabled(has_results)
        self.export_button.setEnabled(has_results)

    def _completed(self, result) -> None:
        self._state = result.state.replace("_", " ")
        if result.messages:
            self.activity.append("<br><b>Collecte finalisée.</b>")
        self.pause_button.setEnabled(False); self.stop_button.setEnabled(False)
        if self._store and self._run_id and self._run_spec:
            counters = self._store.counters(self._run_id, self._run_spec.target_mode)
            for key, value in (("found", counters.found), ("unique", counters.unique),
                               ("details", counters.descriptions), ("target", counters.matching_target)):
                self.metrics[key].setText(str(value))
            target_label = "descriptions" if self._run_spec.target_mode is TargetMode.DESCRIPTIONS else "offres uniques"
            self._set_counters(counters, result.attempts)
            self.state.setText(self._completion_message(counters, target_label, result.attempts))
            self._set_stage("complete", "Terminée", done=True)
            has_results = counters.unique > 0
            self.results_button.setEnabled(has_results); self.export_button.setEnabled(has_results)
            if has_results and self._auto_export:
                self._start_automatic_export()
        else:
            self._render()

    def _advance_demo(self) -> None:
        self._progress = min(100, self._progress + 8)
        if self._progress >= 100:
            self._state = "Objectif atteint — données de démonstration"
            self._timer.stop(); self.pause_button.setEnabled(False); self.stop_button.setEnabled(False)
        self._render()

    def _render(self) -> None:
        target = int(self._spec["target"]) if self._spec else 0
        detail_target = target if self._spec and self._spec["target_mode"] == "descriptions" else int(target * .75)
        values = {"found": round(target * self._progress / 70), "unique": round(target * self._progress / 82),
                  "details": round(detail_target * self._progress / 100), "target": min(detail_target, round(detail_target * self._progress / 100))}
        for key, value in values.items(): self.metrics[key].setText(str(value))
        target_label = "descriptions" if self._spec and self._spec["target_mode"] == "descriptions" else "offres uniques"
        self.state.setText(f"{self._state} — objectif: {target} {target_label}; budget: démonstration locale.")

    def _reset_live_status(self) -> None:
        self.progress.setValue(0)
        self.progress.setFormat("0 % — préparation")
        for card, label in self.stage_cards.values():
            card.setObjectName("stage-idle"); card.style().unpolish(card); card.style().polish(card)
            label.setText("En attente")
        self._set_stage("discovering", "Préparation", active=True)

    def _set_counters(self, counters, attempts: int) -> None:
        for key, value in (("found", counters.found), ("unique", counters.unique),
                           ("details", counters.descriptions), ("target", counters.matching_target)):
            self.metrics[key].setText(str(value))
        target = self._run_spec.target if self._run_spec else 0
        percent = min(100, round(counters.matching_target * 100 / target)) if target else 0
        self.progress.setValue(percent)
        self.progress.setFormat(f"{percent} % — {counters.matching_target} / {target} vers l’objectif")
        self.state.setText(f"{self._state} — {counters.matching_target} / {target} vers l’objectif ; tentatives: {attempts}.")

    def _completion_message(self, counters, target_label: str, attempts: int) -> str:
        if not self._store or not self._run_id or not self._run_spec:
            return f"{self._state} — objectif: {target_label}; tentatives: {attempts}."
        counts = self._store.qualification_counts(self._run_id)
        excluded = counts.get("excluded", 0)
        unknown = counts.get("unknown", 0)
        filters = self._run_spec.filters
        selected = [value for value in (filters.contract, filters.education, filters.experience) if value]
        selected.extend(filters.skills)
        if selected and counters.descriptions and not counters.matching_target:
            return (f"{self._state} — {counters.descriptions} descriptions récupérées, mais 0 / "
                    f"{self._run_spec.target} {target_label} correspondent aux filtres ({', '.join(selected)}). "
                    f"À vérifier : {excluded} exclue(s), {unknown} sans valeur indiquée. tentatives: {attempts}.")
        return (f"{self._state} — {counters.descriptions} descriptions récupérées ; "
                f"{counters.matching_target} / {self._run_spec.target} {target_label} vers l’objectif. "
                f"tentatives: {attempts}.")

    def _open_results(self) -> None:
        if self._run_id:
            self.results_requested.emit(self._run_id)

    def _export_results(self) -> None:
        if self._run_id:
            self.export_requested.emit(self._run_id)

    def _start_automatic_export(self) -> None:
        if not self._store or not self._run_id or (self._export_thread and self._export_thread.isRunning()):
            return
        destination = default_export_path(self._run_id)
        self.export_button.setEnabled(False)
        self.export_button.setText("Création du classeur Excel…")
        self.activity.append("<br><b>Génération du classeur Excel en arrière-plan…</b>")
        self._export_thread = ExportThread(self._store, self._run_id, str(destination))
        self._export_thread.completed.connect(self._automatic_export_complete)
        self._export_thread.failed.connect(self._automatic_export_failed)
        self._export_thread.start()

    def _automatic_export_complete(self, destination: str) -> None:
        self._export_path = destination
        self.open_excel_button.setEnabled(True)
        self.export_button.setText("Exporter une autre copie")
        self.export_button.setEnabled(True)
        self.activity.append(f"<b>Classeur Excel créé :</b> {escape(destination)}")
        self.state.setText(self.state.text() + " Classeur Excel créé.")

    def _open_excel(self) -> None:
        if self._export_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._export_path))

    def _automatic_export_failed(self, message: str) -> None:
        self.export_button.setText("Réessayer l’export Excel")
        self.export_button.setEnabled(True)
        self.activity.append(f"<b>Export Excel impossible :</b> {escape(message)}")

    def _set_stage(self, stage: str, text: str, *, active: bool = False, done: bool = False) -> None:
        order = ("discovering", "describing", "qualifying", "complete")
        current = order.index(stage) if stage in order else -1
        for index, key in enumerate(order):
            card, label = self.stage_cards[key]
            if key == stage and active:
                state, label_text = "stage-active", text
            elif index < current or (key == stage and done):
                state, label_text = "stage-done", "Terminé"
            else:
                state, label_text = "stage-idle", "En attente"
            card.setObjectName(state); card.style().unpolish(card); card.style().polish(card)
            label.setText(label_text)

    def _on_progress(self, event) -> None:
        if self._run_spec is None:
            return
        stage_labels = {
            "preparing": "Préparation des sources", "discovering": "Recherche en cours",
            "describing": "Lecture des descriptions", "qualifying": "Extraction des besoins",
            "contact": "Recherche des emails publics",
            "source_unavailable": "Source mise en pause", "complete": "Collecte terminée",
        }
        self._state = stage_labels.get(event.stage, "Collecte en cours")
        visual_stage = event.stage if event.stage in self.stage_cards else "discovering"
        self._set_stage(visual_stage, self._state, active=event.stage != "complete", done=event.stage == "complete")
        self._set_counters(event.counters, event.attempts)
        if event.counters.unique:
            self.results_button.setEnabled(True); self.export_button.setEnabled(True)
        prefix = f"[{event.source.title()}] " if event.source else ""
        self.activity.append(escape(prefix + event.message))

    def pause_or_resume(self) -> None:
        if self._thread and self._thread.isRunning():
            if self._pause_event.is_set():
                self._pause_event.clear(); self._state = "Collecte en cours"; self.pause_button.setText("Mettre en pause")
            else:
                self._pause_event.set(); self._state = "En pause après l'opération active"; self.pause_button.setText("Reprendre")
            if self._store and self._run_id and self._run_spec:
                self._set_counters(self._store.counters(self._run_id, self._run_spec.target_mode), 0)
            self._set_stage("discovering", self._state, active=True)
            return
        if self._timer.isActive():
            self._timer.stop(); self._state = "En pause — résultats déjà persistés"; self.pause_button.setText("Reprendre")
        else:
            self._timer.start(350); self._state = "En cours"; self.pause_button.setText("Mettre en pause")
        self._render()

    def stop(self) -> None:
        if self._thread and self._thread.isRunning():
            self._stop_event.set(); self._state = "Arrêt demandé après l'opération active"; self.stop_button.setEnabled(False)
            if self._store and self._run_id and self._run_spec:
                self._set_counters(self._store.counters(self._run_id, self._run_spec.target_mode), 0)
            self._set_stage("discovering", self._state, active=True)
            return
        self._timer.stop(); self._state = "Arrêtée — étude partielle conservée"; self.pause_button.setEnabled(False); self.stop_button.setEnabled(False); self._render()


class ResultsPage(QWidget):
    def __init__(self, offers: list[JobOffer], export_results=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self); layout.setContentsMargins(32, 28, 32, 28)
        layout.addLayout(page_header("Résultats", "Filtrez les offres et vérifiez chaque besoin à partir de son extrait source."))
        filters = QHBoxLayout()
        self.query = QLineEdit(); self.query.setPlaceholderText("Rechercher entreprise, poste ou compétence"); self.query.setAccessibleName("Filtrer les résultats")
        self.source = QComboBox(); self.source.addItems(("Toutes les sources", "LinkedIn", "Indeed"))
        self.location = QComboBox(); self.location.addItems(("Toutes les villes", "Casablanca", "Rabat"))
        self.qualification = QComboBox(); self.qualification.addItems(("Toutes les qualifications", "matching", "unknown", "excluded"))
        self.count = QLabel(); self.count.setObjectName("muted")
        filters.addWidget(self.query, 1); filters.addWidget(self.source); filters.addWidget(self.location); filters.addWidget(self.qualification); filters.addWidget(self.count)
        self.export_button = QPushButton("Exporter toute l’étude")
        self.include_descriptions = QCheckBox("Inclure les descriptions")
        self.include_descriptions.setChecked(True)
        self.export_button.setEnabled(export_results is not None)
        if export_results:
            self.export_button.clicked.connect(export_results)
        filters.addWidget(self.include_descriptions); filters.addWidget(self.export_button)
        layout.addLayout(filters)
        self.summary = QLabel(); self.summary.setObjectName("muted"); self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.model = OffersModel(offers, self)
        self.proxy = OfferFilter(self); self.proxy.setSourceModel(self.model); self.proxy.setDynamicSortFilter(True)
        self.table = QTableView(); self.table.setModel(self.proxy); self.table.setSelectionBehavior(QTableView.SelectRows); self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.table.setAlternatingRowColors(True); self.table.setSortingEnabled(True); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True); self.table.setAccessibleName("Tableau des offres")
        self._table_settings = QSettings("Corporate Scraper", "v2")
        saved_header = self._table_settings.value("results/header-state")
        if saved_header:
            self.table.horizontalHeader().restoreState(saved_header)
        self.table.horizontalHeader().sectionMoved.connect(self._save_table_layout)
        self.table.horizontalHeader().sectionResized.connect(self._save_table_layout)
        self.detail = QTextBrowser(); self.detail.setOpenExternalLinks(False); self.detail.anchorClicked.connect(QDesktopServices.openUrl)
        self.detail.setAccessibleName("Détail de l’offre")
        splitter = QSplitter(); splitter.addWidget(self.table); splitter.addWidget(self.detail); splitter.setSizes((720, 360))
        layout.addWidget(splitter, 1)
        self.query.textChanged.connect(self._apply_filters); self.source.currentTextChanged.connect(self._apply_filters); self.location.currentTextChanged.connect(self._apply_filters); self.qualification.currentTextChanged.connect(self._apply_filters)
        self.table.selectionModel().currentChanged.connect(self._show_offer)
        self.proxy.rowsInserted.connect(lambda *_: self._update_count()); self.proxy.rowsRemoved.connect(lambda *_: self._update_count())
        self._apply_filters()
        if self.proxy.rowCount(): self.table.selectRow(0); self._show_offer(self.proxy.index(0, 0), QModelIndex())

    def load_offers(self, offers: list[JobOffer], persisted: bool) -> None:
        self.model.replace_offers(offers)
        self.source.clear(); self.source.addItem("Toutes les sources")
        self.source.addItems(sorted({offer.source for offer in offers}))
        self.location.clear(); self.location.addItem("Toutes les villes")
        self.location.addItems(sorted({offer.location for offer in offers}))
        self.qualification.setCurrentIndex(0)
        self.export_button.setEnabled(persisted)
        self._apply_filters()
        if self.proxy.rowCount():
            self.table.selectRow(0)
            self._show_offer(self.proxy.index(0, 0), QModelIndex())
        else:
            self.detail.setPlainText("Aucune offre sélectionnée pour cette étude.")

    def _save_table_layout(self, *_: object) -> None:
        self._table_settings.setValue("results/header-state", self.table.horizontalHeader().saveState())

    def _apply_filters(self) -> None:
        self.proxy.set_query(self.query.text()); self.proxy.set_source(self.source.currentText()); self.proxy.set_location(self.location.currentText()); self.proxy.set_qualification(self.qualification.currentText()); self._update_count()

    def _update_count(self) -> None:
        visible = [self.model.offer_at(self.proxy.mapToSource(self.proxy.index(row, 0)).row())
                   for row in range(self.proxy.rowCount())]
        self.count.setText(f"{len(visible)} offre(s)")
        if not visible:
            self.summary.setText("Aucune donnée pour les filtres actuels.")
            return
        companies = Counter(item.company for item in visible)
        cities = Counter(item.location for item in visible)
        skills = Counter(skill for item in visible for skill in item.skills)
        self.summary.setText(
            f"Entreprises: {', '.join(name for name, _ in companies.most_common(3))}  ·  "
            f"Villes: {', '.join(name for name, _ in cities.most_common(3))}  ·  "
            f"Compétences: {', '.join(name for name, _ in skills.most_common(5))}"
        )

    def _show_offer(self, proxy_index: QModelIndex, _: QModelIndex) -> None:
        if not proxy_index.isValid(): self.detail.clear(); return
        source_index = self.proxy.mapToSource(proxy_index); offer = self.model.offer_at(source_index.row())
        evidence = "".join(f"<li><b>{escape(item.field)} — {escape(item.value)}</b><br>{escape(item.excerpt)} <em>({escape(item.method)})</em></li>" for item in offer.evidence) or "<li>Aucune preuve structurée disponible.</li>"
        description = escape(offer.description).replace("\n", "<br>")
        self.detail.setHtml(
            f"<h2>{escape(offer.title)}</h2><p><b>{escape(offer.company)}</b> · {escape(offer.location)} · {escape(offer.source)}</p>"
            f"<p><b>Contrat:</b> {escape(offer.contract)}<br><b>Expérience:</b> {escape(offer.experience)}<br>"
            f"<b>Niveau / diplôme:</b> {escape(offer.education)}<br>"
            f"<b>Email de contact:</b> {escape(offer.contact_email or 'Non trouvé')}<br>"
            f"<b>Vérification contact:</b> {escape(offer.contact_status)} {('· ' + escape(offer.contact_level)) if offer.contact_level else ''}"
            f"{(' · confiance ' + str(offer.contact_confidence) + '%') if offer.contact_confidence is not None else ''}<br>"
            f"<b>État:</b> {offer.description_status} · Cible: {offer.qualification} · {offer.quality}</p>"
            f"<h3>Compétences</h3><p>{escape(', '.join(offer.skills))}</p><h3>Description</h3><p>{description}</p>"
            f"<h3>Éléments de preuve</h3><ul>{evidence}</ul><p><a href='{escape(offer.url, quote=True)}'>Ouvrir l’offre originale</a></p>"
        )


class HistoryPage(QWidget):
    def __init__(self, store: StudyStore, open_run, parent: QWidget | None = None) -> None:
        super().__init__(parent); layout = QVBoxLayout(self); layout.setContentsMargins(32, 28, 32, 28)
        layout.addLayout(page_header("Historique et planification", "Les études sauvegardées et les presets planifiés apparaîtront ici."))
        card = QFrame(); card.setObjectName("card"); card_layout = QVBoxLayout(card)
        self.summary = QLabel(); card_layout.addWidget(self.summary)
        self.runs = QTextBrowser(); self.runs.setOpenExternalLinks(False); self.runs.anchorClicked.connect(self._open_run); card_layout.addWidget(self.runs)
        refresh = QPushButton("Actualiser l’historique"); refresh.clicked.connect(self.refresh); card_layout.addWidget(refresh, alignment=Qt.AlignRight)
        self.store = store; self.open_run = open_run; self.refresh()
        layout.addWidget(card); layout.addStretch()

    def refresh(self) -> None:
        rows = self.store.list_runs()
        self.summary.setText(f"{len(rows)} étude(s) enregistrée(s)")
        self.runs.setHtml("<hr>".join(
            f"<a href='study://{row['id']}'><b>{escape(row['name'])}</b></a> — {escape(row['state'])}"
            f"<br><small>{row['id']} · {row['updated_at']}</small>" for row in rows
        ) or "Aucune étude enregistrée.")

    def _open_run(self, url: QUrl) -> None:
        if url.scheme() == "study" and url.host():
            self.open_run(url.host())


class SettingsPage(QWidget):
    def __init__(self, storage_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent); layout = QVBoxLayout(self); layout.setContentsMargins(32, 28, 32, 28)
        layout.addLayout(page_header("Paramètres", "Les réglages restent séparés des recherches afin que chaque étude soit reproductible."))
        group = QGroupBox("Par défaut") ; form = QFormLayout(group)
        country = QLineEdit("Maroc (MA)"); country.setReadOnly(True)
        storage = QLineEdit(storage_path) ; storage.setReadOnly(True)
        form.addRow("Zone géographique", country); form.addRow("Études locales", storage)
        self.results_path = QLineEdit(str(results_directory()))
        self.results_path.setAccessibleName("Dossier des résultats Excel")
        browse = QPushButton("Parcourir…")
        browse.clicked.connect(self._browse)
        save = QPushButton("Enregistrer le dossier")
        save.setObjectName("primary")
        save.clicked.connect(self._save)
        open_folder = QPushButton("Ouvrir le dossier des résultats")
        open_folder.clicked.connect(self._open_folder)
        row = QHBoxLayout(); row.addWidget(self.results_path, 1); row.addWidget(browse)
        form.addRow("Résultats Excel", row)
        form.addRow("", save)
        form.addRow("", open_folder)
        self.path_status = QLabel("Par défaut : results dans le dossier de lancement du projet.")
        self.path_status.setWordWrap(True)
        form.addRow("", self.path_status)
        explanation = QLabel("SQLite conserve les études et leurs descriptions après fermeture. Les fichiers Excel sont générés séparément dans le dossier ci-dessus.")
        explanation.setWordWrap(True)
        form.addRow("Sauvegarde locale", explanation)
        layout.addWidget(group); layout.addStretch()

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Dossier des résultats", self.results_path.text())
        if selected:
            self.results_path.setText(selected)

    def _save(self) -> None:
        try:
            path = set_results_directory(self.results_path.text())
        except (OSError, ValueError) as error:
            self.path_status.setText(f"Dossier non enregistré : {error}")
            return
        self.results_path.setText(str(path))
        self.path_status.setText(f"Enregistré. Les prochains exports seront placés dans {path}.")

    def _open_folder(self) -> None:
        directory = results_directory()
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.path_status.setText(str(error))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))


class MainWindow(QMainWindow):
    navigation_labels = ("Nouvelle recherche", "Collecte en cours", "Résultats", "Historique et planification", "Paramètres")

    def __init__(self, offers: list[JobOffer] | None = None, store: StudyStore | None = None, live_enabled: bool = True) -> None:
        super().__init__()
        self.setWindowTitle("Corporate Scraper v2")
        self.resize(1280, 800); self.setMinimumSize(1024, 700)
        self._offers = offers if offers is not None else ([] if live_enabled else sample_offers())
        self.current_run_id: str | None = None
        self.live_enabled = live_enabled
        self.store = store or StudyStore(study_database())
        shell = QWidget(); shell_layout = QHBoxLayout(shell); shell_layout.setContentsMargins(0, 0, 0, 0); shell_layout.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(245); side_layout = QVBoxLayout(sidebar); side_layout.setContentsMargins(8, 8, 8, 16)
        brand = QLabel("Corporate\nScraper"); brand.setObjectName("brand"); side_layout.addWidget(brand)
        subtitle = QLabel("Intelligence recrutement IT"); subtitle.setObjectName("subtitle"); side_layout.addWidget(subtitle)
        self.navigation = QListWidget(); self.navigation.setObjectName("navigation"); self.navigation.setAccessibleName("Navigation principale")
        for label in self.navigation_labels:
            item = QListWidgetItem(label); item.setData(Qt.UserRole, self.navigation.count()); self.navigation.addItem(item)
        side_layout.addWidget(self.navigation, 1)
        version = QLabel("Études locales · v2"); version.setObjectName("subtitle"); side_layout.addWidget(version)
        self.pages = QStackedWidget()
        self.collection_page = CollectionPage()
        self.search_page = SearchPage(self.start_run)
        self.results_page = ResultsPage(self._offers, self.export_current)
        self.history_page = HistoryPage(self.store, self.open_run)
        for page in (self.search_page, self.collection_page, self.results_page, self.history_page, SettingsPage(str(self.store.path))): self.pages.addWidget(page)
        shell_layout.addWidget(sidebar); shell_layout.addWidget(self.pages, 1); self.setCentralWidget(shell)
        self.navigation.currentRowChanged.connect(self._show_page); self.navigation.setCurrentRow(0)
        self.collection_page.results_requested.connect(self.open_run)
        self.collection_page.export_requested.connect(self.export_run)
        if live_enabled and offers is None:
            saved_runs = self.store.list_runs()
            if saved_runs:
                self._load_run_results(saved_runs[0]["id"])
        action = QAction("Nouvelle recherche", self); action.setShortcut(QKeySequence.New); action.triggered.connect(lambda: self.navigation.setCurrentRow(0)); self.addAction(action)

    def start_run(self, spec: dict[str, object]) -> None:
        page = self.collection_page
        if any(thread and thread.isRunning() for thread in (page._thread, page._export_thread)):
            self.navigation.setCurrentRow(1)
            QMessageBox.information(self, "Étude en cours", "Attendez la fin de la collecte et de son export avant de démarrer une autre étude.")
            return
        if not spec["name"] or not spec["terms"] or not spec["cities"] or not spec["sources"]:
            QMessageBox.warning(self, "Recherche incomplète", "Indiquez un nom, des termes, au moins une ville et une source.")
            return
        try:
            run_spec = RunSpec(name=str(spec["name"]), queries=tuple(part.strip() for part in str(spec["terms"]).split(",") if part.strip()),
                               cities=tuple(part.strip() for part in str(spec["cities"]).split(",") if part.strip()),
                               sources=tuple(str(source).casefold() for source in spec["sources"]), target=int(spec["target"]),
                               target_mode=TargetMode(str(spec["target_mode"])), max_pages=int(spec["pages"]),
                               max_attempts=int(spec["attempts"]), max_duration_minutes=int(spec["duration_hours"]) * 60,
                               balanced=bool(spec.get("balanced", True)),
                               find_contact_email=bool(spec.get("find_contact_email", True)),
                               filters=FilterSpec(
                                   skills=tuple(part.strip() for part in str(spec["required_skills"]).split(",") if part.strip()),
                                   contract=None if spec["contract"] == "Tout contrat" else str(spec["contract"]),
                                   education=str(spec["education"]) or None, experience=str(spec["experience"]) or None,
                                   include_unknown=bool(spec["include_unknown"]),
                               ))
            run_id = self.store.create_run(run_spec)
        except ValueError as error:
            QMessageBox.warning(self, "Recherche invalide", str(error)); return
        self.current_run_id = run_id
        if self.live_enabled:
            self.collection_page.start_live(self.store, run_id, run_spec, spec)
        else:
            self.collection_page.start(spec)
        self.history_page.refresh(); self.navigation.setCurrentRow(1)

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        # The sidebar must never reopen the fixture table after a real study
        # has started. It always reflects the active persisted study instead.
        if index == 2 and self.current_run_id:
            self._load_run_results(self.current_run_id)

    def open_run(self, run_id: str) -> None:
        self._load_run_results(run_id)
        self.navigation.setCurrentRow(2)

    def _load_run_results(self, run_id: str) -> None:
        offers: list[JobOffer] = []
        for row in self.store.offers(run_id):
            evidence = tuple(Evidence(item["field"], item["value"], item["excerpt"], item["method"])
                             for item in self.store.evidence_for_offer(row["id"]))
            offers.append(JobOffer(
                identifier=row["source_key"], title=row["title"], company=row["company"] or "Inconnue",
                location=row["location"] or "Non précisée", source=row["source"].title(), posted=row["posted_text"] or "Non précisée",
                skills=tuple(json.loads(row["skills_json"])), experience=row["experience"] or "Non précisée",
                contract=row["contract"] or "Non précisé", description=row["description"] or "",
                url=row["canonical_url"], description_status=row["description_status"], quality=row["quality"], evidence=evidence,
                qualification=row["qualification_status"], record_id=row["id"],
                education=row["education"] or "Non indiqué",
                contact_email=row["contact_email"] or "", contact_status=row["contact_status"] or "not_requested",
                contact_level=row["contact_level"] or "", contact_confidence=row["contact_confidence"],
            ))
        self.current_run_id = run_id
        self.results_page.load_offers(offers, persisted=True)

    def export_run(self, run_id: str) -> None:
        self._load_run_results(run_id)
        self.export_current()

    def export_current(self, checked: bool = False) -> None:
        if not self.current_run_id:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Exporter l'étude", str(default_export_path(self.current_run_id)), "Classeur Excel (*.xlsx)")
        if not destination:
            return
        try:
            export_study(self.store, self.current_run_id, destination,
                         include_descriptions=self.results_page.include_descriptions.isChecked())
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Export impossible", str(error))
        else:
            QMessageBox.information(self, "Export terminé", f"Étude exportée vers :\n{destination}")


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion"); app.setStyleSheet(STYLE)
    palette = app.palette(); palette.setColor(QPalette.Window, QColor("#f4f7fb")); app.setPalette(palette)
    window = MainWindow(); window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())

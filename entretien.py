import tkinter as tk
import random                                   # pour un chois aleatior sur le adress  IP
import time 
import threading                                # utilisation de thread
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright # pilote un vrai navigateur Chromium en arrière-plan, capable d'exécuter le JavaScript
from fake_useragent import UserAgent            # choisir un user aleatoir valide a chaque envoi de requet
from urllib.parse import quote_plus             #suprimer les space saisi par lutilisateur 
from urllib.parse import urlparse
from tkinter import ttk
from rapidfuzz import fuzz                      #libreri  de comparaison
import re                                       # Rgulare Expression detecter et modifier un contenu     


def Normaliser(texte):
    texte = texte.strip().lower() 
    texte = re.sub(r'\s+', ' ', texte) 
    texte = re.sub(r'\s*\+\s*', '+', texte)  # bac + 1 = bac+1
    return texte


def extraire_correspondances(texte_source, liste_reference, seuil=88):
   
    texte_norm = Normaliser(texte_source)
    trouves = []
    for ref in liste_reference:
        ref_norm = Normaliser(ref)
        if ref_norm in texte_norm:
            trouves.append(ref)
            continue
        if len(ref_norm) >= 4:
            score = fuzz.partial_ratio(ref_norm, texte_norm)
            if score >= seuil:
                trouves.append(ref)
    return trouves



def detect_security_mechanism(html):
    html_lower = html.lower()
    indicators = ["captcha","recaptcha",
        "hcaptcha","turnstile","cf-chl-","g-recaptcha","h-captcha","verify you are human","verify you're human",
        "i'm not a robot"
    ]
    ensembe = set()
    # HTML et JavaScript 
    for indicator in indicators:
        if indicator in html_lower:
            ensembe.add(indicator)
    # Scripts
    soup= BeautifulSoup(html, "lxml")
    for script in soup.find_all("script"):
        content = script.get_text(" ", strip=True).lower()

        for indicator in indicators:
            if indicator in content:
                ensembe.add(indicator)
    return ensembe


BASE_URL = "https://www.linkedin.com/jobs/search/"
user=UserAgent()

HEADERS = {
   "User-Agent": user.random
}

Liste_IP=[
"31.59.20.176:6754:uminmkww:7jrjpkwe5h3i",
"31.56.127.193:7684:uminmkww:7jrjpkwe5h3i",
"45.38.107.97:6014:uminmkww:7jrjpkwe5h3i",
"198.105.121.200:6462:uminmkww:7jrjpkwe5h3i",
"64.137.96.74:6641:uminmkww:7jrjpkwe5h3i",
"198.23.243.226:6361:uminmkww:7jrjpkwe5h3i",
"38.154.185.97:6370:uminmkww:7jrjpkwe5h3i",
"84.247.60.125:6095:uminmkww:7jrjpkwe5h3i",
"142.111.67.146:5611:uminmkww:7jrjpkwe5h3i",
"191.96.254.138:6185:uminmkww:7jrjpkwe5h3i"]




VILLES = [
    "Agadir", "Ain Harrouda", "Al Hoceima", "Asilah", "Azrou",
    "Beni Mellal", "Berkane", "Berrechid", "Casablanca", "Chefchaouen",
    "Dakhla", "El Jadida", "Errachidia", "Essaouira", "Fes",
    "Guelmim", "Ifrane", "Kenitra", "Khemisset", "Khouribga",
    "Laayoune", "Larache", "Marrakech", "Meknes", "Mohammedia",
    "Nador", "Ouarzazate", "Oujda", "Rabat", "Safi",
    "Sale", "Settat", "Sidi Kacem", "Tanger", "Taza",
    "Temara", "Tetouan", "Taourirt", "Taroudant", "Tiznit",
]

def Recherche_par_request(postes, localisation, start=0):
    params = {"keywords": postes, "location": localisation, "start": start}
    url=(BASE_URL)
    choix_Proxy = random.choice(Liste_IP)
    ip, port, user_proxy, pwd = choix_Proxy.split(":")
    proxies = {
        "http": f"http://{user_proxy}:{pwd}@{ip}:{port}/",
        "https": f"http://{user_proxy}:{pwd}@{ip}:{port}/"
    }
    HEADERS={"User-Agent":user.random}

    try:
        reponse =requests.get(
        url=url,proxies=proxies,
        headers=HEADERS,   
        params=params, timeout=15)
        reponse.raise_for_status() 
        return reponse.text
    except requests.RequestException as e:
        print(f"Erreur requête : {e}")
        return None


def recuperer_page_playwright(postes, localisation, start=0):
    url = (BASE_URL+f"?keywords={quote_plus(postes)}&location={quote_plus(localisation)}&sortBy=DD&start={start}")

    choix_Proxy = random.choice(Liste_IP)   # on choisi un ip aleatoir
    ip, port, user_proxy, pwd = choix_Proxy.split(":")

    try:
        with sync_playwright() as p:        # lancer le playwright
            browser = p.chromium.launch(    # lancer le web
                headless=True,              # web en arieur plan
                proxy={
                    "server": f"http://{ip}:{port}",
                    "username": user_proxy,
                    "password": pwd
                }
            )
            page = browser.new_page(
                user_agent=user.random)
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded") # charger le l'url et attender le html et le js
            except Exception as e:                                           # intercepter leureur 
                print(f"Erreur lors du chargement de la page : {e}")
                browser.close()                                              # ferfer larieur plan
                return None

            try:
                page.wait_for_selector("ul.jobs-search__results-list", timeout=15000) # attendre et recuperepr le contenu  html ou le dom
            except Exception:# Le sélecteur n'apparait pas on récupère quand même le HTML pour debug
                print("Sélecteur introuvable, LinkedIn bloque peut-être le headless. Récupération du HTML brut pour analyse.")
                html_debug = page.content()
                browser.close()
                return html_debug

            html = page.content()
            browser.close()
            return html

    except Exception as e:
        print(f"Erreur Playwright : {e}")
        return None


def collecter_donnees_brutes(html):
    if not html:
        print("HTML Introuvable !!!")
        return []
    soup = BeautifulSoup(html, "lxml")
    Donner_Bruit = []
    
    for element in soup.select("li"):
        Titre_el = element.select_one(".base-search-card__title")
        Entreprise_el = element.select_one(".base-search-card__subtitle")
        Localisation_el = element.select_one(".job-search-card__location")
        lien_el = element.select_one(".base-card__full-link")
        source=urlparse(BASE_URL).netloc.replace("www.","").split(".")[0]
        Statut_el = element.select_one(".job-search-card_closed-notice, .job-search-cardbenefits, .base-search-card_metadata .job-posting-benefits")
        Statut_offre = "Désactivé" if Statut_el else "Activé"
        try:
            Date_el = element.select_one(".job-search-card__listdate, time")
        except Exception:
            Date_el = None
        texte_element=element.get_text(" ",strip=True).lower()
        Salaire_el = element.select_one(".job-search-card__salary-info")
        contact=element.select_one(".linkedin.sdui.generated.jobseeker.dsl.impl.peopleWhoCanHelp")

        from liste import technologies, niveaux_etudes, experience, type_contrat

        Technologie = extraire_correspondances(texte_element, technologies)
        Niveau      = extraire_correspondances(texte_element, niveaux_etudes)
        Experienc   = extraire_correspondances(texte_element, experience)
        Contrat     = extraire_correspondances(texte_element, type_contrat)

        Titre = Titre_el.get_text(strip=True) if Titre_el else ""
        Entreprise = Entreprise_el.get_text(strip=True) if Entreprise_el else ""
        Localisation = Localisation_el.get_text(strip=True) if Localisation_el else ""
        Lien = lien_el.get("href", "") if lien_el else ""
        Date=Date_el.get_text(strip=True) if Date_el else ""
        Salaire = Salaire_el.get_text(strip=True) if Salaire_el else ""
        Contacte_Recruteur=contact.get_text(strip=True) if contact else ""
        Posting_Date_Status_Detail = (f"{Statut_offre if Statut_offre else 'statut inconnu'} | "f"{Date if Date else 'date inconnue'}")

        if not Titre and not Entreprise:
            continue

        Donner_Bruit.append({
            "Titre ": Titre if Titre else "N/A",
            "Entreprise ": Entreprise if Entreprise else "N/A",
            "Localisation ": Localisation if Localisation else "N/A",
            "Lien ": Lien if Lien else "N/A",
            "Technologie":Technologie if Technologie else "N/A",
            "sourcev ":Statut_offre if Statut_offre else "N/A",
            "date ":Date if Date else "N/A",
            "Contra ":Contrat if Contrat else "N/A",
            "niveau":Niveau if Niveau else "N/A",
            "salaire ":Salaire if Salaire else "N/A",
            "contacte :":Contacte_Recruteur if Contacte_Recruteur else "N/A",
            "Experienc:":Experienc if Experienc else "N/A",
            "Posting_Date_Status_Detail :":Posting_Date_Status_Detail if Posting_Date_Status_Detail else "N/A"
        })

    return Donner_Bruit

stop_event = threading.Event() 

def recherche_thread(Poste_Rechercher, Liste_localisations, nb_pages):
    stop_event.clear() 
    Statu.set(f"Recherche en cours sur : {Poste_Rechercher} {Liste_localisations}")
    toutes_les_donnees = []
    debut=time.time() 
    for ville in Liste_localisations:
        Statu.set(f"Recherche sur le ville de {ville}/{len(Liste_localisations)}")
        for i in range(nb_pages):
            if stop_event.is_set():
                Statu.set(f"Recherche interompue par l'utilisateur a la ville{ville}")
                break

            start = i * 25  
            Statu.set(f"Récupération page {i+1}/{nb_pages} (start={start})...")

            html = Recherche_par_request(Poste_Rechercher, ville, start=start)
            Donner = collecter_donnees_brutes(html)

            if not Donner:
                Statu.set(f"Requête simple insuffisante page {i+1}, Playwright en cours...")
                html = recuperer_page_playwright(Poste_Rechercher, ville, start=start)
                Donner = collecter_donnees_brutes(html)

            if not Donner:
                print(f"Aucun résultat trouvé à la page {i+1}, arrêt de la pagination.")
                break
            
            toutes_les_donnees.extend(Donner)
            if i<nb_pages-1:
                pause = random.uniform(3, 8)    
                Statu.set(f"Pause de {pause:.1f}s avant la prochaine page...")
                time.sleep(pause)               
        if ville!=Liste_localisations[-1]:
            pause_ville=random.uniform(5,12)
            Statu.set(f"Paus de {pause_ville:.1f}s avant la prochaine ville ")
            time.sleep(pause_ville)
        
    duree_totale = time.time() - debut      
    Statu.set(f"donner collecter en {duree_totale}")

    for x in toutes_les_donnees:
        for i, j in x.items():
            print("-"*60)
            print(i," :",j)
        print("")
        print("")
    
    Statu.set(f"Recherche terminée : {len(toutes_les_donnees)} résultat(s) trouvé(s) sur {nb_pages} page(s) en {duree_totale:.1f}s")
    fenetre.after(0,lambda:Bouton_demarrer.config(state="normal")) 
    fenetre.after(0,lambda:Bouton_arrete.config(state="disabled"))

def Recherhce():
    Poste_Rechercher = postes.get()
    Liste_localisations = []
    for ville, var in villes_vars.items():
        if var.get():          
            Liste_localisations.append(ville)

    if not Poste_Rechercher or not Liste_localisations:
        Statu.set("Erreur : veuillez remplir le Poste_Rechercher et la localisation")
        return

    try:
        page = int(Nombre_de_Page.get())
        if page<0:
            return
    except ValueError:
        page = 1

    Bouton_demarrer.config(state="disabled") 
    Bouton_arrete.config(state="normal")
    threading.Thread(       
        target=recherche_thread,
        args=(Poste_Rechercher, Liste_localisations, page),
        daemon=True         
    ).start()               



def Arreter():
    stop_event.set()
    Statu.set("Arrêt demandé, patientez la fin de la page en cours...")
    Bouton_arrete.config(state="disabled")
    
def Exporter():
    Statu.set(f"Tous les contenu Sont Exporter sur Excel")


villes_vars = {}

def mettre_a_jour_tags_villes():
    # Nettoyer les anciens tags
    for widget in cadre_tags.winfo_children():
        widget.destroy()
    
    villes_selectionnees = [ville for ville, var in villes_vars.items() if var.get()]
    nb = len(villes_selectionnees)
    
    # Mettre à jour le texte du bouton principal
    fleche = "▲" if panel_ouvert else "▼"
    Bouton_choisir_ville.config(text=f"Choisir Ville ({nb} villes) {fleche}")    
    # Créer dynamiquement une pastille (tag) avec une croix pour chaque ville sélectionnée
    for ville in villes_selectionnees:
        tag_frame = tk.Frame(cadre_tags, bg="#3caddd", bd=1, relief="solid")
        tag_frame.pack(side="left", padx=2, pady=2)
        
        lbl_nom = tk.Label(tag_frame, text=ville, bg="#e0e0e0", font=("Arial", 9))
        lbl_nom.pack(side="left", padx=(4, 2))
        
        # Fonction locale pour désélectionner la ville au clic sur la croix
        def deselectionner(v=ville):
            villes_vars[v].set(False)
            mettre_a_jour_tags_villes()
            
        btn_croix = tk.Button(tag_frame, text="×", bg="#e0e0e0", bd=0, fg="red", 
                              font=("Arial", 9, "bold"), command=deselectionner, cursor="hand2")
        btn_croix.pack(side="right", padx=(0, 4))


panel_ouvert = False  # état global : panneau ouvert ou fermé

def construire_panel_villes(parent):
    """Construit une seule fois le contenu du panneau de sélection des villes."""
    cadre_recherche = ttk.Frame(parent, padding=(10, 5, 10, 5))
    cadre_recherche.pack(fill="x")

    ttk.Label(cadre_recherche, text="Rechercher :").pack(side="left")

    recherche_var = tk.StringVar()
    champ_recherche = ttk.Entry(cadre_recherche, textvariable=recherche_var)
    champ_recherche.pack(side="left", fill="x", expand=True, padx=(5, 5))

    def effacer_recherche():
        recherche_var.set("")
        champ_recherche.focus_set()

    ttk.Button(cadre_recherche, text="Effacer", command=effacer_recherche).pack(side="left")

    cadre_liste = ttk.Frame(parent)
    cadre_liste.pack(fill="both", expand=True, padx=10, pady=5)

    canvas = tk.Canvas(cadre_liste, highlightthickness=0, height=180)
    scrollbar = ttk.Scrollbar(cadre_liste, orient="vertical", command=canvas.yview)
    cadre_checkboxes = ttk.Frame(canvas)

    cadre_checkboxes.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=cadre_checkboxes, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    cadre_bas = ttk.Frame(parent, padding=10)
    cadre_bas.pack(fill="x")

    label_compteur = ttk.Label(cadre_bas, text="")
    label_compteur.pack(side="left")

    def maj_compteur():
        nb = sum(var.get() for var in villes_vars.values())
        label_compteur.config(text=f"{nb} ville(s) sélectionnée(s)")

    def sur_clic_case():
        maj_compteur()
        mettre_a_jour_tags_villes()
        afficher_villes(recherche_var.get())

    checkbox_widgets = {}
    for ville in sorted(VILLES):
        chk = ttk.Checkbutton(
            cadre_checkboxes,
            text=ville,
            variable=villes_vars[ville],
            command=sur_clic_case,
        )
        checkbox_widgets[ville] = chk

    def afficher_villes(filtre=""):
        for widget in cadre_checkboxes.winfo_children():
            widget.pack_forget()
        filtre = filtre.strip().lower()
        for ville in sorted(VILLES):
            if ville.lower().startswith(filtre):
                checkbox_widgets[ville].pack(anchor="w", pady=2, padx=5)

    afficher_villes()

    def on_recherche_change(*_):
        afficher_villes(recherche_var.get())
    recherche_var.trace_add("write", on_recherche_change)

    maj_compteur()

    ttk.Button(cadre_bas, text="Fermer", command=lambda: toggler_panel_villes()).pack(side="right")


def toggler_panel_villes():
    """Affiche ou masque le panneau de sélection des villes sous le bouton."""
    global panel_ouvert
    if panel_ouvert:
        cadre_panel_villes.grid_remove()
        Bouton_choisir_ville.config(text=f"Choisir Ville ({sum(v.get() for v in villes_vars.values())} villes) ▼")
        panel_ouvert = False
    else:
        cadre_panel_villes.grid()
        Bouton_choisir_ville.config(text=f"Choisir Ville ({sum(v.get() for v in villes_vars.values())} villes) ▲")
        panel_ouvert = True
   
fenetre=tk.Tk()

villes_vars.update({ville: tk.BooleanVar(value=False) for ville in VILLES})

fenetre.title("Scripeur De Recruyement Python")
fenetre.geometry("500x360") # Légèrement agrandi en hauteur pour accueillir les tags
fenetre.columnconfigure(1,weight=1)
fenetre.columnconfigure(2,weight=1)
fenetre.columnconfigure(3,weight=1)
fenetre.rowconfigure(5,weight=1)

tk.Label(fenetre,text="Poste_Rechercher :").grid(row=0,column=0,padx=10,pady=10,sticky="ew")
postes=tk.Entry(fenetre,width=40)
postes.grid(row=0,column=1,columnspan=3,padx=10,pady=10,sticky="ew")

cadre_tags = tk.Frame(fenetre)
cadre_tags.grid(row=1, column=1, columnspan=3, padx=10, pady=2, sticky="ew")

tk.Label(fenetre,text="Localisation (Ville):").grid(row=2,column=0,padx=10,pady=10,sticky="ew")
Bouton_choisir_ville = tk.Button(fenetre, text="Choisir Ville (0 villes) ▼", command=toggler_panel_villes)
Bouton_choisir_ville.grid(row=2,column=1,columnspan=3,padx=10,pady=10,sticky="ew")

# Panneau rétractable, placé juste sous le bouton, caché au démarrage
cadre_panel_villes = ttk.Frame(fenetre, relief="groove", borderwidth=1)
cadre_panel_villes.grid(row=3, column=0, columnspan=4, padx=10, pady=(0,10), sticky="nsew")
construire_panel_villes(cadre_panel_villes)
cadre_panel_villes.grid_remove()   # masqué par défaut

tk.Label(fenetre,text="Page :").grid(row=4,column=0,columnspan=3,padx=10,pady=10,sticky="w")
Nombre_de_Page=tk.Entry(fenetre,width=40)
Nombre_de_Page.grid(row=4,column=1,columnspan=3,padx=10,pady=10,sticky="ew")

Bouton_demarrer=tk.Button(fenetre,text="Démarrer",command=Recherhce,bg="#26e362",width=13)
Bouton_demarrer.grid(row=5,column=0,padx=11,pady=11,sticky="ew")

Bouton_arrete=tk.Button(fenetre,text="Arrêter",command=Arreter,bg="#9DE7FB",width=12)
Bouton_arrete.grid(row=5,column=1,padx=10,pady=10,sticky="ew")
Bouton_arrete.config(state="disabled")

Bouton_Exporter=tk.Button(fenetre,text="Exporter",command=Exporter,bg="#f56462",width=12)
Bouton_Exporter.grid(row=5,column=2,padx=10,pady=10,sticky="ew")

Statu=tk.StringVar()
Statu.set("Saisissez les paramètres puis cliquez sur Démarrer pour lancer la Rechercher")
tk.Label(fenetre, textvariable=Statu, bd=3, relief="sunken", anchor="w").grid(row=6, column=0, columnspan=4, sticky="ew")
fenetre.mainloop()
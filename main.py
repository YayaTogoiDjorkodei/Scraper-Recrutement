import tkinter as tk
import random # pour un chois aleatior sur le adress  IP
import time 
import threading # utilisation de thread
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright # pilote un vrai navigateur Chromium en arrière-plan, capable d'exécuter le JavaScript

BASE_URL = "https://www.linkedin.com/"

HEADERS = {
   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
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

def Recherche_par_request(postes, localisation, start=0):
    params = {"keywords": postes, "location": localisation, "start": start}
    choix_Proxy = random.choice(Liste_IP)
    ip, port, user, pwd = choix_Proxy.split(":")
    proxies = {
        "http": f"http://{user}:{pwd}@{ip}:{port}/",
        "https": f"http://{user}:{pwd}@{ip}:{port}/"
    }

    try:
        reponse =requests.get(
        BASE_URL,proxies=proxies,
        headers=HEADERS,   
        params=params, timeout=15)
        reponse.raise_for_status() 
        return reponse.text
    except requests.RequestException as e:
        print(f"Erreur requête : {e}")
        return None


def recuperer_page_playwright(postes, localisation, start=0):
    from urllib.parse import quote_plus #suprimer les space saisi par lutilisateur 
    url = ("https://www.linkedin.com/jobs/search/"
           f"?keywords={quote_plus(postes)}&location={quote_plus(localisation)}&start={start}")

    choix_Proxy = random.choice(Liste_IP)# on choisi un ip aleatoir
    ip, port, user, pwd = choix_Proxy.split(":")

    try:
        with sync_playwright() as p: # la,cer le playwright
            browser = p.chromium.launch( # lancer le web
                headless=True,
                proxy={
                    "server": f"http://{ip}:{port}",
                    "username": user,
                    "password": pwd
                }
            )
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            )
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded") # charger le l'url et attender le html
            except Exception as e: # intercepter leureur 
                print(f"Erreur lors du chargement de la page : {e}")
                browser.close() # verfer larier plan
                return None

            try:
                page.wait_for_selector("ul.jobs-search__results-list", timeout=15000) # attendre et recuperepr le contenu 
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

        Titre = Titre_el.get_text(strip=True) if Titre_el else ""
        Entreprise = Entreprise_el.get_text(strip=True) if Entreprise_el else ""
        Localisation = Localisation_el.get_text(strip=True) if Localisation_el else ""
        Lien = lien_el.get("href", "") if lien_el else ""

        if not Titre and not Entreprise:
            continue

        Donner_Bruit.append({
            "Titre ": Titre,
            "Entreprise ": Entreprise,
            "Localisation ": Localisation,
            "Lien ": Lien
        })
    return Donner_Bruit


#Fonction exécutée dans le thread séparé
def _recherche_thread(Poste_Rechercher, localisation_Rechercher, nb_pages):
    Statu.set(f"Recherche en cours sur : {Poste_Rechercher} {localisation_Rechercher}")

    toutes_les_donnees = []
    debut=time.time() 
    for i in range(nb_pages):
        start = i * 25  
        Statu.set(f"Récupération page {i+1}/{nb_pages} (start={start})...")

        html = Recherche_par_request(Poste_Rechercher, localisation_Rechercher, start=start)
        Donner = collecter_donnees_brutes(html)

        if not Donner:
            Statu.set(f"Requête simple insuffisante page {i+1}, Playwright en cours...")
            html = recuperer_page_playwright(Poste_Rechercher, localisation_Rechercher, start=start)
            Donner = collecter_donnees_brutes(html)

        if not Donner:
            print(f"Aucun résultat trouvé à la page {i+1}, arrêt de la pagination.")
            break
        toutes_les_donnees.extend(Donner)
        if i<nb_pages-1:
            pause = random.uniform(3, 8)  # nombre aleatoir entre 3 et 8 secondes
            Statu.set(f"Pause de {pause:.1f}s avant la prochaine page...")
            time.sleep(pause) # ajouter un pause
    duree_totale = time.time() - debut  # temps écoulé en sec

    for x in toutes_les_donnees:
        for i, j in x.items():
            print(i, " ", j)
        print("")
    Statu.set(f"Recherche terminée : {len(toutes_les_donnees)} résultat(s) trouvé(s) sur {nb_pages} page(s) en {duree_totale:.1f}s")

def Recherhce():
    Poste_Rechercher = postes.get()
    localisation_Rechercher = localisation.get()

    if not Poste_Rechercher or not localisation_Rechercher:
        Statu.set("Erreur : veuillez remplir le Poste_Rechercher et la localisation")
        return

    try:
        page = int(Nombre_de_Page.get())
        if page<0:
            print("le Nombre de page doit etre un entier")
            return
    except ValueError:
        page = 1

    threading.Thread(   # Lancer la recherche dans un thread séparé pour :
                        #Ne pas bloquer l'interface Tkinter
                        #Éviter le conflit entre le boucl de tkinter et celui de playwright
        target=_recherche_thread,
        args=(Poste_Rechercher, localisation_Rechercher, page),
        daemon=True # arrter le theard qaunt tkinter se ferme
    ).start() # lancer le thread


def Arreter():
    Statu.set(f"Rechercher Terminer cliquer sur Exporter")

def Exporter():
    Statu.set(f"Tous les contenu Sont Exporter sur Excel")


fenetre=tk.Tk()
fenetre.title("Scripeur De Recruyement Python")
fenetre.geometry("500x300")

#positionsjhk
tk.Label(fenetre,text="Poste_Rechercher :").grid(row=0,column=0,padx=10,pady=10,sticky="w")
postes=tk.Entry(fenetre,width=40)
postes.grid(row=0,column=1,columnspan=3,padx=10,pady=10,sticky="w")

#localisation
tk.Label(fenetre,text="Localisation :").grid(row=1,column=0,padx=10,pady=10,sticky="w")
localisation=tk.Entry(fenetre,width=40)
localisation.grid(row=1,column=1,columnspan=3,padx=10,pady=10,sticky="w")    

#page
tk.Label(fenetre,text="Page :").grid(row=2,column=0,columnspan=3,padx=10,pady=10,sticky="w")
Nombre_de_Page=tk.Entry(fenetre,width=40)
Nombre_de_Page.grid(row=2,column=1,columnspan=3,padx=10,pady=10,sticky="w")

#Bouttona
Bouton_demarrer=tk.Button(fenetre,text="Démarrer",command=Recherhce,bg="#26e362",width=13)
Bouton_demarrer.grid(row=3,column=0,padx=11,pady=11,sticky="w")

Bouton_arrete=tk.Button(fenetre,text="Arrêter",command=Arreter,bg="#9DE7FB",width=12)
Bouton_arrete.grid(row=3,column=1,padx=10,pady=10,sticky="w")

Bouton_Exporter=tk.Button(fenetre,text="Exporter",command=Exporter,bg="#f56462",width=12)
Bouton_Exporter.grid(row=3,column=2,padx=10,pady=10,sticky="w")

#statue de recherc
Statu=tk.StringVar() # mettre a jours Statue automatiquement
Statu.set("Saisissez les paramètres puis cliquez sur Démarrer pour lancer la Rechercher")
tk.Label(fenetre, textvariable=Statu, bd=3, relief="sunken", anchor="w").grid(row=4, column=0, columnspan=4, sticky="we")

fenetre.mainloop()

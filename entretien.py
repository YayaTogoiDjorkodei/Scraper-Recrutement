import tkinter as tk
import requests
import random
import threading # lancer de thread 
from bs4 import BeautifulSoup
from playwright.async_api import sync_playwright

BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

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

#recherche avec request 
def Recherche_par_request(postes,localisation,start=0):
    params={"keywords": postes, "location": localisation, "start": start}
    choix_ip=random.choice(Liste_IP)
    ip,port,user,password=choix_ip.split(":")
    proxies = {
        "http": f"http://{user}:{password}@{ip}:{port}/",
        "https": f"http://{user}:{password}@{ip}:{port}/"
    }
    try:
        reponse=requests.get(BASE_URL,headers=HEADERS,proxies=proxies,params=params,timeout=15) #demander le HTML
        reponse.raise_for_status() # verifier s'il ya une ereur
        return reponse.text #retourn donner sous forme de text
    except requests.RequestException: # capter leureur 
        return None

def recuperer_page_playwright(postes,localisation,start=0):
    from urllib.request import quote_plus
    url = ("https://www.linkedin.com/jobs/search/"
           f"?keywords={quote_plus(postes)}&location={quote_plus(localisation)}&start={start}")
    choix_ip=random.choice(Liste_IP)
    ip,port,user,password=choix_ip.split(":")
    try:

        with sync_playwright() as p:
            demarer=p.chromium.launch(
                    headless=True,
                    proxy={
                        "server": f"http://{ip}:{port}",
                        "username": user,
                        "password": password
                    }
                )
            page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
                )            
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded") # charger le l'url et attender le html
            except Exception as e:
                print(f"Eureur de page :{e}")
                demarer.close()
                return None
            try:
                page.wait_for_selector("ul.jobs-search__results-list", timeout=15000)
            except Exception as p:
                    print("Sélecteur introuvable, LinkedIn bloque peut-être le headless. Récupération du HTML brut pour analyse.")
                    html_brud=page.content()
                    demarer.close()
                    return html_brud
            html_brud=page.content()
            demarer.close()
            return html_brud
    except  Exception as p:
        print(f"Erruer de playwright {p}")
        return None
    
#Collection des donner bruit
def collecter_donnees_brutes(html):
    if not html:
        print("HTML Introuvable !!!")
        return[]
    soup=BeautifulSoup(html,"lxml") # trasformation des donner facilemnt navigable 
    Donner_Bruit=[]
    for element in soup.select("li"):
        Titre_el=element.select_one(".base-search-card__title")         #Titre des offre demploi
        Entreprise_el=element.select_one(".base-search-card__subtitle") #nom de Entreprise 
        Localisation_el=element.select_one(".job-search-card__location")# localisation
        lien_el=element.select_one(".base-card__full-link")             # lien

        Titre = Titre_el.get_text(strip=True) if Titre_el else ""
        Entreprise = Entreprise_el.get_text(strip=True) if Entreprise_el else ""
        Localisation=Localisation_el.get_text(strip=True) if Localisation_el else ""
        Lien=lien_el.get("href", "") if lien_el else "",

        if not Titre and not Entreprise:
            continue

        Donner_Bruit.append({"Titre ":Titre,
                             "Entreprise ":Entreprise,
                             "Localisation ":Localisation,
                             "Lien ":Lien})
    return Donner_Bruit


# recuperation des Contenu
def Recherhce():
    Poste_Rechercher=postes.get()
    localisation_Rechercher=localisation.get()
    
    try:
        page=int(Nombre_de_Page.get())
        if page<1:
            page=1
    except ValueError:
        Statu.set("Erreur : le nombre de page doit être un nombre entier")
        return
    
    if not Poste_Rechercher or not localisation_Rechercher:
        Statu.set("Erreur : veuillez remplir le Poste_Rechercher et la localisation")
        return
    Liste_de_Offre=[]
    for Page_actuelle in range(1,page+1):
        start=(Page_actuelle-1)*25
    Statu.set(f"Recherche en cour... : {Poste_Rechercher} {localisation_Rechercher} {Page_actuelle}/{page}")
    fenetre.update_idletasks() 
    html=Recherche_par_request(Poste_Rechercher,localisation_Rechercher,start=start)
    Donner=collecter_donnees_brutes(html)

    if not Donner: # request insufusant
        Statu.set(f"Request insufusant Seluinum en cours....:pag{Page_actuelle})")
        html=recuperer_page_selenium(Poste_Rechercher,localisation_Rechercher,start=start)
        Donner=collecter_donnees_brutes(html)
        Liste_de_Offre.extend(Donner)
    
    for x in Liste_de_Offre:
        for i,j in x.items():
            print(i," ",j)
        print("")

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

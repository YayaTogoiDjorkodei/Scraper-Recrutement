import tkinter as tk
import requests
from bs4 import BeautifulSoup

#seluinum si request echou
from selenium import webdriver # controler le web
from selenium.webdriver.chrome.service import Service       # gere le procesuse en ariere plane 
from selenium.webdriver.chrome.options import Options       # configurer le chrome
from selenium.webdriver.common.by import By                 # permet de recherches les elment par (id , classe ,css etc...)
from selenium.webdriver.support.ui import WebDriverWait      #surveiler larieur plane pour ne pas deploquer
from selenium.webdriver.support import expected_conditions as EC # controler les ELEM?T 
from webdriver_manager.chrome import ChromeDriverManager # telecharegr le version compatiple avec le pc 

BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
#BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
#https://www.linkedin.com/jobs/

HEADERS = {#passer au serveur comme un vraie navigateur
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/124.0.0.0 Safari/537.36"  
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

#recherche avec request 
def Recherche_par_request(postes,localisation,start=0):
    params={"keywords": postes, "location": localisation, "start": start}
    try:
        reponse=requests.get(BASE_URL,headers=HEADERS,params=params,timeout=15) #demander le HTML
        reponse.raise_for_status() # verifier s'il ya une ereur
        return reponse.text #retourn donner sous forme de text
    except requests.RequestException: # capter leureur 
        return None

def recuperer_page_selenium(postes,localisation,start=0):
    from urllib.parse import quote_plus # organoser les donner sous forme logique 
    url=("https://www.linkedin.com/jobs/search/"
        f"?keywords={quote_plus(postes)}&location={quote_plus(localisation)}&start={start}")
    
    options=Options()                                           #configuration de chrome avant de lancer
    options.add_argument("--headless=new")                      #configuration de  chroem en arieur plan
    service=Service(ChromeDriverManager().install())            # installer la version de lancement  compatible ave le pc 
    drive=webdriver.chrome(service=service,options=options)     #lancer seluinum

    try:
        drive.get(url) # recuperer les donner 
        WebDriverWait(drive,15).until(EC.presence_of_element_located(By.CSS_SELECTOR,"ul.jobs-search__results-list")) # 15 seconde avant d'interompre le serveur 
        return drive.page_source 
    except Exception:
        return None
    finally:
        drive.quit()  # fermer l'arieur plan


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

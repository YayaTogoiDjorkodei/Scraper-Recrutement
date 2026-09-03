def charger_liste_ip(chemin="IP_proxies.txt"):
    try:
        with open(chemin , "r",encoding="UTF-8") as f:
            return [ligne.strip() for ligne in f if ligne.strip()]
    except Exception as e:
        print(f"Fichier {chemin} introuvable")
        return []

import requests
import random
choix_Proxy = random.choice(charger_liste_ip())
ip, port, user_proxy, pwd = choix_Proxy.split(":")

proxies = {
    "http": f"http://{user_proxy}:{pwd}@{ip}:{port}/",
    "https": f"http://{user_proxy}:{pwd}@{ip}:{port}/"
}
r = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
print(r.status_code, r.text)
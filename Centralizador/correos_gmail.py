import time
from curl_cffi import requests
import random
import os
import threading
import queue

class ProxyMonitor:
    """Monitor de proxies usando curl_cffi para health checks.
    Soporta lista N de proxies y añade iteración estocástica y sigilo."""

    def _cargar_proxies(self):
        """Lee proxies del archivo .txt, asegurando el formato correcto."""
        if os.path.exists("proxies_buenos.txt"):
            with open("proxies_buenos.txt", "r") as f:
                file_proxies = []
                for l in f:
                    l = l.strip()
                    if l and not l.startswith("#"):
                        if not l.startswith("socks") and not l.startswith("http"):
                            l = "socks5://" + l
                        file_proxies.append(l)
                if file_proxies:
                    self.proxy_list = file_proxies

    def __init__(self, *default_proxies):
        self.proxy_list = list(default_proxies)
        self._cargar_proxies()
        self.valid_queue = queue.Queue(maxsize=15)
        self.running = True

    def stop(self):
        self.running = False

    def monitor_loop(self):
        """Bucle de rotación: rota cada 3 minutos, con demoras aleatorias para evitar patrones."""
        proxy_index = 0
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        
        while self.running:
            if self.valid_queue.full():
                time.sleep(2)
                continue
                
            self._cargar_proxies()
            if not self.proxy_list:
                time.sleep(5)
                continue

            test_proxy = self.proxy_list[proxy_index]
            print(f"[{self.__class__.__name__}] Buscando proxy. (Recámara al {self.valid_queue.qsize()}/{self.valid_queue.maxsize}). Candidato: {test_proxy}")
            
            try:
                browser = random.choice(["chrome110", "edge101"])
                resp = requests.get("https://accounts.google.com/v3/signin/identifier", 
                                    timeout=8, 
                                    impersonate=browser, 
                                    proxies={"http": test_proxy, "https": test_proxy},
                                    headers=headers)
                
                if resp.status_code in [200, 302]:
                    print(f"[{self.__class__.__name__}] PING EXITOSO. Almacenando bala viva de {test_proxy}")
                    
                    self.valid_queue.put(test_proxy)
                    
                    proxy_index = (proxy_index + 1) % len(self.proxy_list)
                    time.sleep(0.5)
                else:
                    proxy_index = (proxy_index + 1) % len(self.proxy_list)
                    time.sleep(0.2)
            except Exception:
                proxy_index = (proxy_index + 1) % len(self.proxy_list)
                time.sleep(0.2)



# Configuración de Correos Gmail - URL de registro
GMAIL_URL = "https://accounts.google.com/v3/signin/identifier?authuser=0&continue=https%3A%2F%2Fmail.google.com%2Fmail%2F&ec=GAlAFw&hl=es-419&service=mail&flowName=GlifWebSignIn&flowEntry=AddSession&dsh=S2117206237%3A1775576771081254"

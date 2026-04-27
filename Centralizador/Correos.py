import random
import time
from curl_cffi import requests
import os
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
        # (Eliminada la configuración de 'headers' manual para no corromper curl_cffi)
        
        while self.running:
            if self.valid_queue.full():
                # Si la recámara de proxies vivos está llena, no gasta internet testeando más
                time.sleep(2)
                continue
                
            self._cargar_proxies()
            if not self.proxy_list:
                time.sleep(5)
                continue

            test_proxy = self.proxy_list[proxy_index]
            print(f"[{self.__class__.__name__}] Buscando proxy. (Recámara al {self.valid_queue.qsize()}/{self.valid_queue.maxsize}). Candidato: {test_proxy}")
            
            try:
                # Rotación masiva de perfiles para aplicar distintos fingerprints automáticamente
                browsers_disponibles = [
                    "chrome100", "chrome101", "chrome104", "chrome105", "chrome106", 
                    "chrome107", "chrome108", "chrome109", "chrome110", "chrome111", 
                    "chrome112", "chrome114", "chrome116", "chrome117", "chrome118", 
                    "chrome119", "chrome120", "edge99", "edge101", "safari15_3", "safari15_5"
                ]
                browser = random.choice(browsers_disponibles)
                resp = requests.get("https://signup.live.com", 
                                    timeout=8, 
                                    impersonate=browser, 
                                    proxies={"http": test_proxy, "https": test_proxy})
                
                if resp.status_code == 200:
                    print(f"[{self.__class__.__name__}] PING EXITOSO. Almacenando bala viva de {test_proxy}")
                    
                    self.valid_queue.put(test_proxy)
                    
                    proxy_index = (proxy_index + 1) % len(self.proxy_list)
                    time.sleep(0.5) # Breve respiro del CPU
                else:
                    proxy_index = (proxy_index + 1) % len(self.proxy_list)
                    time.sleep(0.2)
            except Exception:
                proxy_index = (proxy_index + 1) % len(self.proxy_list)
                time.sleep(0.2)

# Configuración de Correos (Outlook) - URL de registro
CORREOS_URL = "https://signup.live.com/signup?lcid=3082&cobrandid=ab0455a0-8d03-46b9-b18b-df2f57b9e44c&uiflavor=web&lic=1&mkt=es-ES"

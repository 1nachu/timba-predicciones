import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

#Truco para importar modulos de la carpeta src/
sys.path.insert(0, str(Path(__file__).parent /'src'))

from football_api_client import FootballDataClient
from live_scores import LiveScoresManager,DefaultCallbacks

#Cargar API
load_dotenv()
API_KEY = os.getenv('FOOTBALL_DATA_API_KEY')

if not API_KEY:
	print("ERROR: No se encontro FOOTBALL_DATA_API_KEY en el archivo .env")
	sys.exit(1)

def main():
	print("Iniciando Timba Live Scores Service...")

	#1 Conectar Cliente
	client = FootballDataClient(API_KEY)

	#2 Iniciar Gestor
	manager = LiveScoresManager(client)

	#3 Registrar Log(para ver que pasa)
	manager.register_callback(DefaultCallbacks.log_callback)

	#4 Arrancar el Polling(chequeo automatico)
	#Intervalo 30s para no saturar la API gratuita
	manager.start_polling(interval=30)

	#5 Bucle infinito para mantener vivo el servicio
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		print("Deteniendo Servicio...")
		manager.stop_polling()

if __name__ == "__main__":
	main()

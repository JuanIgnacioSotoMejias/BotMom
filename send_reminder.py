"""
Recordatorio de Medicinas via WhatsApp (CallMeBot)
Usado por GitHub Actions — 100% gratis, funciona desde Venezuela.
"""

import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime

# Variables desde GitHub Secrets
MI_NUMERO = os.environ["MI_NUMERO"]      # solo el numero: 584243591230
API_KEY   = os.environ["CALLMEBOT_KEY"]  # clave que te da CallMeBot

def enviar(medicinas: str, nota: str = ""):
    hora = datetime.utcnow()
    # Convertir UTC a Venezuela (UTC-4)
    from datetime import timedelta
    hora_vet = hora - timedelta(hours=4)
    hora_fmt = hora_vet.strftime("%I:%M %p")

    lista = "\n".join([f"  💊 {m.strip()}" for m in medicinas.split(",")])
    nota_txt = f"\n📌 {nota}" if nota else ""

    cuerpo = (
        f"🔔 Recordatorio de Medicinas\n"
        f"🕐 {hora_fmt} (Venezuela)\n\n"
        f"Es hora de tomar:\n"
        f"{lista}"
        f"{nota_txt}\n\n"
        f"✅ No olvides tomarlas con agua!"
    )

    texto_encoded = urllib.parse.quote(cuerpo)
    url = f"https://api.callmebot.com/whatsapp.php?phone={MI_NUMERO}&text={texto_encoded}&apikey={API_KEY}"

    try:
        with urllib.request.urlopen(url) as response:
            resultado = response.read().decode()
            print(f"✅ Enviado OK: {medicinas}")
            print(f"   Respuesta API: {resultado[:100]}")
    except Exception as e:
        print(f"❌ Error al enviar: {e}")
        sys.exit(1)

if __name__ == "__main__":
    medicinas = sys.argv[1] if len(sys.argv) > 1 else "Medicina"
    nota      = sys.argv[2] if len(sys.argv) > 2 else ""
    enviar(medicinas, nota)

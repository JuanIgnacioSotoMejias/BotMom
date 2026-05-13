"""
BotMom — Recordatorio de Medicinas vía WhatsApp (CallMeBot)
Usado por GitHub Actions para Venezuela. 100% gratuito y sin dependencias.
"""

import os
import sys
import time
import logging
import argparse
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

# ─── Configuracion de Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Constantes ──────────────────────────────────────────────────────────────
# Venezuela Time = UTC-4 (sin cambio de horario de verano)
VET_OFFSET: timedelta = timedelta(hours=-4)

# Variables de entorno desde GitHub Secrets
MI_NUMERO: Optional[str] = os.environ.get("MI_NUMERO")      # ej: 584243591230
API_KEY: Optional[str]   = os.environ.get("CALLMEBOT_KEY")  # clave de CallMeBot

# ─── Horario de Medicinas ─────────────────────────────────────────────────────
# Ordenado cronológicamente por hora VET.
# Formato: "cron_utc": ("Nombre", "nota_opcional")
SCHEDULE_MAP: Dict[str, Tuple[str, str]] = {
    "0 11 * * *":  ("ACTIVACION",   "El sistema está en línea y listo para los recordatorios de hoy."),
    "0 12 * * *":  ("Spirulina",    "Primera dosis del día"),            # 08:00 VET
    "30 12 * * *": ("Asaprol",      ""),                                  # 08:30 VET
    "0 14 * * *":  ("Muxer",        "Tomar con agua"),                    # 10:00 VET
    "0 15 * * *":  ("Detox Complex",""),                                  # 11:00 VET
    "0 16 * * *":  ("Omega 3",      "Tomar con el almuerzo"),             # 12:00 VET
    "0 20 * * *":  ("Spirulina",    "Segunda dosis de Spirulina"),        # 16:00 VET
    "0 23 * * *":  ("Magnesio",     "Tomar con cena o antes de dormir"), # 19:00 VET
    "0 0 * * *":   ("Ashwagandha",  "Tomar antes de dormir"),            # 20:00 VET
    "0 2 * * *":   ("Muxer",        "Tomar con agua"),                    # 22:00 VET
    "0 3 * * *":   ("Detox Complex",""),                                  # 23:00 VET
    "0 4 * * *":   ("Spirulina",    "Última dosis del día"),             # 00:00 VET
    "0 5 * * *":   ("DESACTIVACION","Ronda finalizada. Hasta mañana."),
}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _hora_vet() -> str:
    """Devuelve la hora actual en Venezuela formateada en español (ej: 08:30 AM)."""
    ahora_utc = datetime.now(timezone.utc)
    ahora_vet = ahora_utc + VET_OFFSET
    hora, minuto = ahora_vet.hour, ahora_vet.minute
    periodo = "AM" if hora < 12 else "PM"
    hora_12 = hora % 12 or 12
    return f"{hora_12:02d}:{minuto:02d} {periodo}"


def _construir_mensaje(medicinas: str, nota: str) -> str:
    """
    Construye el cuerpo del mensaje de WhatsApp según el tipo de recordatorio.

    Args:
        medicinas: Nombre del medicamento(s) o clave especial ('ACTIVACION'/'DESACTIVACION').
        nota:      Texto adicional opcional para el mensaje.

    Returns:
        Cadena de texto lista para enviar via WhatsApp.
    """
    hora_fmt = _hora_vet()

    if medicinas == "ACTIVACION":
        return (
            f"✅ *BotMom Activado*\n"
            f"🕐 {hora_fmt} (Venezuela)\n\n"
            f"_{nota}_"
        )

    if medicinas == "DESACTIVACION":
        return (
            f"💤 *BotMom Desactivado*\n"
            f"🕐 {hora_fmt} (Venezuela)\n\n"
            f"_{nota}_"
        )

    # Recordatorio normal: soporta múltiples medicinas separadas por coma
    lista = "\n".join(f"  💊 {m.strip()}" for m in medicinas.split(","))
    pie   = f"\n\n📌 {nota}" if nota else ""

    return (
        f"🔔 *Recordatorio de Medicinas*\n"
        f"🕐 {hora_fmt} (Venezuela)\n\n"
        f"Es hora de tomar:\n"
        f"{lista}"
        f"{pie}\n\n"
        f"✅ No olvides tomarlas con agua! 💧"
    )


# ─── Lógica de Envío ──────────────────────────────────────────────────────────
def enviar(medicinas: str, nota: str = "", retries: int = 3) -> None:
    """
    Construye y envía un mensaje de WhatsApp a través de la API de CallMeBot,
    con reintentos automáticos en caso de fallo de red.

    Args:
        medicinas: Nombre del medicamento(s) o accion (ej. 'ACTIVACION').
        nota:      Mensaje extra a enviar. Por defecto vacío.
        retries:   Número máximo de intentos de conexión. Por defecto 3.
    """
    cuerpo        = _construir_mensaje(medicinas, nota)
    texto_encoded = urllib.parse.quote(cuerpo)
    url           = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={MI_NUMERO}&text={texto_encoded}&apikey={API_KEY}"
    )

    for intento in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                resultado = response.read().decode()
                logger.info("✅ Enviado OK: %s", medicinas)
                logger.info("   Respuesta API: %s", resultado[:100])
                return  # Éxito — salir del loop
        except HTTPError as e:
            # No loguear la URL para evitar exponer el número y apikey en logs públicos
            logger.warning("⚠️ Intento %d/%d — HTTPError %s: %s", intento + 1, retries, e.code, e.reason)
        except URLError as e:
            logger.warning("⚠️ Intento %d/%d — URLError: %s", intento + 1, retries, e.reason)

        if intento < retries - 1:
            logger.info("   Reintentando en 5 segundos...")
            time.sleep(5)
        else:
            logger.error("❌ No se pudo enviar el mensaje tras %d intentos.", retries)
            sys.exit(1)


# ─── Punto de Entrada ─────────────────────────────────────────────────────────
def main() -> None:
    """
    Parsea los argumentos de línea de comandos y ejecuta el envío.
    Modo cron:   --cron "0 12 * * *"   (lo pasa GitHub Actions)
    Modo manual: --medicina "Spirulina" [--nota "texto"]
    """
    parser = argparse.ArgumentParser(
        description="BotMom — Recordatorio de medicinas via WhatsApp (CallMeBot)."
    )
    parser.add_argument(
        "--cron",
        type=str,
        help="Expresion cron que disparó la ejecución (busca en SCHEDULE_MAP).",
    )
    parser.add_argument(
        "--medicina",
        type=str,
        help="Nombre de la medicina a enviar en modo manual.",
    )
    parser.add_argument(
        "--nota",
        type=str,
        default="",
        help="Nota adicional opcional (solo en modo manual).",
    )

    args = parser.parse_args()

    # Validacion temprana de credenciales
    if not MI_NUMERO or not API_KEY:
        logger.error("❌ Faltan las variables de entorno MI_NUMERO y/o CALLMEBOT_KEY.")
        sys.exit(1)

    if args.cron:
        entrada = SCHEDULE_MAP.get(args.cron)
        if entrada:
            med, nota = entrada
            logger.info("🕒 Cron '%s' -> Medicina: %s", args.cron, med)
            enviar(med, nota)
        else:
            # Cron no mapeado no es un error crítico — el workflow puede tener
            # horarios que no generan mensajes (ej. horarios de mantenimiento)
            logger.warning("⚠️ Cron '%s' no encontrado en SCHEDULE_MAP. Sin accion.", args.cron)
    elif args.medicina:
        logger.info("🚀 Modo manual -> Medicina: %s", args.medicina)
        enviar(args.medicina, args.nota)
    else:
        logger.error("❌ Debes especificar '--cron' o '--medicina'. Usa -h para ayuda.")
        sys.exit(1)


if __name__ == "__main__":
    main()

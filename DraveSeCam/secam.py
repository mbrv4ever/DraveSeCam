# -*- coding: utf-8 -*-
"""
DraveSeCam - lokale, offline bewakingscamera (Dravenlock).
Live beeld, bewegingsdetectie en snapshots. Donationware. PyQt6 + OpenCV.
Geen internet. (c) Dravenlock.
"""
import os
import sys
import json
import locale
import datetime
import time

import numpy as np

# Demp OpenCV's backend-waarschuwingen (bv. de DSHOW-melding) in het CMD-venster.
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

# Geluid: microfoon (sounddevice) + samenvoegen met beeld (ffmpeg via imageio-ffmpeg).
import wave
import subprocess
import smtplib
import ssl as _ssl
import mimetypes
import socket
import secrets
import threading
import http.server
from urllib.parse import urlparse, parse_qs
from email.message import EmailMessage
try:
    import sounddevice as sd
except Exception:  # pragma: no cover
    sd = None
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # pragma: no cover
    FFMPEG_EXE = None

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSlider, QListWidget, QFrame, QSizePolicy,
    QDialog, QTextBrowser, QStatusBar, QCheckBox, QLineEdit, QFormLayout, QScrollArea,
)
from PyQt6.QtGui import QIcon, QPixmap, QImage, QAction, QFont
from PyQt6.QtCore import Qt, QTimer, QLocale, QSize, QThread, pyqtSignal

APP_NAAM = "DraveSeCam"
APP_VERSIE = "0.6.4"
ORG = "Dravenlock"

# ---- huisstijl ----
BG = "#0e0e11"
PANEEL = "#16161b"
PANEEL2 = "#1c1c22"
TEKST = "#d4d4d4"
MUTED = "#8a8a94"
ACCENT = "#6fa3d6"
LINE = "#23232b"
WARN = "#d68a6f"
GOED = "#7fb069"


def _basis_map():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


def _app_map():
    """De map waar de app/EXE staat (voor het bewaren van opnames - portable)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _kies_data_map():
    """Bewaar opnames naast de app. Als dat niet kan (alleen-lezen), wijk uit naar de
    gebruikersmap, zodat de app nooit vastloopt."""
    naast_app = os.path.join(_app_map(), "DraveSeCam-data")
    try:
        os.makedirs(naast_app, exist_ok=True)
        toets = os.path.join(naast_app, ".schrijftest")
        with open(toets, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(toets)
        return naast_app
    except Exception:
        thuis = os.path.join(os.path.expanduser("~"), "DraveSeCam-data")
        try:
            os.makedirs(thuis, exist_ok=True)
        except Exception:
            pass
        return thuis


HIER = _basis_map()
ASSETS = os.path.join(HIER, "assets")
DATA_MAP = _kies_data_map()
SNAPSHOT_MAP = os.path.join(DATA_MAP, "opnames")
CONFIG = os.path.join(DATA_MAP, "instellingen.json")

_TAAL = "nl"

# ======================================================================
# Vertalingen
# ======================================================================
VERTALINGEN = {
    "nl": {
        "titel": "DraveSeCam - bewaking",
        "camera": "Camera",
        "verversen": "Camera's zoeken",
        "start": "Start camera",
        "stop": "Stop camera",
        "bewaking_aan": "Bewaking AAN",
        "bewaking_uit": "Bewaking UIT",
        "gevoeligheid": "Gevoeligheid",
        "laag": "laag",
        "hoog": "hoog",
        "snapshot": "Foto nu maken",
        "open_map": "Open opnames-map",
        "open_logboek": "Open logboek",
        "log_start": "Logboek gestart.",
        "gebeurtenissen": "Gebeurtenissen",
        "klaar": "Klaar. Kies een camera en druk op Start camera.",
        "opstarten": "Bezig met opstarten\nCamera zoeken...",
        "opstarten_kort": "Bezig met opstarten - camera zoeken...",
        "geen_camera": "Geen camerabeeld.\nKies een camera en druk op Start camera.",
        "zoeken": "Camera's zoeken...",
        "gevonden": "{n} camera('s) gevonden.",
        "geen_gevonden": "Geen camera gevonden. Is er een webcam aangesloten?",
        "geen_gevonden_hint": "Geen camera gevonden. Controleer in Windows: Instellingen > Privacy en beveiliging > Camera (zet 'Camera-toegang' en 'Apps toegang geven' AAN). Sluit ook andere apps die de camera gebruiken (Teams, Zoom, Camera-app).",
        "gestart": "Camera gestart.",
        "gestopt": "Camera gestopt.",
        "fout_open": "Kon camera niet openen.",
        "beweging": "Beweging gedetecteerd",
        "foto_opgeslagen": "Foto opgeslagen: {naam}",
        "bewaking_actief": "Bewaking actief.",
        "bewaking_gestopt": "Bewaking gestopt.",
        "geen_cv2": "OpenCV ontbreekt. Installeer met:  pip install opencv-python",
        "menu_bestand": "Bestand",
        "menu_taal": "Taal",
        "menu_help": "Help",
        "afsluiten": "Afsluiten",
        "snelgids": "Snelgids (F1)",
        "over": "Over DraveSeCam",
        "donatie": "Doneren",
        "beweging_pct": "Beweging: {p:.1f}%",
        "bij_beweging": "Bij beweging",
        "modus_foto": "Foto maken",
        "modus_video": "Video opnemen",
        "modus_beide": "Foto + video",
        "opname_bezig": "\u25cf Video-opname bezig...",
        "video_gestart": "Video-opname gestart",
        "video_opgeslagen": "Video opgeslagen: {naam} ({n} beelden)",
        "video_mislukt": "Video-opname lukt niet (geen geschikte codec gevonden).",
        "video_nu": "Video (5 sec)",
        "eerst_starten": "Start eerst de camera.",
        "video_leeg": "Video bleef leeg - de codec schreef niets weg. Probeer opnieuw.",
        "geluid_opnemen": "Geluid opnemen (microfoon)",
        "geluid_niet": "Geluid niet beschikbaar (pakket ontbreekt)",
        "geluid_bezig": "Geluid toevoegen aan video...",
        "video_met_geluid": "Video met geluid opgeslagen: {naam}",
        "geluid_mislukt": "Geluid toevoegen mislukt - video zonder geluid bewaard.",
        "email_bij_beweging": "E-mail sturen bij beweging",
        "email_instellen": "E-mail instellen...",
        "email_titel": "E-mailinstellingen",
        "email_uitleg": "Stuur automatisch een e-mail (met foto) bij beweging. Let op: hiervoor "
                        "gebruikt de app internet. Gebruik bij voorkeur een app-wachtwoord.",
        "email_dienst": "Maildienst",
        "email_app_ww_tip": "Tip: voor deze dienst heb je meestal een app-wachtwoord nodig "
                            "(zet eerst 2-staps-verificatie aan).",
        "email_ms_tip": "Let op: Microsoft blokkeert vaak wachtwoord-login voor mail "
                        "(moderne authenticatie/OAuth vereist). Werkt mogelijk niet.",
        "email_host": "Server (SMTP)",
        "email_poort": "Poort",
        "email_beveiliging": "Beveiliging",
        "email_gebruiker": "Gebruikersnaam",
        "email_adres": "Jouw e-mailadres",
        "email_wachtwoord": "Wachtwoord (app-wachtwoord)",
        "email_van": "Van (afzender)",
        "email_naar": "Sturen naar (leeg = jezelf)",
        "email_bijlage_label": "Meesturen",
        "bijlage_foto": "Foto",
        "bijlage_video": "Video (kan groot zijn)",
        "bijlage_beide": "Foto + video",
        "email_modus_foto": "Foto",
        "email_modus_video": "video",
        "email_modus_beide": "foto + video",
        "email_aan_modus": "E-mail aan - meesturen: {wat}",
        "email_tekst_video": "Er is beweging gedetecteerd op {tijd}.\nDe video zit als bijlage.\n\n- DraveSeCam",
        "video_te_groot": "Video te groot om te mailen ({mb} MB) - niet verstuurd.",
        "diag_uit": "staat uit - zet het vinkje 'E-mail sturen bij beweging' aan.",
        "diag_modus_video": "modus Video - de mail komt zodra de clip klaar is.",
        "diag_geen_server": "geen server ingesteld (open E-mail instellen).",
        "diag_wachttijd": "wachttijd actief (zie 'Minuten tussen mails').",
        "diag_bewaking_uit": "bewaking staat uit.",
        "diag_geen_clip": "geen videoclip gevonden om te mailen.",
        "email_aan_kort": "E-mail: AAN",
        "stream_aan": "Live meekijken (netwerk)",
        "stream_open": "Open live",
        "stream_uitleg": "Bekijk het camerabeeld live in een browser op hetzelfde wifi-netwerk.",
        "stream_actief": "Live meekijken: {url}",
        "stream_gestopt": "Live meekijken gestopt.",
        "stream_fout": "Kon de live-server niet starten (poort bezet?).",
        "mail_live_link": "Live meekijken (zelfde netwerk):",
        "stream_extern": "Ook van buitenaf (port forwarding)",
        "adres_knop": "Adressen / router...",
        "adres_titel": "Meekijken van buitenaf instellen",
        "stream_extern_tip": "Voor kijken van buiten je huis. Vereist port forwarding in je router. "
                             "De mail krijgt dan je publieke internet-adres. Houd de sleutel geheim.",
        "stream_extern_aan": "Van buitenaf AAN - de mail krijgt je publieke adres (zorg voor port forwarding in je router).",
        "stream_extern_uit": "Van buitenaf UIT - mail gebruikt weer het lokale adres.",
        "mail_live_link_extern": "Live meekijken (van overal, via port forwarding):",
        "email_uit_kort": "E-mail: UIT (vinkje 'E-mail sturen bij beweging')",
        "email_interval": "Minuten tussen mails",
        "email_test": "Testmail versturen",
        "email_opslaan": "Opslaan",
        "email_annuleer": "Annuleren",
        "email_onvolledig": "Vul minstens server en ontvanger in.",
        "email_test_bezig": "Testmail wordt verstuurd...",
        "email_test_ok": "Testmail verstuurd. Controleer je inbox.",
        "email_test_fout": "Versturen mislukt: {fout}",
        "email_bezig": "E-mail wordt verstuurd...",
        "email_verstuurd": "E-mail verstuurd bij beweging.",
        "email_mislukt": "E-mail versturen mislukt: {fout}",
        "email_onderwerp": "DraveSeCam: beweging gedetecteerd",
        "email_tekst": "Er is beweging gedetecteerd op {tijd}.\nDe foto zit als bijlage.\n\n- DraveSeCam",
    },
    "en": {
        "titel": "DraveSeCam - surveillance",
        "camera": "Camera",
        "verversen": "Find cameras",
        "start": "Start camera",
        "stop": "Stop camera",
        "bewaking_aan": "Monitoring ON",
        "bewaking_uit": "Monitoring OFF",
        "gevoeligheid": "Sensitivity",
        "laag": "low",
        "hoog": "high",
        "snapshot": "Take photo now",
        "open_map": "Open captures folder",
        "open_logboek": "Open log file",
        "log_start": "Log started.",
        "gebeurtenissen": "Events",
        "klaar": "Ready. Pick a camera and press Start camera.",
        "opstarten": "Starting up\nSearching camera...",
        "opstarten_kort": "Starting up - searching camera...",
        "geen_camera": "No camera image.\nPick a camera and press Start camera.",
        "zoeken": "Searching cameras...",
        "gevonden": "{n} camera(s) found.",
        "geen_gevonden": "No camera found. Is a webcam connected?",
        "geen_gevonden_hint": "No camera found. In Windows check: Settings > Privacy & security > Camera (turn 'Camera access' and app access ON). Also close other apps using the camera (Teams, Zoom, Camera app).",
        "gestart": "Camera started.",
        "gestopt": "Camera stopped.",
        "fout_open": "Could not open camera.",
        "beweging": "Motion detected",
        "foto_opgeslagen": "Photo saved: {naam}",
        "bewaking_actief": "Monitoring active.",
        "bewaking_gestopt": "Monitoring stopped.",
        "geen_cv2": "OpenCV missing. Install with:  pip install opencv-python",
        "menu_bestand": "File",
        "menu_taal": "Language",
        "menu_help": "Help",
        "afsluiten": "Quit",
        "snelgids": "Quick guide (F1)",
        "over": "About DraveSeCam",
        "donatie": "Donate",
        "beweging_pct": "Motion: {p:.1f}%",
        "bij_beweging": "On motion",
        "modus_foto": "Take photo",
        "modus_video": "Record video",
        "modus_beide": "Photo + video",
        "opname_bezig": "\u25cf Recording video...",
        "video_gestart": "Video recording started",
        "video_opgeslagen": "Video saved: {naam} ({n} frames)",
        "video_mislukt": "Video recording failed (no suitable codec found).",
        "video_nu": "Video (5 sec)",
        "eerst_starten": "Start the camera first.",
        "video_leeg": "Video stayed empty - the codec wrote nothing. Try again.",
        "geluid_opnemen": "Record sound (microphone)",
        "geluid_niet": "Sound not available (package missing)",
        "geluid_bezig": "Adding sound to video...",
        "video_met_geluid": "Video with sound saved: {naam}",
        "geluid_mislukt": "Adding sound failed - video saved without sound.",
        "email_bij_beweging": "Send e-mail on motion",
        "email_instellen": "E-mail settings...",
        "email_titel": "E-mail settings",
        "email_uitleg": "Automatically send an e-mail (with photo) on motion. Note: this uses "
                        "the internet. Prefer an app password.",
        "email_dienst": "Mail provider",
        "email_app_ww_tip": "Tip: this provider usually needs an app password "
                            "(enable two-step verification first).",
        "email_ms_tip": "Note: Microsoft often blocks password login for mail "
                        "(modern auth/OAuth required). May not work.",
        "email_host": "Server (SMTP)",
        "email_poort": "Port",
        "email_beveiliging": "Security",
        "email_gebruiker": "Username",
        "email_adres": "Your e-mail address",
        "email_wachtwoord": "Password (app password)",
        "email_van": "From (sender)",
        "email_naar": "Send to (empty = yourself)",
        "email_bijlage_label": "Attach",
        "bijlage_foto": "Photo",
        "bijlage_video": "Video (can be large)",
        "bijlage_beide": "Photo + video",
        "email_modus_foto": "photo",
        "email_modus_video": "video",
        "email_modus_beide": "photo + video",
        "email_aan_modus": "E-mail on - attaching: {wat}",
        "email_tekst_video": "Motion was detected at {tijd}.\nThe video is attached.\n\n- DraveSeCam",
        "video_te_groot": "Video too large to e-mail ({mb} MB) - not sent.",
        "diag_uit": "is off - tick 'Send e-mail on motion'.",
        "diag_modus_video": "Video mode - the mail follows once the clip is ready.",
        "diag_geen_server": "no server set (open E-mail settings).",
        "diag_wachttijd": "wait time active (see 'Minutes between mails').",
        "diag_bewaking_uit": "monitoring is off.",
        "diag_geen_clip": "no video clip found to e-mail.",
        "email_aan_kort": "E-mail: ON",
        "stream_aan": "Live view (network)",
        "stream_open": "Open live",
        "stream_uitleg": "Watch the camera live in a browser on the same wifi network.",
        "stream_actief": "Live view: {url}",
        "stream_gestopt": "Live view stopped.",
        "stream_fout": "Could not start the live server (port in use?).",
        "mail_live_link": "Live view (same network):",
        "stream_extern": "Also from outside (port forwarding)",
        "adres_knop": "Addresses / router...",
        "adres_titel": "Set up viewing from outside",
        "stream_extern_tip": "For viewing from outside your home. Requires port forwarding in your router. "
                             "The e-mail then gets your public internet address. Keep the key secret.",
        "stream_extern_aan": "From outside ON - the e-mail gets your public address (set up port forwarding in your router).",
        "stream_extern_uit": "From outside OFF - e-mail uses the local address again.",
        "mail_live_link_extern": "Live view (from anywhere, via port forwarding):",
        "email_uit_kort": "E-mail: OFF (tick 'Send e-mail on motion')",
        "email_interval": "Minutes between mails",
        "email_test": "Send test mail",
        "email_opslaan": "Save",
        "email_annuleer": "Cancel",
        "email_onvolledig": "Fill in at least server and recipient.",
        "email_test_bezig": "Sending test mail...",
        "email_test_ok": "Test mail sent. Check your inbox.",
        "email_test_fout": "Sending failed: {fout}",
        "email_bezig": "Sending e-mail...",
        "email_verstuurd": "E-mail sent on motion.",
        "email_mislukt": "Sending e-mail failed: {fout}",
        "email_onderwerp": "DraveSeCam: motion detected",
        "email_tekst": "Motion was detected at {tijd}.\nThe photo is attached.\n\n- DraveSeCam",
    },
}


def T(sleutel, **kw):
    s = VERTALINGEN.get(_TAAL, VERTALINGEN["nl"]).get(sleutel, sleutel)
    return s.format(**kw) if kw else s


def detecteer_taal():
    try:
        naam = QLocale.system().name().lower()
    except Exception:
        naam = ""
    if naam.startswith("nl"):
        return "nl"
    if naam.startswith("en"):
        return "en"
    try:
        code = (locale.getdefaultlocale()[0] or "").lower()
    except Exception:
        code = ""
    return "nl" if code.startswith("nl") else "en"


def app_icoon():
    p = os.path.join(ASSETS, "logo.png")
    return QIcon(p) if os.path.exists(p) else QIcon()


def centreer(widget, ouder=None):
    widget.adjustSize()
    scr = QApplication.primaryScreen()
    midden = scr.availableGeometry().center() if scr else None
    if midden is not None:
        g = widget.frameGeometry(); g.moveCenter(midden); widget.move(g.topLeft())


def STIJL():
    return f"""
    QWidget {{ background:{BG}; color:{TEKST}; font-size:16px; }}
    QMainWindow, QDialog {{ background:{BG}; }}
    QLabel {{ color:{TEKST}; }}
    QStatusBar {{ background:{PANEEL}; color:{MUTED}; font-size:15px; }}
    QPushButton {{ background:{PANEEL2}; color:{TEKST}; border:1px solid {LINE};
        border-radius:9px; padding:9px 12px; font-size:16px; }}
    QPushButton:hover {{ border-color:{ACCENT}; }}
    QPushButton#primair {{ background:{ACCENT}; color:#0c1116; border:none; font-weight:bold; }}
    QPushButton#aan {{ background:{GOED}; color:#0c1116; border:none; font-weight:bold; }}
    QPushButton#uit {{ background:{PANEEL2}; color:{TEKST}; border:1px solid {LINE}; }}
    QComboBox {{ background:#e9e9e9; color:#111111; border:1px solid #9a9aa2;
        border-radius:8px; padding:10px 12px; font-size:17px; min-height:24px; }}
    QComboBox QAbstractItemView {{ background:#f2f2f0; color:#111111;
        selection-background-color:{ACCENT}; selection-color:#0c1116; font-size:16px; }}
    QLineEdit {{ background:#e9e9e9; color:#111111; border:1px solid #9a9aa2;
        border-radius:8px; padding:10px 12px; font-size:17px; }}
    QLineEdit:focus {{ border:1px solid {ACCENT}; }}
    QListWidget {{ background:{PANEEL2}; color:{TEKST}; border:1px solid {LINE};
        border-radius:8px; padding:6px; font-size:15px; }}
    QTextBrowser {{ background:{PANEEL2}; color:{TEKST}; border:1px solid {LINE};
        border-radius:8px; padding:10px; font-size:16px; }}
    QMenuBar {{ background:{PANEEL}; color:{TEKST}; font-size:15px; }}
    QMenuBar::item:selected {{ background:{PANEEL2}; }}
    QMenu {{ background:{PANEEL}; color:{TEKST}; border:1px solid {LINE}; }}
    QMenu::item:selected {{ background:{ACCENT}; color:#0c1116; }}
    QSlider::groove:horizontal {{ height:10px; background:{PANEEL2};
        border:1px solid {LINE}; border-radius:5px; }}
    QSlider::handle:horizontal {{ background:{ACCENT}; width:28px; height:28px;
        margin:-10px 0; border-radius:14px; }}
    QToolTip {{ background:{PANEEL2}; color:#ffffff; border:1px solid {ACCENT};
        padding:6px 8px; font-size:14px; }}
    """


# ======================================================================
# Beeldverwerking
# ======================================================================
def naar_grijs_blur(bgr):
    """BGR-frame -> vervaagde grijswaarden (voor bewegingsvergelijking)."""
    grijs = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(grijs, (21, 21), 0)


def beweging_fractie(vorige, huidige):
    """Fractie (0..1) van het beeld dat duidelijk veranderd is."""
    verschil = cv2.absdiff(vorige, huidige)
    _, masker = cv2.threshold(verschil, 25, 255, cv2.THRESH_BINARY)
    masker = cv2.dilate(masker, None, iterations=2)
    return float(np.count_nonzero(masker)) / float(masker.size)


def frame_naar_pixmap(bgr, breedte, hoogte):
    """BGR-numpy -> QPixmap, passend geschaald binnen (breedte, hoogte)."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, _ = rgb.shape
    rgb = np.ascontiguousarray(rgb)
    beeld = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
    pm = QPixmap.fromImage(beeld.copy())  # copy: losgekoppeld van numpy-buffer
    return pm.scaled(int(breedte), int(hoogte), Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)


# ======================================================================
# Camerabron (afgeschermd zodat testbeelden mogelijk zijn)
# ======================================================================
AUDIO_SR = 44100
AUDIO_KANALEN = 1


def geluid_beschikbaar():
    """Microfoon-opname + samenvoegen mogelijk?"""
    return sd is not None and FFMPEG_EXE is not None


def schrijf_wav(pad, chunks, samplerate=AUDIO_SR, kanalen=AUDIO_KANALEN):
    """Schrijf opgevangen float32-audio (lijst van numpy-blokken) naar een WAV (int16)."""
    if not chunks:
        return False
    try:
        data = np.concatenate(chunks, axis=0)
        data = np.clip(data, -1.0, 1.0)
        ints = (data * 32767.0).astype("<i2")
        with wave.open(pad, "wb") as w:
            w.setnchannels(kanalen)
            w.setsampwidth(2)
            w.setframerate(samplerate)
            w.writeframes(ints.tobytes())
        return True
    except Exception:
        return False


def _geen_venster_vlag():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0


def voeg_geluid_toe(video_pad, audio_pad, uit_pad):
    """Voegt geluid bij beeld met ffmpeg (h264 + aac -> mp4). True bij succes."""
    if FFMPEG_EXE is None:
        return False
    cmd = [FFMPEG_EXE, "-y", "-i", video_pad, "-i", audio_pad,
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", uit_pad]
    try:
        r = subprocess.run(cmd, capture_output=True, creationflags=_geen_venster_vlag())
        return r.returncode == 0 and os.path.exists(uit_pad) and os.path.getsize(uit_pad) > 0
    except Exception:
        return False


def lan_ip():
    """Lokaal netwerk-IP bepalen (192.168.x.x), zonder echt iets te versturen."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


class _StreamHandler(http.server.BaseHTTPRequestHandler):
    """Levert een live MJPEG-stream + een simpele kijkpagina."""

    def log_message(self, *a):
        pass  # geen console-spam

    def _sleutel_ok(self, params):
        nodig = getattr(self.server, "sleutel", "")
        gegeven = params.get("sleutel", [""])[0]
        return (not nodig) or (gegeven == nodig)

    def do_GET(self):
        u = urlparse(self.path)
        params = parse_qs(u.query)
        if not self._sleutel_ok(params):
            self.send_response(403); self.end_headers()
            try:
                self.wfile.write("Geen toegang - verkeerde of ontbrekende sleutel.".encode("utf-8"))
            except Exception:
                pass
            return
        if u.path == "/stream":
            self._stream()
        elif u.path in ("/", "/index.html"):
            self._pagina(params.get("sleutel", [""])[0])
        else:
            self.send_response(404); self.end_headers()

    def _pagina(self, sleutel):
        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>DraveSeCam live</title>"
            "<style>body{background:#0e0e11;margin:0;text-align:center;}"
            "h1{color:#d4d4d4;font-family:sans-serif;font-size:20px;margin:12px;}"
            "img{max-width:100%;height:auto;}</style></head>"
            "<body><h1>DraveSeCam &mdash; live</h1>"
            "<img src='/stream?sleutel=" + sleutel + "' alt='live'></body></html>"
        )
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def _stream(self):
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while getattr(self.server, "actief", True):
                jpg = getattr(self.server, "laatste_jpg", None)
                if jpg:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(("Content-Length: %d\r\n\r\n" % len(jpg)).encode())
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
                time.sleep(0.05)                          # ~20 beelden/sec
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


class StreamServer:
    """Beheert de webserver in een aparte thread; deelt het laatste JPEG-beeld."""
    def __init__(self, poort, sleutel):
        self.poort = int(poort)
        self.sleutel = sleutel
        self.httpd = None
        self.thread = None

    def start(self):
        self.httpd = http.server.ThreadingHTTPServer(("0.0.0.0", self.poort), _StreamHandler)
        self.httpd.daemon_threads = True
        self.httpd.sleutel = self.sleutel
        self.httpd.laatste_jpg = None
        self.httpd.actief = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def zet_frame(self, jpg):
        if self.httpd is not None:
            self.httpd.laatste_jpg = jpg

    def stop(self):
        if self.httpd is not None:
            self.httpd.actief = False
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        self.httpd = None
        self.thread = None


_PUB_IP = {"ip": "", "tijd": None}


def publiek_ip(force=False):
    """Haalt het publieke internet-IP op (met cache van 5 min). Leeg bij mislukken."""
    nu = datetime.datetime.now()
    if (not force and _PUB_IP["ip"] and _PUB_IP["tijd"]
            and (nu - _PUB_IP["tijd"]).total_seconds() < 300):
        return _PUB_IP["ip"]
    import urllib.request
    for url in ("https://api.ipify.org", "https://checkip.amazonaws.com",
                "https://ifconfig.me/ip"):
        try:
            r = urllib.request.urlopen(url, timeout=4)
            ip = r.read().decode("utf-8", "ignore").strip()
            if ip and ip.count(".") == 3 and all(d.isdigit() for d in ip.split(".")):
                _PUB_IP["ip"] = ip
                _PUB_IP["tijd"] = nu
                return ip
        except Exception:
            continue
    return _PUB_IP["ip"]


def camera_backends():
    """Backends om te proberen, in volgorde. Windows: MSMF, dan DSHOW (geen CAP_ANY:
    dat valt op sommige pc's naar de obsensor-backend en spamt foutmeldingen)."""
    if cv2 is None:
        return []
    if sys.platform.startswith("win"):
        return [cv2.CAP_MSMF, cv2.CAP_DSHOW]
    return [cv2.CAP_ANY]


class CameraBron:
    def __init__(self):
        self.cap = None
        self.index = -1
        self.backend = None

    @staticmethod
    def _probeer_open(index, backend):
        """Open een camera met een backend; geef de capture terug als die binnen
        korte tijd ook echt een beeld levert (sommige webcams moeten opwarmen)."""
        try:
            cap = cv2.VideoCapture(index, backend)
        except Exception:
            return None
        if cap.isOpened():
            for _ in range(8):                 # ~0,4 s de tijd geven om beeld te leveren
                ok, frame = cap.read()
                if ok and frame is not None:
                    return cap
                time.sleep(0.05)
        cap.release()
        return None

    @staticmethod
    def zoek_cameras(maximaal=5):
        """Geeft een lijst van bruikbare camera-indices terug (eerste werkende backend telt)."""
        gevonden = []
        if cv2 is None:
            return gevonden
        for i in range(maximaal):
            for be in camera_backends():
                cap = CameraBron._probeer_open(i, be)
                if cap is not None:
                    cap.release()
                    gevonden.append(i)
                    break
        return gevonden

    def open(self, index):
        self.sluit()
        if cv2 is None:
            return False
        for be in camera_backends():
            cap = CameraBron._probeer_open(index, be)
            if cap is not None:
                self.cap = cap
                self.index = index
                self.backend = be
                return True
        return False

    def lees(self):
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        return frame if ok else None

    def sluit(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.index = -1
        self.backend = None


class CameraZoeker(QThread):
    """Zoekt camera's in een aparte thread, zodat de UI niet bevriest bij het opstarten."""
    klaar = pyqtSignal(list)

    def run(self):
        try:
            indices = CameraBron.zoek_cameras()
        except Exception:
            indices = []
        self.klaar.emit(indices)


class MuxWorker(QThread):
    """Voegt geluid bij een opgenomen videoclip (ffmpeg) zonder de UI te blokkeren."""
    klaar = pyqtSignal(str, str, str, bool)  # video_pad, audio_pad, uit_pad, gelukt

    def __init__(self, video_pad, audio_pad, uit_pad):
        super().__init__()
        self.video_pad = video_pad
        self.audio_pad = audio_pad
        self.uit_pad = uit_pad

    def run(self):
        ok = voeg_geluid_toe(self.video_pad, self.audio_pad, self.uit_pad)
        self.klaar.emit(self.video_pad, self.audio_pad, self.uit_pad, ok)


def verstuur_mail(cfg, onderwerp, tekst, bijlage_pad=None):
    """Verstuurt een e-mail via SMTP. Geeft (gelukt, foutmelding) terug."""
    host = (cfg.get("email_host") or "").strip()
    naar = (cfg.get("email_naar") or "").strip()
    if not host or not naar:
        return False, "Server of ontvanger ontbreekt."
    poort = int(cfg.get("email_poort") or 465)
    beveiliging = cfg.get("email_beveiliging") or "ssl"
    gebruiker = (cfg.get("email_gebruiker") or "").strip()
    wachtwoord = cfg.get("email_wachtwoord") or ""
    van = (cfg.get("email_van") or gebruiker or "").strip()
    try:
        msg = EmailMessage()
        msg["Subject"] = onderwerp
        msg["From"] = van
        msg["To"] = naar
        msg.set_content(tekst)
        if bijlage_pad and os.path.exists(bijlage_pad):
            with open(bijlage_pad, "rb") as f:
                data = f.read()
            ctype, _ = mimetypes.guess_type(bijlage_pad)
            if ctype and "/" in ctype:
                maintype, subtype = ctype.split("/", 1)
            else:
                maintype, subtype = "application", "octet-stream"
            msg.add_attachment(data, maintype=maintype, subtype=subtype,
                               filename=os.path.basename(bijlage_pad))
        if beveiliging == "ssl":
            ctx = _ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, poort, timeout=20, context=ctx)
        else:
            server = smtplib.SMTP(host, poort, timeout=20)
            if beveiliging == "starttls":
                server.starttls(context=_ssl.create_default_context())
        if gebruiker:
            server.login(gebruiker, wachtwoord)
        server.send_message(msg)
        server.quit()
        return True, ""
    except Exception as e:
        return False, str(e)


class MailWorker(QThread):
    """Verstuurt een e-mail in de achtergrond, zodat de UI niet bevriest."""
    klaar = pyqtSignal(bool, str)

    def __init__(self, cfg, onderwerp, tekst, bijlage_pad=None):
        super().__init__()
        self.cfg = dict(cfg)
        self.onderwerp = onderwerp
        self.tekst = tekst
        self.bijlage_pad = bijlage_pad

    def run(self):
        ok, fout = verstuur_mail(self.cfg, self.onderwerp, self.tekst, self.bijlage_pad)
        self.klaar.emit(ok, fout)


# ======================================================================
# Snelgids
# ======================================================================
class SnelgidsDialoog(QDialog):
    def __init__(self, ouder=None):
        super().__init__(ouder)
        self.setWindowTitle(T("snelgids")); self.setWindowIcon(app_icoon())
        self.setStyleSheet(STIJL()); self.setMinimumSize(560, 460)
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 20, 24, 20); lay.setSpacing(12)
        kop = QLabel("DraveSeCam - %s" % T("snelgids"))
        kop.setStyleSheet("font-size:22px; font-weight:bold; color:#ffffff;")
        tekst = QTextBrowser()
        if _TAAL == "nl":
            tekst.setHtml(
                "<p><b>Opstarten:</b> de app zoekt en start je webcam vanzelf en zet de "
                "bewaking meteen AAN. Bij beweging worden foto's en/of video's bewaard in "
                "de opnames-map.</p>"
                "<p><b>Bij beweging:</b> kies Foto, Video of Foto+video. Vink "
                "<b>Geluid opnemen</b> aan voor video met geluid (.mp4).</p>"
                "<p><b>Gevoeligheid:</b> hoger = kleine beweging telt al; lager = alleen "
                "grote beweging.</p>"
                "<p><b>E-mail bij beweging:</b> druk op <b>E-mail instellen...</b>, kies je "
                "maildienst, vul je adres en een <b>app-wachtwoord</b> in en sla op. Daarmee "
                "staat 'E-mail sturen bij beweging' aan.</p>"
                "<p><b>Logboek:</b> alle gebeurtenissen staan ook in <b>logboek.txt</b> "
                "(knop 'Open logboek').</p>"
                "<hr>"
                "<p><b>Live meekijken (zelfde wifi):</b> vink <b>Live meekijken (netwerk)</b> "
                "aan en druk op <b>Open live (browser)</b>. Op een telefoon/tablet op hetzelfde "
                "wifi open je het adres <b>http://JOUW-PC-IP:8080/?sleutel=...</b> (dat adres "
                "staat ook in de bewegings-mail). De sleutel beschermt de toegang.</p>"
                "<p><b>Van buitenaf kijken (gevorderd):</b> vink <b>Ook van buitenaf (port "
                "forwarding)</b> aan. Dan zet de app je <b>publieke internet-adres</b> in de "
                "bewegings-mail (automatisch ververst, dus ook bij een gewijzigd thuis-IP klopt "
                "de link). Je moet wel eenmalig in je router <b>port forwarding</b> instellen: "
                "stuur de poort (bv. 8080 TCP) door naar het IP van deze PC. Een hoge poort "
                "(8080/8888) voorkomt conflicten met Windows-diensten.</p>"
                "<p><b>Let op - veiligheid:</b> een camera die open op internet staat is een "
                "risico. Houd de sleutel geheim, deel de link niet openbaar, en zet port "
                "forwarding weer uit als je het niet gebruikt. Het verkeer is onversleuteld "
                "(geen https).</p>")
        else:
            tekst.setHtml(
                "<p><b>Startup:</b> the app finds and starts your webcam automatically and "
                "turns monitoring ON right away. On motion, photos and/or videos are saved in "
                "the captures folder.</p>"
                "<p><b>On motion:</b> choose Photo, Video or Photo+video. Tick <b>Record "
                "sound</b> for video with audio (.mp4).</p>"
                "<p><b>Sensitivity:</b> higher = small motion counts; lower = large motion only.</p>"
                "<p><b>E-mail on motion:</b> press <b>E-mail settings...</b>, pick your provider, "
                "enter your address and an <b>app password</b> and save. That enables "
                "'Send e-mail on motion'.</p>"
                "<p><b>Log:</b> all events are also in <b>logboek.txt</b> (button 'Open log file').</p>"
                "<hr>"
                "<p><b>Live view (same wifi):</b> tick <b>Live view (network)</b> and press "
                "<b>Open live (browser)</b>. On a phone/tablet on the same wifi, open "
                "<b>http://YOUR-PC-IP:8080/?sleutel=...</b> (this address is also in the motion "
                "e-mail). The key protects access.</p>"
                "<p><b>Viewing from outside (advanced):</b> tick <b>Also from outside (port "
                "forwarding)</b>. The app then puts your <b>public internet address</b> in the "
                "motion e-mail (refreshed automatically, so the link stays correct even if your "
                "home IP changes). You do need to set up <b>port forwarding</b> in your router "
                "once: forward the port (e.g. 8080 TCP) to this PC's IP. A high port (8080/8888) "
                "avoids conflicts with Windows services.</p>"
                "<p><b>Note - security:</b> a camera open on the internet is a risk. Keep the key "
                "secret, don't share the link publicly, and turn port forwarding off when unused. "
                "Traffic is unencrypted (no https).</p>")
        sluit = QPushButton("OK"); sluit.setObjectName("primair")
        sluit.setMinimumHeight(46); sluit.clicked.connect(self.accept)
        lay.addWidget(kop); lay.addWidget(tekst, 1); lay.addWidget(sluit)
        QTimer.singleShot(0, lambda: centreer(self))


class AdressenDialoog(QDialog):
    """Toont de concrete adressen voor meekijken + uitleg port forwarding, met eigen waarden."""
    def __init__(self, ouder, lan, pub, poort, sleutel):
        super().__init__(ouder)
        self.setWindowTitle(T("adres_titel")); self.setWindowIcon(app_icoon())
        self.setStyleSheet(STIJL()); self.setMinimumSize(620, 520)
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 20, 24, 20); lay.setSpacing(12)
        kop = QLabel("DraveSeCam - %s" % T("adres_titel"))
        kop.setStyleSheet("font-size:22px; font-weight:bold; color:#ffffff;")

        thuis = "http://%s:%d/?sleutel=%s" % (lan, poort, sleutel)
        buiten = ("http://%s:%d/?sleutel=%s" % (pub, poort, sleutel)) if pub else ""

        tekst = QTextBrowser()
        if _TAAL == "nl":
            html = (
                "<p><b>1) Stuur deze poort door in je router (port forwarding):</b></p>"
                "<p style='font-size:18px;'>Externe poort <b>%d</b> (TCP) &rarr; naar deze PC "
                "<b>%s</b> , interne poort <b>%d</b>.</p>"
                "<p><b>2) Je toegangssleutel:</b> <span style='font-size:18px;'>%s</span></p>"
                "<hr>"
                "<p><b>Thuis kijken (zelfde wifi):</b><br><span style='font-size:17px;'>%s</span></p>"
                "<p><b>Van buitenaf kijken (na port forwarding):</b><br>%s</p>"
                "<hr>"
                "<p><b>Zo stel je port forwarding in:</b></p>"
                "<p>a. Open je router in de browser (vaak <b>192.168.0.1</b> of "
                "<b>192.168.1.1</b>) en log in.<br>"
                "b. Zoek <b>Port forwarding</b> / <b>Poort doorsturen</b> / <b>NAT</b>.<br>"
                "c. Maak een regel: externe poort <b>%d</b> &rarr; intern IP <b>%s</b>, "
                "interne poort <b>%d</b>, type <b>TCP</b>.<br>"
                "d. Opslaan. Klikt Windows op een firewall-vraag? Kies <b>Toestaan</b>.<br>"
                "e. Van buitenaf open je de bovenste 'van buitenaf'-link (staat ook in de mail).</p>"
                "<p><b>Let op:</b> je publieke IP kan veranderen; de bewegings-mail bevat altijd "
                "het actuele adres. Houd de sleutel geheim, deel de link niet openbaar, en zet "
                "port forwarding weer uit als je het niet gebruikt. Het verkeer is onversleuteld "
                "(geen https).</p>"
            ) % (poort, lan, poort, sleutel, thuis,
                 (("<span style='font-size:17px;'>" + buiten + "</span>") if buiten
                  else "<i>Publiek IP nog onbekend - vink 'Ook van buitenaf' aan en wacht even, "
                       "of bekijk het adres in de bewegings-mail.</i>"),
                 poort, lan, poort)
        else:
            html = (
                "<p><b>1) Forward this port in your router (port forwarding):</b></p>"
                "<p style='font-size:18px;'>External port <b>%d</b> (TCP) &rarr; to this PC "
                "<b>%s</b> , internal port <b>%d</b>.</p>"
                "<p><b>2) Your access key:</b> <span style='font-size:18px;'>%s</span></p>"
                "<hr>"
                "<p><b>View at home (same wifi):</b><br><span style='font-size:17px;'>%s</span></p>"
                "<p><b>View from outside (after port forwarding):</b><br>%s</p>"
                "<hr>"
                "<p><b>How to set up port forwarding:</b></p>"
                "<p>a. Open your router in a browser (often <b>192.168.0.1</b> or "
                "<b>192.168.1.1</b>) and log in.<br>"
                "b. Find <b>Port forwarding</b> / <b>NAT</b>.<br>"
                "c. Add a rule: external port <b>%d</b> &rarr; internal IP <b>%s</b>, "
                "internal port <b>%d</b>, type <b>TCP</b>.<br>"
                "d. Save. If Windows asks about the firewall, choose <b>Allow</b>.<br>"
                "e. From outside, open the 'from outside' link above (also in the e-mail).</p>"
                "<p><b>Note:</b> your public IP can change; the motion e-mail always contains the "
                "current address. Keep the key secret, don't share the link publicly, and turn "
                "port forwarding off when unused. Traffic is unencrypted (no https).</p>"
            ) % (poort, lan, poort, sleutel, thuis,
                 (("<span style='font-size:17px;'>" + buiten + "</span>") if buiten
                  else "<i>Public IP not known yet - tick 'Also from outside' and wait a moment, "
                       "or see the address in the motion e-mail.</i>"),
                 poort, lan, poort)
        tekst.setHtml(html)
        tekst.setOpenExternalLinks(False)
        sluit = QPushButton("OK"); sluit.setObjectName("primair")
        sluit.setMinimumHeight(46); sluit.clicked.connect(self.accept)
        lay.addWidget(kop); lay.addWidget(tekst, 1); lay.addWidget(sluit)
        QTimer.singleShot(0, lambda: centreer(self))


class EmailInstellingenDialoog(QDialog):
    """Scherm om de mailserver in te stellen en een testmail te sturen."""
    # (label, server, poort, beveiliging, app-wachtwoord-tip, microsoft-tip)
    DIENSTEN = [
        ("Handmatig instellen", "", 465, "ssl", False, False),
        ("Gmail", "smtp.gmail.com", 587, "starttls", True, False),
        ("Outlook.com / Hotmail / Live", "smtp-mail.outlook.com", 587, "starttls", True, True),
        ("Microsoft 365 / Office 365", "smtp.office365.com", 587, "starttls", False, True),
        ("Yahoo Mail", "smtp.mail.yahoo.com", 465, "ssl", True, False),
        ("iCloud Mail", "smtp.mail.me.com", 587, "starttls", True, False),
        ("GMX", "mail.gmx.com", 587, "starttls", False, False),
        ("Ziggo", "smtp.ziggo.nl", 587, "starttls", False, False),
        ("KPN", "smtp.kpnmail.nl", 587, "starttls", False, False),
        ("Telenet (BE)", "smtp.telenet.be", 587, "starttls", False, False),
    ]

    def __init__(self, ouder, cfg):
        super().__init__(ouder)
        self.cfg = cfg
        self._mailer = None
        self.setWindowTitle(T("email_titel")); self.setWindowIcon(app_icoon())
        self.setStyleSheet(STIJL()); self.setMinimumWidth(580)
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 20, 24, 20); lay.setSpacing(12)

        uitleg = QLabel(T("email_uitleg")); uitleg.setWordWrap(True)
        uitleg.setStyleSheet(f"color:{MUTED};")
        lay.addWidget(uitleg)

        form = QFormLayout(); form.setSpacing(10)
        self.dienst = QComboBox()
        for d in self.DIENSTEN:
            self.dienst.addItem(d[0], d)
        self.dienst.currentIndexChanged.connect(self._dienst_gekozen)
        form.addRow(T("email_dienst"), self.dienst)

        self.host = QLineEdit(str(cfg.get("email_host", "")))
        self.poort = QLineEdit(str(cfg.get("email_poort", 465)))
        self.bev = QComboBox()
        self.bev.addItem("SSL (465)", "ssl")
        self.bev.addItem("STARTTLS (587)", "starttls")
        self.bev.addItem("Geen (25)", "geen")
        self.bev.setCurrentIndex(max(0, self.bev.findData(cfg.get("email_beveiliging", "ssl"))))
        self.adres = QLineEdit(str(cfg.get("email_van") or cfg.get("email_gebruiker") or ""))
        self.wachtwoord = QLineEdit(str(cfg.get("email_wachtwoord", "")))
        self.wachtwoord.setEchoMode(QLineEdit.EchoMode.Password)
        self.naar = QLineEdit(str(cfg.get("email_naar", "")))
        self.bijlage = QComboBox()
        self.bijlage.addItem(T("bijlage_foto"), "foto")
        self.bijlage.addItem(T("bijlage_video"), "video")
        self.bijlage.addItem(T("bijlage_beide"), "beide")
        self.bijlage.setCurrentIndex(max(0, self.bijlage.findData(cfg.get("email_bijlage", "foto"))))
        self.interval = QLineEdit(str(cfg.get("email_interval_min", 2)))
        for sleutel, w in [("email_host", self.host), ("email_poort", self.poort),
                           ("email_beveiliging", self.bev), ("email_adres", self.adres),
                           ("email_wachtwoord", self.wachtwoord), ("email_naar", self.naar),
                           ("email_bijlage_label", self.bijlage), ("email_interval", self.interval)]:
            form.addRow(T(sleutel), w)
        lay.addLayout(form)

        self.tip = QLabel(""); self.tip.setWordWrap(True); self.tip.setStyleSheet(f"color:{ACCENT};")
        lay.addWidget(self.tip)

        self.mld = QLabel(""); self.mld.setWordWrap(True); self.mld.setStyleSheet(f"color:{MUTED};")
        lay.addWidget(self.mld)

        rij = QHBoxLayout()
        self.knop_test = QPushButton(T("email_test")); self.knop_test.setMinimumHeight(44)
        self.knop_test.clicked.connect(self._test)
        knop_ann = QPushButton(T("email_annuleer")); knop_ann.setMinimumHeight(44)
        knop_ann.clicked.connect(self.reject)
        knop_ok = QPushButton(T("email_opslaan")); knop_ok.setObjectName("primair")
        knop_ok.setMinimumHeight(44); knop_ok.clicked.connect(self._opslaan)
        rij.addWidget(self.knop_test); rij.addStretch(1)
        rij.addWidget(knop_ann); rij.addWidget(knop_ok)
        lay.addLayout(rij)

        # begin-selectie: opgeslagen dienst, anders herkennen aan server, anders handmatig
        self._kies_begin_dienst()
        QTimer.singleShot(0, lambda: centreer(self, ouder))

    def _kies_begin_dienst(self):
        opgeslagen = self.cfg.get("email_provider")
        huidige_host = (self.cfg.get("email_host") or "").lower()
        idx = 0
        for i, d in enumerate(self.DIENSTEN):
            if opgeslagen and d[0] == opgeslagen:
                idx = i; break
            if not opgeslagen and d[1] and d[1].lower() == huidige_host:
                idx = i; break
        self.dienst.blockSignals(True)
        self.dienst.setCurrentIndex(idx)
        self.dienst.blockSignals(False)
        self._toon_tip(self.DIENSTEN[idx])

    def _dienst_gekozen(self, _idx):
        d = self.dienst.currentData()
        if not d:
            return
        if d[1]:                              # niet 'handmatig': vul server-velden in
            self.host.setText(d[1])
            self.poort.setText(str(d[2]))
            self.bev.setCurrentIndex(max(0, self.bev.findData(d[3])))
        self._toon_tip(d)

    def _toon_tip(self, d):
        delen = []
        if d[4]:
            delen.append(T("email_app_ww_tip"))
        if d[5]:
            delen.append(T("email_ms_tip"))
        self.tip.setText("  ".join(delen))

    def _verzamel(self):
        d = dict(self.cfg)
        d["email_host"] = self.host.text().strip()
        try:
            d["email_poort"] = int(self.poort.text().strip() or 465)
        except ValueError:
            d["email_poort"] = 465
        d["email_beveiliging"] = self.bev.currentData()
        adres = self.adres.text().strip()
        d["email_gebruiker"] = adres          # gebruikersnaam = je e-mailadres
        d["email_van"] = adres                # afzender = je e-mailadres
        d["email_naar"] = self.naar.text().strip() or adres   # leeg = naar jezelf
        d["email_wachtwoord"] = self.wachtwoord.text()
        d["email_bijlage"] = self.bijlage.currentData() or "foto"
        try:
            d["email_interval_min"] = max(0, int(self.interval.text().strip() or 2))
        except ValueError:
            d["email_interval_min"] = 2
        return d

    def _opslaan(self):
        d = self._verzamel()
        if not d.get("email_host") or not d.get("email_naar"):
            self.mld.setText(T("email_onvolledig")); return
        d["email_provider"] = self.dienst.currentText()
        d["email_aan"] = True          # na opslaan meteen inschakelen
        self.cfg.update(d); bewaar_config(self.cfg); self.accept()

    def _test(self):
        d = self._verzamel()
        if not d.get("email_host") or not d.get("email_naar"):
            self.mld.setText(T("email_onvolledig")); return
        self.mld.setText(T("email_test_bezig")); self.knop_test.setEnabled(False)
        tijd = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._mailer = MailWorker(d, T("email_onderwerp"), T("email_tekst", tijd=tijd))
        self._mailer.klaar.connect(self._test_klaar)
        self._mailer.start()

    def _test_klaar(self, ok, fout):
        self.knop_test.setEnabled(True)
        self.mld.setText(T("email_test_ok") if ok else T("email_test_fout", fout=fout))


# ======================================================================
# Hoofdvenster
# ======================================================================
class DraveSeCamVenster(QMainWindow):
    def __init__(self, cfg, testbron=None):
        super().__init__()
        self.cfg = cfg
        self.bron = CameraBron()
        self._testbron = testbron          # callable -> bgr frame of None (voor tests)
        self._vorige_grijs = None
        self._draait = False
        self._bewaking = False
        self._laatste_foto_tijd = None     # cooldown
        self.gevoeligheid = int(cfg.get("gevoeligheid", 50))
        # video-opname
        self._recorder = None
        self._rec_size = None
        self._rec_start = None
        self._rec_frames = 0
        self._rec_pad = None
        self._rec_volpad = None
        self._rec_tail_tot = None
        self._fps = 20.0
        self._video_fout = False
        # geluid
        self._audio_chunks = []
        self._audio_stream = None
        self._audio_actief = False
        self._muxers = []                  # referenties vasthouden (GC-preventie)
        # e-mail
        self._laatste_foto_mail = None
        self._laatste_video_mail = None
        self._mailers = []
        self._mail_diag_vorig = None
        # live meekijken (stream)
        self._stream = None
        self._pub_ip = ""
        if not self.cfg.get("stream_sleutel"):
            self.cfg["stream_sleutel"] = secrets.token_urlsafe(6)
            bewaar_config(self.cfg)
        self._pub_timer = QTimer(self)
        self._pub_timer.setInterval(300000)              # elke 5 min publiek IP verversen
        self._pub_timer.timeout.connect(self._ververs_pub_ip)

        self.setWindowTitle(T("titel")); self.setWindowIcon(app_icoon())
        self.setStyleSheet(STIJL())
        self._bouw_menu()
        self._bouw_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.setInterval(33)         # ~30 fps

        self._zoeker = None
        self.status().showMessage(T("klaar"))
        os.makedirs(SNAPSHOT_MAP, exist_ok=True)

        # Automatisch opstarten: camera zoeken + starten (alleen bij echte camera).
        if cv2 is not None and self._testbron is None:
            self.beeld.setText("")
            QTimer.singleShot(150, lambda: self._toon_banner(T("opstarten_kort")))
            QTimer.singleShot(300, self._auto_start)
        if self.cfg.get("stream_aan"):
            QTimer.singleShot(500, self._start_stream)
        if self.cfg.get("stream_extern"):
            self._pub_timer.start()
            QTimer.singleShot(700, self._ververs_pub_ip)

    # -- helpers --
    def status(self):
        sb = self.statusBar()
        return sb

    def _bouw_menu(self):
        mb = self.menuBar()
        m_best = mb.addMenu(T("menu_bestand"))
        a_af = QAction(T("afsluiten"), self); a_af.triggered.connect(self.close)
        m_best.addAction(a_af)
        m_taal = mb.addMenu(T("menu_taal"))
        a_nl = QAction("Nederlands", self); a_nl.triggered.connect(lambda: self._zet_taal("nl"))
        a_en = QAction("English", self); a_en.triggered.connect(lambda: self._zet_taal("en"))
        m_taal.addAction(a_nl); m_taal.addAction(a_en)
        m_help = mb.addMenu(T("menu_help"))
        a_gids = QAction(T("snelgids"), self); a_gids.setShortcut("F1")
        a_gids.triggered.connect(lambda: SnelgidsDialoog(self).exec())
        m_help.addAction(a_gids)

    def _zet_taal(self, taal):
        global _TAAL
        _TAAL = taal
        self.cfg["taal"] = taal
        bewaar_config(self.cfg)
        # eenvoudig: vraag herstart voor volledige hertaling
        self.status().showMessage("Taal: %s" % taal)

    def _bouw_ui(self):
        centraal = QWidget(); self.setCentralWidget(centraal)
        hoofd = QHBoxLayout(centraal)
        hoofd.setContentsMargins(16, 16, 16, 20); hoofd.setSpacing(16)

        # -- links: live beeld --
        self.beeld = QLabel(T("geen_camera"))
        self.beeld.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beeld.setMinimumSize(720, 540)
        self.beeld.setStyleSheet(
            f"background:#000000; color:{MUTED}; border:1px solid {LINE};"
            "border-radius:10px; font-size:18px;")
        self.beeld.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        hoofd.addWidget(self.beeld, 1)

        # banner-balk (overlay bovenin het beeld) voor opstart-/statusmeldingen
        self.banner = QLabel("", self.beeld)
        self.banner.setStyleSheet(
            f"background:{ACCENT}; color:#0c1116; font-size:18px; font-weight:bold;"
            "padding:12px 22px; border-radius:10px;")
        self.banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.banner.hide()

        # -- rechts: bediening (vaste, niet te brede kolom) --
        paneel = QWidget(); paneel.setFixedWidth(360)
        kol = QVBoxLayout(paneel); kol.setContentsMargins(0, 0, 0, 0); kol.setSpacing(12)

        lbl_cam = QLabel(T("camera")); lbl_cam.setStyleSheet("font-weight:bold;")
        self.combo = QComboBox()
        self.combo.setToolTip(T("camera"))
        self.knop_zoek = QPushButton(T("verversen"))
        self.knop_zoek.setToolTip(T("verversen"))
        self.knop_zoek.clicked.connect(self.zoek_cameras)

        self.knop_start = QPushButton(T("start")); self.knop_start.setObjectName("primair")
        self.knop_start.setToolTip(T("start"))
        self.knop_start.clicked.connect(self.start_stop)

        self.knop_bewaking = QPushButton(T("bewaking_uit")); self.knop_bewaking.setObjectName("uit")
        self.knop_bewaking.setToolTip(T("bewaking_aan"))
        self.knop_bewaking.clicked.connect(self.wissel_bewaking)

        lbl_modus = QLabel(T("bij_beweging")); lbl_modus.setStyleSheet("font-weight:bold;")
        self.combo_modus = QComboBox()
        self.combo_modus.addItem(T("modus_foto"), "foto")
        self.combo_modus.addItem(T("modus_video"), "video")
        self.combo_modus.addItem(T("modus_beide"), "beide")
        huidige = self.cfg.get("opname_modus", "beide")
        idx = max(0, self.combo_modus.findData(huidige))
        self.combo_modus.setCurrentIndex(idx)
        self.combo_modus.setToolTip(T("bij_beweging"))
        self.combo_modus.currentIndexChanged.connect(self._modus_gewijzigd)

        self.chk_geluid = QCheckBox(T("geluid_opnemen"))
        self.chk_geluid.setToolTip(T("geluid_opnemen"))
        if geluid_beschikbaar():
            self.chk_geluid.setChecked(bool(self.cfg.get("geluid", True)))
        else:
            self.chk_geluid.setChecked(False)
            self.chk_geluid.setEnabled(False)
            self.chk_geluid.setText(T("geluid_niet"))
        self.chk_geluid.stateChanged.connect(self._geluid_gewijzigd)

        self.lbl_opname = QLabel("")
        self.lbl_opname.setStyleSheet(f"color:{WARN}; font-weight:bold;")

        lbl_gev = QLabel(T("gevoeligheid")); lbl_gev.setStyleSheet("font-weight:bold;")
        self.schuif = QSlider(Qt.Orientation.Horizontal)
        self.schuif.setRange(1, 100); self.schuif.setValue(self.gevoeligheid)
        self.schuif.setToolTip(T("gevoeligheid"))
        self.schuif.valueChanged.connect(self._gevoeligheid_gewijzigd)
        rij_gev = QHBoxLayout()
        l_laag = QLabel(T("laag")); l_laag.setStyleSheet(f"color:{MUTED};")
        l_hoog = QLabel(T("hoog")); l_hoog.setStyleSheet(f"color:{MUTED};")
        rij_gev.addWidget(l_laag); rij_gev.addWidget(self.schuif, 1); rij_gev.addWidget(l_hoog)
        self.lbl_beweging = QLabel(T("beweging_pct", p=0.0)); self.lbl_beweging.setStyleSheet(f"color:{MUTED};")

        self.knop_foto = QPushButton(T("snapshot")); self.knop_foto.setToolTip(T("snapshot"))
        self.knop_foto.clicked.connect(self.handmatige_foto)
        self.knop_video_nu = QPushButton(T("video_nu")); self.knop_video_nu.setToolTip(T("video_nu"))
        self.knop_video_nu.clicked.connect(self.start_handmatige_video)
        self.knop_map = QPushButton(T("open_map")); self.knop_map.setToolTip(T("open_map"))
        self.knop_map.clicked.connect(self.open_map)
        self.knop_log = QPushButton(T("open_logboek")); self.knop_log.setToolTip(T("open_logboek"))
        self.knop_log.clicked.connect(self.open_logboek)

        self.chk_email = QCheckBox(T("email_bij_beweging"))
        self.chk_email.setToolTip(T("email_bij_beweging"))
        self.chk_email.setChecked(bool(self.cfg.get("email_aan", False)))
        self.chk_email.stateChanged.connect(self._email_gewijzigd)
        self.knop_email = QPushButton(T("email_instellen")); self.knop_email.setToolTip(T("email_instellen"))
        self.knop_email.clicked.connect(self._open_email_instellingen)

        self.chk_stream = QCheckBox(T("stream_aan"))
        self.chk_stream.setToolTip(T("stream_uitleg"))
        self.chk_stream.setChecked(bool(self.cfg.get("stream_aan", False)))
        self.chk_stream.stateChanged.connect(self._stream_gewijzigd)
        self.knop_live = QPushButton(T("stream_open"))
        self.knop_live.setToolTip(T("stream_open"))
        self.knop_live.clicked.connect(self._open_live)
        self.knop_adres = QPushButton(T("adres_knop"))
        self.knop_adres.setToolTip(T("adres_knop"))
        self.knop_adres.clicked.connect(self._toon_adressen)
        self.chk_extern = QCheckBox(T("stream_extern"))
        self.chk_extern.setToolTip(T("stream_extern_tip"))
        self.chk_extern.setChecked(bool(self.cfg.get("stream_extern", False)))
        self.chk_extern.stateChanged.connect(self._extern_gewijzigd)

        lbl_geb = QLabel(T("gebeurtenissen")); lbl_geb.setStyleSheet("font-weight:bold;")
        self.log = QListWidget()
        self.log.setMinimumHeight(160)
        self.log.setStyleSheet("QListWidget{font-size:16px;} QListWidget::item{padding:4px 2px;}")

        kol.setSpacing(8)
        # camera-bediening
        kol.addWidget(lbl_cam); kol.addWidget(self.combo)
        rij_cam = QHBoxLayout(); rij_cam.setSpacing(8)
        rij_cam.addWidget(self.knop_zoek); rij_cam.addWidget(self.knop_start)
        kol.addLayout(rij_cam)
        kol.addWidget(self.knop_bewaking)
        kol.addSpacing(2)
        # bij beweging + geluid
        kol.addWidget(lbl_modus); kol.addWidget(self.combo_modus)
        kol.addWidget(self.chk_geluid); kol.addWidget(self.lbl_opname)
        kol.addSpacing(2)
        # gevoeligheid
        kol.addWidget(lbl_gev); kol.addLayout(rij_gev); kol.addWidget(self.lbl_beweging)
        kol.addSpacing(2)
        # actieknoppen in 2 kolommen
        rij_a = QHBoxLayout(); rij_a.setSpacing(8)
        rij_a.addWidget(self.knop_foto); rij_a.addWidget(self.knop_video_nu)
        kol.addLayout(rij_a)
        rij_b = QHBoxLayout(); rij_b.setSpacing(8)
        rij_b.addWidget(self.knop_map); rij_b.addWidget(self.knop_log)
        kol.addLayout(rij_b)
        kol.addSpacing(2)
        # e-mail (volle breedte i.v.m. lange tekst)
        kol.addWidget(self.chk_email)
        kol.addWidget(self.knop_email)
        kol.addSpacing(2)
        # live meekijken
        kol.addWidget(self.chk_stream)
        rij_live = QHBoxLayout(); rij_live.setSpacing(8)
        rij_live.addWidget(self.knop_live); rij_live.addWidget(self.knop_adres)
        kol.addLayout(rij_live)
        kol.addWidget(self.chk_extern)
        kol.addSpacing(2)
        # gebeurtenissen (krijgt de resterende ruimte)
        kol.addWidget(lbl_geb); kol.addWidget(self.log, 1)

        # donatie onderaan
        self.knop_don = QPushButton("\u2665 " + T("donatie"))
        self.knop_don.setToolTip("https://paypal.me/roger076")
        self.knop_don.clicked.connect(self._toon_donatie)
        kol.addWidget(self.knop_don)

        scroll = QScrollArea()
        scroll.setWidget(paneel)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(386)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        hoofd.addWidget(scroll)

        sb = QStatusBar(); self.setStatusBar(sb)

        if cv2 is None:
            self.knop_start.setEnabled(False)
            self.knop_zoek.setEnabled(False)
            self.beeld.setText(T("geen_cv2"))

    # -- gebeurtenissen --
    def _logbestand(self):
        return os.path.join(os.path.dirname(SNAPSHOT_MAP), "logboek.txt")

    def log_regel(self, tekst):
        nu = datetime.datetime.now()
        tijd = nu.strftime("%H:%M:%S")
        regel = "%s  %s" % (tijd, tekst)
        self.log.insertItem(0, regel)
        while self.log.count() > 200:
            self.log.takeItem(self.log.count() - 1)
        # ook naar extern logbestand (groot leesbaar in Kladblok)
        try:
            pad = self._logbestand()
            os.makedirs(os.path.dirname(pad), exist_ok=True)
            with open(pad, "a", encoding="utf-8") as f:
                f.write(nu.strftime("%Y-%m-%d ") + regel + "\n")
        except Exception:
            pass

    def open_logboek(self):
        pad = self._logbestand()
        try:
            os.makedirs(os.path.dirname(pad), exist_ok=True)
            if not os.path.exists(pad):
                with open(pad, "a", encoding="utf-8") as f:
                    f.write(datetime.datetime.now().strftime("%Y-%m-%d ") + T("log_start") + "\n")
            if sys.platform.startswith("win"):
                os.startfile(pad)  # noqa
            elif sys.platform == "darwin":
                os.system('open "%s"' % pad)
            else:
                os.system('xdg-open "%s"' % pad)
        except Exception:
            self.status().showMessage(pad)

    def zoek_cameras(self):
        self.status().showMessage(T("zoeken")); QApplication.processEvents()
        indices = CameraBron.zoek_cameras() if self._testbron is None else [0]
        self.combo.clear()
        if not indices:
            self.status().showMessage(T("geen_gevonden"))
            self.log_regel(T("geen_gevonden_hint"))
            self.beeld.setText(T("geen_gevonden_hint"))
            return
        for i in indices:
            self.combo.addItem("Camera %d" % i, i)
        self.status().showMessage(T("gevonden", n=len(indices)))
        self.log_regel(T("gevonden", n=len(indices)))

    def _auto_start(self):
        """Bij het opstarten: camera zoeken in een thread (UI blijft reageren), dan starten."""
        if cv2 is None or self._zoeker is not None:
            return
        self.knop_zoek.setEnabled(False)
        self.knop_start.setEnabled(False)
        self.status().showMessage(T("zoeken"))
        self._zoeker = CameraZoeker()
        self._zoeker.klaar.connect(self._zoeker_klaar)
        self._zoeker.start()

    def _zoeker_klaar(self, indices):
        self._zoeker = None
        self._verberg_banner()
        self.knop_zoek.setEnabled(True)
        self.knop_start.setEnabled(True)
        self.combo.clear()
        if not indices:
            self.status().showMessage(T("geen_gevonden"))
            self.log_regel(T("geen_gevonden_hint"))
            self.beeld.setText(T("geen_gevonden_hint"))
            return
        for i in indices:
            self.combo.addItem("Camera %d" % i, i)
        laatste = self.cfg.get("laatste_camera")
        if laatste in indices:
            self.combo.setCurrentIndex(max(0, self.combo.findData(laatste)))
        self.log_regel(T("gevonden", n=len(indices)))
        self._start()  # meteen live beeld
        # bewakingsapp: meteen bewaken (camera draait nu)
        if self._draait and not self._bewaking:
            self.wissel_bewaking()

    def start_stop(self):
        if self._draait:
            self._stop()
        else:
            self._start()

    def _start(self):
        if self._testbron is None:
            idx = self.combo.currentData()
            if idx is None:
                self.zoek_cameras()
                idx = self.combo.currentData()
            if idx is None:
                return
            if not self.bron.open(idx):
                self.status().showMessage(T("fout_open"))
                self.log_regel(T("fout_open"))
                return
            self.cfg["laatste_camera"] = idx
            bewaar_config(self.cfg)
            # fps van de camera bepalen (voor video-opname)
            self._fps = 20.0
            try:
                f = self.bron.cap.get(cv2.CAP_PROP_FPS)
                if f and 1.0 < f < 121.0:
                    self._fps = float(f)
            except Exception:
                pass
        self._vorige_grijs = None
        self._draait = True
        self._video_fout = False
        self.knop_start.setText(T("stop"))
        self.timer.start()
        self.status().showMessage(T("gestart")); self.log_regel(T("gestart"))

    def _stop(self):
        self.timer.stop()
        if self._recorder is not None:
            self._stop_opname()
        self.bron.sluit()
        self._draait = False
        self.knop_start.setText(T("start"))
        self.beeld.setText(T("geen_camera"))
        self.status().showMessage(T("gestopt")); self.log_regel(T("gestopt"))

    def wissel_bewaking(self):
        self._bewaking = not self._bewaking
        if self._bewaking:
            self.knop_bewaking.setText(T("bewaking_aan")); self.knop_bewaking.setObjectName("aan")
            self._video_fout = False
            self._mail_diag_vorig = None
            melding = T("bewaking_actief") + "  " + T("bij_beweging") + ": " + self._modus_label()
            if self.cfg.get("email_aan"):
                bijlage = self._email_bijlage()
                melding += "  |  " + T("email_aan_kort") + " (" + \
                    (T("bijlage_video") if bijlage == "video" else T("bijlage_foto")) + ")"
            else:
                melding += "  |  " + T("email_uit_kort")
            self.status().showMessage(melding); self.log_regel(melding)
        else:
            self.knop_bewaking.setText(T("bewaking_uit")); self.knop_bewaking.setObjectName("uit")
            self.status().showMessage(T("bewaking_gestopt")); self.log_regel(T("bewaking_gestopt"))
            if self._recorder is not None:
                self._stop_opname()
        # herlaad stijl voor objectName-wissel
        self.knop_bewaking.setStyleSheet("")
        self.setStyleSheet(STIJL())

    def _toon_banner(self, tekst):
        self.banner.setText(tekst)
        self.banner.adjustSize()
        self._plaats_banner()
        self.banner.show()
        self.banner.raise_()

    def _verberg_banner(self):
        self.banner.hide()

    def _plaats_banner(self):
        if not self.banner.isVisible() and not self.banner.text():
            return
        bx = max(10, (self.beeld.width() - self.banner.width()) // 2)
        self.banner.move(bx, 18)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._plaats_banner()

    def _modus_label(self):
        m = self.cfg.get("opname_modus", "beide")
        return {"foto": T("modus_foto"), "video": T("modus_video"),
                "beide": T("modus_beide")}.get(m, m)

    def _gevoeligheid_gewijzigd(self, waarde):
        self.gevoeligheid = waarde
        self.cfg["gevoeligheid"] = waarde
        bewaar_config(self.cfg)

    def _modus_gewijzigd(self, _idx):
        self.cfg["opname_modus"] = self.combo_modus.currentData()
        bewaar_config(self.cfg)

    def _geluid_gewijzigd(self, _state):
        self.cfg["geluid"] = self.chk_geluid.isChecked()
        bewaar_config(self.cfg)

    def _email_gewijzigd(self, _state):
        self.cfg["email_aan"] = self.chk_email.isChecked()
        bewaar_config(self.cfg)

    def _open_email_instellingen(self):
        dlg = EmailInstellingenDialoog(self, self.cfg)
        if dlg.exec():                       # opgeslagen -> schakelaar in lijn brengen
            self.chk_email.setChecked(bool(self.cfg.get("email_aan", False)))

    # -- live meekijken --
    def _stream_gewijzigd(self, _state):
        self.cfg["stream_aan"] = self.chk_stream.isChecked()
        bewaar_config(self.cfg)
        if self.chk_stream.isChecked():
            self._start_stream()
        else:
            self._stop_stream()

    def _start_stream(self):
        if self._stream is not None:
            return
        sleutel = self.cfg.get("stream_sleutel", "")
        voorkeur = int(self.cfg.get("stream_poort", 8080) or 8080)
        for p in [voorkeur, 8081, 8888, 8090]:
            try:
                srv = StreamServer(p, sleutel)
                srv.start()
                self._stream = srv
                self.cfg["stream_poort"] = p
                bewaar_config(self.cfg)
                link = self._stream_link()
                self.log_regel(T("stream_actief", url=link))
                self.status().showMessage(T("stream_actief", url=link))
                return
            except OSError:
                continue
        self.log_regel(T("stream_fout"))
        self.chk_stream.setChecked(False)

    def _stop_stream(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream = None
            self.log_regel(T("stream_gestopt"))

    def _stream_link(self, extern=False):
        if self._stream is None:
            return ""
        sleutel = self.cfg.get("stream_sleutel", "")
        if extern:
            host = (self.cfg.get("stream_extern_host") or "").strip() or self._pub_ip
            poort = int(self.cfg.get("stream_extern_poort", self._stream.poort) or self._stream.poort)
            if not host:
                return ""
        else:
            host = lan_ip()
            poort = self._stream.poort
        return "http://%s:%d/?sleutel=%s" % (host, poort, sleutel)

    def _extern_gewijzigd(self, _state):
        aan = self.chk_extern.isChecked()
        self.cfg["stream_extern"] = aan
        bewaar_config(self.cfg)
        if aan:
            if self._stream is None:
                self.chk_stream.setChecked(True)         # server moet draaien
            self._pub_timer.start()
            self._ververs_pub_ip()
            self.log_regel(T("stream_extern_aan"))
        else:
            self._pub_timer.stop()
            self.log_regel(T("stream_extern_uit"))

    def _ververs_pub_ip(self):
        """Haalt het publieke IP op in een achtergrondthread (blokkeert de UI niet)."""
        def werk():
            ip = publiek_ip(force=True)
            if ip and ip != self._pub_ip:
                self._pub_ip = ip
        threading.Thread(target=werk, daemon=True).start()

    def _open_live(self):
        if self._stream is None:
            self.chk_stream.setChecked(True)     # zet streaming aan
        link = self._stream_link()
        if not link:
            return
        try:
            import webbrowser
            webbrowser.open(link)
        except Exception:
            self.status().showMessage(link)
        self.log_regel(T("stream_actief", url=link))

    def _toon_adressen(self):
        if self._stream is None:
            self.chk_stream.setChecked(True)     # server moet draaien voor de poort/sleutel
        if not self._pub_ip:
            self._ververs_pub_ip()               # publiek IP alvast proberen op te halen
        poort = self._stream.poort if self._stream else int(self.cfg.get("stream_poort", 8080))
        AdressenDialoog(self, lan_ip(), self._pub_ip, poort,
                        self.cfg.get("stream_sleutel", "")).exec()

    def _mail_diag(self, reden):
        """Schrijft een mail-reden in het log, maar niet vaker dan 1x per 12s per reden."""
        nu = datetime.datetime.now()
        vorig = getattr(self, "_mail_diag_vorig", None)
        if vorig and vorig[0] == reden and (nu - vorig[1]).total_seconds() < 12:
            return
        self._mail_diag_vorig = (reden, nu)
        self.log_regel("E-mail: " + reden)

    def _mail_interval(self):
        try:
            return max(0, int(self.cfg.get("email_interval_min", 2))) * 60
        except (ValueError, TypeError):
            return 120

    def _email_bijlage(self):
        """Veilige bijlage-modus: alleen 'video' als echt zo ingesteld, anders 'foto'."""
        return "video" if self.cfg.get("email_bijlage") == "video" else "foto"

    def _misschien_mailen(self, frame):
        if not self._bewaking:
            return
        try:
            if not self.cfg.get("email_aan"):
                self._mail_diag(T("diag_uit")); return
            if self._email_bijlage() != "foto":
                self._mail_diag(T("diag_modus_video")); return   # mail komt na de clip
            if not (self.cfg.get("email_host") and self.cfg.get("email_naar")):
                self._mail_diag(T("diag_geen_server")); return
            nu = datetime.datetime.now()
            interval = self._mail_interval()
            if self._laatste_foto_mail and (nu - self._laatste_foto_mail).total_seconds() < interval:
                self._mail_diag(T("diag_wachttijd")); return
            self._laatste_foto_mail = nu
            rel = self._bewaar_foto(frame, nu)               # snapshot als bijlage
            bijlage = os.path.join(SNAPSHOT_MAP, rel)
            self._verstuur(T("email_onderwerp"),
                           T("email_tekst", tijd=nu.strftime("%Y-%m-%d %H:%M:%S")), bijlage)
        except Exception as e:
            self._mail_diag("fout - " + str(e))

    def _misschien_video_mailen(self, video_pad):
        if not self.cfg.get("email_aan"):
            return                                       # foto-pad logt dit al
        if self._email_bijlage() != "video":
            return
        try:
            if not self._bewaking:
                self._mail_diag(T("diag_bewaking_uit")); return
            if not (self.cfg.get("email_host") and self.cfg.get("email_naar")):
                self._mail_diag(T("diag_geen_server")); return
            if not (video_pad and os.path.exists(video_pad)):
                self._mail_diag(T("diag_geen_clip")); return
            nu = datetime.datetime.now()
            interval = self._mail_interval()
            if self._laatste_video_mail and (nu - self._laatste_video_mail).total_seconds() < interval:
                self._mail_diag(T("diag_wachttijd")); return
            grootte = os.path.getsize(video_pad)
            if grootte > 20 * 1024 * 1024:               # te groot voor de meeste mailservers
                self.log_regel(T("video_te_groot", mb=grootte // (1024 * 1024)))
                return
            self._laatste_video_mail = nu
            self._verstuur(T("email_onderwerp"),
                           T("email_tekst_video", tijd=nu.strftime("%Y-%m-%d %H:%M:%S")), video_pad)
        except Exception as e:
            self._mail_diag("fout - " + str(e))

    def _verstuur(self, onderwerp, tekst, bijlage):
        if self.cfg.get("stream_extern"):
            link = self._stream_link(extern=True)        # publieke link voor onderweg
            label = T("mail_live_link_extern")
            if not link:                                 # publiek IP nog niet bekend -> lokaal
                link = self._stream_link(); label = T("mail_live_link")
        else:
            link = self._stream_link(); label = T("mail_live_link")
        if link:
            tekst = tekst + "\n\n" + label + "\n" + link
        worker = MailWorker(self.cfg, onderwerp, tekst, bijlage)
        worker.klaar.connect(self._mail_klaar)
        self._mailers.append(worker)
        self.log_regel(T("email_bezig"))
        worker.start()

    def _mail_klaar(self, ok, fout):
        if ok:
            self.log_regel(T("email_verstuurd")); self.status().showMessage(T("email_verstuurd"))
        else:
            self.log_regel(T("email_mislukt", fout=fout))
            self.status().showMessage(T("email_mislukt", fout=fout))

    def _geluid_aan(self):
        return geluid_beschikbaar() and self.chk_geluid.isChecked() and self._testbron is None

    def _start_geluid(self):
        if not self._geluid_aan():
            return
        self._audio_chunks = []

        def terugroep(indata, frames, tijd, status):
            try:
                self._audio_chunks.append(indata.copy())
            except Exception:
                pass

        try:
            self._audio_stream = sd.InputStream(
                samplerate=AUDIO_SR, channels=AUDIO_KANALEN, dtype="float32",
                callback=terugroep)
            self._audio_stream.start()
            self._audio_actief = True
        except Exception:
            self._audio_stream = None
            self._audio_actief = False

    def _stop_geluid(self, basis_zonder_ext):
        """Stopt de microfoon en schrijft een WAV; geeft het wav-pad terug of None."""
        if not self._audio_actief:
            return None
        self._audio_actief = False
        try:
            self._audio_stream.stop(); self._audio_stream.close()
        except Exception:
            pass
        self._audio_stream = None
        wav_pad = basis_zonder_ext + ".wav"
        ok = schrijf_wav(wav_pad, self._audio_chunks)
        self._audio_chunks = []
        return wav_pad if ok else None

    def _mux_klaar(self, video_pad, audio_pad, uit_pad, ok):
        if uit_pad.startswith(SNAPSHOT_MAP):
            rel = os.path.relpath(uit_pad, SNAPSHOT_MAP)
        else:
            rel = os.path.basename(uit_pad)
        if ok:
            for p in (video_pad, audio_pad):     # losse beeld + geluid opruimen
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            self.log_regel(T("video_met_geluid", naam=rel))
            self.status().showMessage(T("video_met_geluid", naam=rel))
            self._misschien_video_mailen(uit_pad)
        else:
            try:
                if os.path.exists(audio_pad):
                    os.remove(audio_pad)
            except Exception:
                pass
            self.log_regel(T("geluid_mislukt"))
            self.status().showMessage(T("geluid_mislukt"))

    def _drempel(self):
        # hogere gevoeligheid -> lagere drempel (kleinere beweging telt al).
        # fractie van het beeld dat moet veranderen, ruwweg 0.05%..5%.
        return (101 - self.gevoeligheid) * 0.0005

    def _lees_frame(self):
        if self._testbron is not None:
            return self._testbron()
        return self.bron.lees()

    def _tick(self):
        frame = self._lees_frame()
        if frame is None:
            return
        # live beeld tonen
        pm = frame_naar_pixmap(frame, self.beeld.width() - 4, self.beeld.height() - 4)
        self.beeld.setPixmap(pm)

        # live meekijken: laatste beeld als JPEG aan de webserver geven
        if self._stream is not None and cv2 is not None:
            try:
                ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if ok:
                    self._stream.zet_frame(buf.tobytes())
            except Exception:
                pass

        # bewegingsdetectie
        grijs = naar_grijs_blur(frame)
        if self._vorige_grijs is not None and self._vorige_grijs.shape == grijs.shape:
            fractie = beweging_fractie(self._vorige_grijs, grijs)
            self.lbl_beweging.setText(T("beweging_pct", p=fractie * 100.0))
            beweging = fractie > self._drempel()
            if beweging:
                self._markeer_beweging(frame)
            self._auto_opname(frame, beweging)
        self._vorige_grijs = grijs
        # schrijf frames van een lopende opname (zowel automatisch als handmatig)
        self._schrijf_lopende_opname(frame)

    def _markeer_beweging(self, frame):
        self.lbl_beweging.setStyleSheet(f"color:{WARN}; font-weight:bold;")
        QTimer.singleShot(400, lambda: self.lbl_beweging.setStyleSheet(f"color:{MUTED};"))
        self._misschien_mailen(frame)
        modus = self.cfg.get("opname_modus", "beide")
        if self._bewaking and modus in ("foto", "beide"):
            nu = datetime.datetime.now()
            # cooldown van 3 seconden tussen automatische foto's
            if self._laatste_foto_tijd and (nu - self._laatste_foto_tijd).total_seconds() < 3:
                return
            naam = self._bewaar_foto(frame, nu)
            self._laatste_foto_tijd = nu
            self.log_regel(T("beweging") + " - " + naam)

    def _auto_opname(self, frame, beweging):
        """Start/verleng video-opname op basis van beweging (modus video/beide)."""
        modus = self.cfg.get("opname_modus", "beide")
        if cv2 is None or not self._bewaking or modus not in ("video", "beide") or self._video_fout:
            return
        if beweging:
            nu = datetime.datetime.now()
            if self._recorder is None:
                self._start_opname(frame, nu)
            if self._recorder is not None:
                self._rec_tail_tot = nu + datetime.timedelta(seconds=5)  # nog 5 s na beweging

    def _schrijf_lopende_opname(self, frame):
        """Schrijft frames naar een actieve opname en rondt af bij de stoptijd."""
        if self._recorder is None:
            return
        nu = datetime.datetime.now()
        h, w = frame.shape[:2]
        if (w, h) == self._rec_size:
            self._recorder.write(frame)
            self._rec_frames += 1
        duur = (nu - self._rec_start).total_seconds()
        if (self._rec_tail_tot and nu > self._rec_tail_tot) or duur > 60:
            self._stop_opname()

    def start_handmatige_video(self):
        """Neemt direct ~5 seconden op, los van beweging - handig om opnemen te testen."""
        if not self._draait:
            self.status().showMessage(T("eerst_starten"))
            return
        if self._recorder is not None:
            return
        frame = self._lees_frame()
        if frame is None:
            return
        self._video_fout = False
        nu = datetime.datetime.now()
        self._start_opname(frame, nu)
        if self._recorder is not None:
            self._rec_tail_tot = nu + datetime.timedelta(seconds=5)

    def _start_opname(self, frame, nu):
        h, w = frame.shape[:2]
        dagmap = os.path.join(SNAPSHOT_MAP, nu.strftime("%Y-%m-%d"))
        os.makedirs(dagmap, exist_ok=True)
        basis = nu.strftime("%H%M%S")
        fps = self._fps if 1.0 < self._fps < 121.0 else 20.0
        # MJPG/.avi werkt vrijwel altijd op Windows; daarna mp4v en XVID.
        kandidaten = [("MJPG", ".avi"), ("mp4v", ".mp4"), ("XVID", ".avi")]
        recorder = None
        pad = None
        gebruikte = ""
        for codec, ext in kandidaten:
            p = os.path.join(dagmap, basis + ext)
            try:
                vw = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*codec), fps, (w, h))
            except Exception:
                vw = None
            if vw is not None and vw.isOpened():
                recorder = vw; pad = p; gebruikte = codec; break
            if vw is not None:
                vw.release()
        if recorder is None:                 # geen enkele codec werkte
            self._video_fout = True
            self.status().showMessage(T("video_mislukt"))
            self.log_regel(T("video_mislukt"))
            return
        self._recorder = recorder
        self._rec_size = (w, h)
        self._rec_start = nu
        self._rec_frames = 0
        self._rec_volpad = pad
        self._rec_pad = os.path.join(nu.strftime("%Y-%m-%d"), os.path.basename(pad))
        self.lbl_opname.setText(T("opname_bezig"))
        self.log_regel(T("video_gestart") + " (" + gebruikte + ") -> " + pad)
        self._start_geluid()

    def _stop_opname(self):
        if self._recorder is None:
            if self._audio_actief:
                self._stop_geluid(os.path.splitext(self._rec_volpad or "audio")[0])
            return
        try:
            self._recorder.release()
        except Exception:
            pass
        self._recorder = None
        self._rec_tail_tot = None
        self.lbl_opname.setText("")

        volpad = getattr(self, "_rec_volpad", None)
        grootte = os.path.getsize(volpad) if (volpad and os.path.exists(volpad)) else 0
        wav = self._stop_geluid(os.path.splitext(volpad)[0]) if volpad else None

        if self._rec_frames > 0 and grootte > 1024:
            if wav:
                uit = os.path.splitext(volpad)[0] + ".mp4"
                self.status().showMessage(T("geluid_bezig"))
                self.log_regel(T("geluid_bezig"))
                mux = MuxWorker(volpad, wav, uit)
                mux.klaar.connect(self._mux_klaar)
                self._muxers.append(mux)
                mux.start()
            else:
                self.log_regel(T("video_opgeslagen", naam=self._rec_pad, n=self._rec_frames))
                self.status().showMessage(T("video_opgeslagen", naam=self._rec_pad, n=self._rec_frames))
                self._misschien_video_mailen(volpad)
        else:
            self._video_fout = True
            self.log_regel(T("video_leeg"))
            self.status().showMessage(T("video_leeg"))
        self.lbl_opname.setText("")

    def _bewaar_foto(self, frame, nu=None):
        nu = nu or datetime.datetime.now()
        dagmap = os.path.join(SNAPSHOT_MAP, nu.strftime("%Y-%m-%d"))
        os.makedirs(dagmap, exist_ok=True)
        naam = nu.strftime("%H%M%S_%f")[:-3] + ".jpg"
        pad = os.path.join(dagmap, naam)
        if cv2 is not None:
            cv2.imwrite(pad, frame)
        return os.path.join(nu.strftime("%Y-%m-%d"), naam)

    def handmatige_foto(self):
        frame = self._lees_frame()
        if frame is None:
            return
        naam = self._bewaar_foto(frame)
        self.status().showMessage(T("foto_opgeslagen", naam=naam))
        self.log_regel(T("foto_opgeslagen", naam=naam))
        # E-mail aan? Stuur deze foto meteen mee (betrouwbaar, los van beweging).
        if self.cfg.get("email_aan"):
            if self.cfg.get("email_host") and self.cfg.get("email_naar"):
                volpad = os.path.join(SNAPSHOT_MAP, naam)
                tijd = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._verstuur(T("email_onderwerp"), T("email_tekst", tijd=tijd), volpad)
            else:
                self._mail_diag(T("diag_geen_server"))

    def open_map(self):
        os.makedirs(SNAPSHOT_MAP, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(SNAPSHOT_MAP)  # noqa
            elif sys.platform == "darwin":
                os.system('open "%s"' % SNAPSHOT_MAP)
            else:
                os.system('xdg-open "%s"' % SNAPSHOT_MAP)
        except Exception:
            self.status().showMessage(SNAPSHOT_MAP)

    def _toon_donatie(self):
        from PyQt6.QtWidgets import QMessageBox
        b = QMessageBox(self); b.setWindowTitle(T("donatie"))
        b.setText("DraveSeCam is gratis (donationware).\n\nPayPal: https://paypal.me/roger076\n"
                  "E-mail: service@dravenlock.nl\n\nBedankt! - Kira en Dravenlock")
        b.setStyleSheet(STIJL()); b.exec()

    def closeEvent(self, e):
        self.timer.stop()
        self._stop_stream()
        if self._recorder is not None:
            self._stop_opname()
        if self._audio_actief:
            try:
                self._audio_stream.stop(); self._audio_stream.close()
            except Exception:
                pass
        for m in list(self._muxers):
            try:
                m.wait(8000)
            except Exception:
                pass
        for m in list(self._mailers):
            try:
                m.wait(8000)
            except Exception:
                pass
        if self._zoeker is not None:
            try:
                self._zoeker.wait(2000)
            except Exception:
                pass
        self.bron.sluit()
        super().closeEvent(e)


# ======================================================================
# Config + main
# ======================================================================
def laad_config():
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def bewaar_config(cfg):
    try:
        os.makedirs(DATA_MAP, exist_ok=True)
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def main():
    global _TAAL
    os.makedirs(DATA_MAP, exist_ok=True)
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Dravenlock.DraveSeCam")
        except Exception:
            pass
    cfg = laad_config()
    _TAAL = cfg.get("taal") or detecteer_taal()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAAM)
    app.setWindowIcon(app_icoon())
    venster = DraveSeCamVenster(cfg)
    venster.showMaximized()
    try:  # Dravenlock: stille update-check (uit te zetten; Ctrl+Shift+U = met de hand)
        import drave_update
        drave_update.start(venster, 'DraveSeCam', APP_VERSIE)
    except Exception:
        pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

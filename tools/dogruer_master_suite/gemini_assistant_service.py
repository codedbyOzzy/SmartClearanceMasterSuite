# -*- coding: utf-8 -*-
"""
gemini_assistant_service.py — SmartClearance Gemini Yapay Zeka Servisi
Gümrük, Dış Ticaret, Lojistik ve Mevzuat Asistanı Motoru
"""
import json
import os
import requests
from typing import List, Dict, Tuple, Optional
from tools.secrets_store import get_secret, set_secret

DEFAULT_SYSTEM_INSTRUCTION = (
    "Sen Doğruer Gümrük Müşavirliği - SmartClearance MasterSuite sisteminde yerleşik olarak görev yapan "
    "kıdemli bir Gümrük Müşaviri, Dış Ticaret Uzmanı ve Lojistik Yapay Zeka Asistanısın. "
    "Kullanıcının GTİP tespiti, gümrük rejimleri, ithalat/ihracat vergileri, ardiye, ordino, konşimento, "
    "Hankook operasyonları, kantar tartımları, beyanname süreçleri ve TAREKS/TSE mevzuatı gibi sorularına "
    "Türkçe, son derece profesyonel, net, maddeler halinde ve pratik çözümler sunarak yanıt ver."
)

class GeminiAssistantService:
    def __init__(self):
        self._history: List[Dict[str, str]] = []
        self._system_instruction = DEFAULT_SYSTEM_INSTRUCTION

    def get_api_key(self) -> str:
        return get_secret("gemini_api_key", "").strip()

    def set_api_key(self, key: str) -> bool:
        return set_secret("gemini_api_key", key)

    def clear_history(self):
        self._history = []

    def get_history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def ask(self, user_message: str) -> Tuple[bool, str]:
        """
        Kullanıcı mesajını Gemini API'ye gönderir ve yanıtı döndürür.
        Dönüş: (success: bool, response_or_error: str)
        """
        api_key = self.get_api_key()
        
        # Eğer API anahtarı girilmemişse bilgilendirici rehber yanıt dön
        if not api_key:
            simulated_reply = self._get_simulated_reply(user_message)
            self._history.append({"role": "user", "text": user_message})
            self._history.append({"role": "assistant", "text": simulated_reply})
            return True, simulated_reply

        # Gemini REST API çağrısı
        # Google'ın en güncel ve hızlı flash modelleri
        models_to_try = [
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
            "gemini-2.5-flash"
        ]
        
        # İçerik geçmişini API formatına hazırla
        contents = []
        for item in self._history[-8:]:  # Son 8 tur (bağlam sınırı)
            role = "user" if item["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": item["text"]}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        payload = {
            "system_instruction": {
                "parts": [{"text": self._system_instruction}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
                "topP": 0.8
            }
        }

        last_error = ""
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            reply_text = parts[0]["text"].strip()
                            self._history.append({"role": "user", "text": user_message})
                            self._history.append({"role": "assistant", "text": reply_text})
                            return True, reply_text
                    return False, "Gemini yanıt verdi ancak metin içeriği çözümlenemedi."
                elif resp.status_code in (400, 404):
                    # Model adı veya istek formatı hatası, sonraki modeli dene
                    try:
                        err_msg = resp.json().get("error", {}).get("message", resp.text)
                    except Exception:
                        err_msg = resp.text
                    last_error = f"API ({resp.status_code} - {model}): {err_msg}"
                    continue
                elif resp.status_code == 403:
                    return False, "Hata 403: Belirtilen Gemini API anahtarı geçersiz veya yetkisiz."
                else:
                    last_error = f"API Hatası ({resp.status_code}): {resp.text[:200]}"
                    continue
            except requests.exceptions.Timeout:
                last_error = "Zaman aşımı: Gemini API 30 saniye içinde yanıt vermedi."
            except Exception as ex:
                last_error = f"Bağlantı hatası: {str(ex)}"

        return False, last_error or "Gemini servisine ulaşılamadı."

    def _get_simulated_reply(self, query: str) -> str:
        q_lower = query.lower()
        if "gtip" in q_lower or "tarife" in q_lower or "lastik" in q_lower:
            return (
                "📢 [DEMO / TEST MODU]: Gemini API Key henüz girilmediği için yerleşik simülasyon yanıtı üretildi.\n\n"
                "🔍 GTİP & Mevzuat Analizi (Örnek):\n"
                "• Olası GTİP: 4011.10.00.00.00 (Otomobillerde kullanılan yeni dış lastikler)\n"
                "• Gümrük Vergisi: AB/EFTA ülkeleri için %0, Diğer ülkeler (Genel) için yaklaşık %4.5\n"
                "• İlgili Mevzuat: TAREKS (Ürün Güvenliği ve Denetimi) ve TSE Uygunluk Belgesi şartı bulunmaktadır.\n\n"
                "💡 Gerçek Gemini API ile anlık canlı analizler için yukarıdaki 'API Key' kutusuna anahtarınızı yapıştırıp 'Kaydet' butonuna basınız."
            )
        elif "ordino" in q_lower or "konşimento" in q_lower:
            return (
                "📢 [DEMO / TEST MODU]: Gemini API Key henüz girilmediği için yerleşik simülasyon yanıtı üretildi.\n\n"
                "📋 Konşimento (Bill of Lading) vs Ordino:\n"
                "1. Konşimento: Taşıyıcı (armatör) tarafından düzenlenen kıymetli evraktır, mülkiyeti temsil eder.\n"
                "2. Ordino (Teslim Emri): Acente/armatöre navlun ve lokal masraflar ödendikten sonra eşyanın gümrükten çekilmesine izin veren belgedir.\n\n"
                "💡 Gerçek Gemini API ile çalışmak için yukarıdaki kutudan API anahtarınızı tanımlayabilirsiniz."
            )
        else:
            return (
                f"📢 [DEMO / TEST MODU]: Sorunuz: '{query}'\n\n"
                "SmartClearance AI Asistan arayüzü başarıyla çalışıyor! 🚀\n"
                "Gemini API entegrasyonu tamamen hazırdır. Kendi Google Gemini API anahtarınızı yukarıdaki kutucuğa yapıştırıp 'Kaydet' dediğiniz anda, "
                "sistem Google'ın en yeni yapay zeka modelleriyle doğrudan canlı gümrük danışmanlığı yapmaya başlayacaktır."
            )


# Global tekil örnek
_assistant_service = None

def get_assistant_service() -> GeminiAssistantService:
    global _assistant_service
    if _assistant_service is None:
        _assistant_service = GeminiAssistantService()
    return _assistant_service

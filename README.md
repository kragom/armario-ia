---
title: Armario IA
emoji: 👕
colorFrom: pink
colorTo: purple
sdk: docker
pinned: false
---

# Armario IA 👗✨

Tu asistente personal de armario con inteligencia artificial.  
Sube fotos de tu ropa y recibe sugerencias de outfits basadas en el clima y tu horóscopo.

## Características

- 📸 **Sube fotos** de tus prendas — la IA las clasifica automáticamente
- 🎨 **Categorías**: superior, inferior, zapatos y accesorios
- 📝 **Notas personales** en cada prenda (¿dónde la compraste? ¿por qué te gusta?)
- 🤖 **Outfits generados por IA** según el clima y la ocasión
- 🌤️ **Recomendaciones basadas en el clima** (Open-Meteo, gratis)
- ⚡ **Imágenes ultrarrápidas**: WebP + miniaturas + caché
- 🌙 **Modo oscuro**
- 🇪🇸 **Interfaz en español**

## Configuración

1. Obtén una API Key de Gemini: https://aistudio.google.com/apikey
2. Abre la app → **Ajustes** → Configura:
   - **API Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai/`
   - **API Key**: tu clave de Gemini
   - **Modelo**: `gemini-2.0-flash`
3. ¡Añade tus prendas!

## Stack técnico

- **Frontend**: React + Vite + Tailwind CSS
- **Backend**: FastAPI (Python)
- **Base de datos**: SQLite
- **IA**: Google Gemini API (OpenAI-compatible)
- **Imágenes**: WebP con miniaturas + rembg
- **Despliegue**: Hugging Face Spaces (Docker)

---

**App en vivo**: [https://hectorpc19-armario-ia.hf.space](https://hectorpc19-armario-ia.hf.space)

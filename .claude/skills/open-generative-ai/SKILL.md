---
name: open-generative-ai
description: Install and set up Open Generative AI (github.com/Anil-matcha/Open-Generative-AI), a free MIT-licensed desktop app for image, video, lip sync and music generation with local open models. Use when the user asks to install, configure, or troubleshoot Open Generative AI, run local image or video models with it, or set up Wan2GP or sd.cpp for it.
---

# Open Generative AI setup

Free, open-source (MIT) desktop app with image, video, lip sync and music studios and 800+ models in one place. Open models run on the user's own computer with no credits. Large cloud models need a paid API key.

Repo: `github.com/Anil-matcha/Open-Generative-AI`

## 1. Install (about 2 minutes)

1. Open the repo's **Releases** page and download **v2.0.0** for the user's computer:
   - Mac M1 to M4: the `arm64.dmg`
   - Intel Mac: the plain `.dmg`
   - Windows: the `.exe`
   - Linux: the `.AppImage`
2. **Mac:** drag the app into Applications. The app is not notarized by Apple, so run this once in Terminal, then right-click the app and choose **Open**:
   ```
   xattr -cr "/Applications/Open Generative AI.app"
   ```
3. **Windows:** if SmartScreen warns, click **More info**, then **Run anyway**.
4. When it asks for an API key, skip it if the user only wants the free local models.

## 2. Free images on your own computer

1. Open **Settings > Local Models** and install the **sd.cpp** engine (one click). It runs on Mac M-series and on Windows or Linux GPUs.
2. Download a model. **Z-Image Turbo** is fast. **Dreamshaper 8** is the lightest tested on a Mac. Models are 2 to 7 GB.
3. In **Image Studio**, turn on the **Local** toggle next to the model picker and generate. No API key needed.

## 3. Free video (needs an NVIDIA or AMD GPU)

Install **Wan2GP** on a Windows or Linux machine with the GPU:

```
git clone https://github.com/deepbeepmeep/Wan2GP
cd Wan2GP
./install.sh
```

1. In the app, go to **Settings > Local Models > Wan2GP**: set the Wan2GP folder, click **Save**, then **Check**.
2. In **Video Studio**, switch to **Local** and pick **Wan 2.1 1.3B** (the lightest, about 8 GB of VRAM).

Local video does not run on Apple Silicon. On a Mac, point the app at Wan2GP running on a GPU machine, or use the cloud models.

## What is free and what is not

- **The app:** free and open source.
- **Local models:** no cost per generation. You pay only in disk space and your computer's power.
- **Cloud models** (Kling, Veo, Sora, Midjourney and more): need a paid Muapi API key, billed by Muapi.

## Troubleshooting notes

- Mac "cannot be opened" error: run the `xattr` command above, then open the app via right-click > Open.
- Windows SmartScreen block: More info > Run anyway.
- Video models fail on a Mac: expected. Use Wan2GP on a GPU machine or a cloud model.
- Wan2GP not detected: re-check the folder path in Settings > Local Models > Wan2GP and click **Check** again.

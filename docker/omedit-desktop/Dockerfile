FROM openmodelica-ai/omedit:1.27.1-qt6
RUN apt-get update && apt-get install -y --no-install-recommends qt6-wayland && rm -rf /var/lib/apt/lists/*
ENV QT_QPA_PLATFORM=wayland
ENV QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu
ENV QT_QUICK_BACKEND=software
CMD ["OMEdit"]

FROM ubuntu@sha256:61ebaa5cc23ca45450db85eac015435199ec569e28ec222ea13f2aed2110b8a6
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates
COPY openmodelica.asc /usr/share/keyrings/openmodelica.asc
COPY openmodelica.list /etc/apt/sources.list.d/openmodelica.list
RUN apt-get update && apt-get install -y --no-install-recommends omedit=1.27.1-1 omc=1.27.1-1 python3 xvfb xauth libgl1-mesa-dri && rm -rf /var/lib/apt/lists/*
ENV QTWEBENGINE_DISABLE_SANDBOX=1
ENV LIBGL_ALWAYS_SOFTWARE=1
CMD ["xvfb-run", "-a", "-s", "-screen 0 1280x900x24", "OMEdit"]

# mrf/Dockerfile

# =====================================================================
# Stage 1: Install all development tools, compile the C++ utilities,
# and create the Python virtual environment.
# =====================================================================
FROM almalinux:10 AS builder

# Build Arguments for the el9 GDAL RPM
ARG GDAL_VERSION=3.6.4
ARG GIBS_GDAL_RELEASE=3 #
ARG ALMALINUX_VERSION=10 #

# Install Build-time Dependencies
RUN dnf install -y epel-release dnf-plugins-core && \
    dnf config-manager --set-enabled crb && \
    dnf groupinstall -y "Development Tools" && \
    dnf install -y --allowerasing \
    cmake \
    git \
    python3-pip \
    python3-devel \
    libtiff-devel \
    sqlite-devel \
    wget \
    curl \
    geos \
    proj && \
    dnf clean all

# Install Pre-compiled GIBS GDAL for el9
RUN wget -P /tmp/ https://github.com/nasa-gibs/gibs-gdal/releases/download/v${GDAL_VERSION}/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    dnf install -y /tmp/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    rm -rf /tmp/*

# Download the missing private marfa.h header
RUN curl -L "https://raw.githubusercontent.com/OSGeo/gdal/v${GDAL_VERSION}/frmts/mrf/marfa.h" -o /usr/local/include/marfa.h

WORKDIR /app
COPY requirements.txt .
# Create the venv and install packages
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt
# Install the Python bindings for the installed GDAL version
RUN pip install GDAL==$(gdal-config --version)

# Copy the rest of the project files
COPY . .

# Build the C++ utilities
RUN cd mrf_apps && make

# Install the project itself into the venv
RUN pip install -e .

# =====================================================================
# Stage 2:  Minimal, distributable image.
# =====================================================================
FROM almalinux:10

# Install only Runtime Dependencies
RUN dnf install -y epel-release dnf-plugins-core && \
    dnf config-manager --set-enabled crb && \
    dnf install -y --allowerasing python3 wget geos proj && \
    dnf clean all

# Install the el10 GDAL RPM for its runtime libraries
ARG GDAL_VERSION=3.6.4
ARG GIBS_GDAL_RELEASE=3
ARG ALMALINUX_VERSION=10
RUN wget -P /tmp/ https://github.com/nasa-gibs/gibs-gdal/releases/download/v${GDAL_VERSION}/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    dnf install -y /tmp/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    rm -rf /tmp/*

# Tell the linker where to find the new libraries
# Create a new configuration file for the dynamic linker
RUN echo "/usr/local/lib" > /etc/ld.so.conf.d/gdal-custom.conf

# Update the shared library cache
RUN ldconfig

WORKDIR /app

# Copy Artifacts from the "builder" Stage
COPY --from=builder /app/mrf_apps/can /usr/local/bin/
COPY --from=builder /app/mrf_apps/jxl /usr/local/bin/
COPY --from=builder /app/mrf_apps/mrf_insert /usr/local/bin/
COPY --from=builder /app/venv /app/venv
COPY mrf_apps/ ./mrf_apps/
COPY pyproject.toml .
COPY README.md .

# Set Final Environment Variables
ENV PATH="/app/venv/bin:$PATH"
ENV GDAL_DATA="/usr/local/share/gdal"

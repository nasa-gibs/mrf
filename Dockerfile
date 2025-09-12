# mrf/Dockerfile
# This file builds the base application image containing all utilites and the Python virtual environment.

# =========================================================================
# Stage 1: compiles the C++ utilities and the Python virtual environment.
# =========================================================================
# Start from a base image with AlmaLinux 10.
FROM almalinux:10 AS builder

# --- Build Arguments for the x86_64 GDAL RPM ---
ARG GDAL_VERSION=3.6.4
ARG GIBS_GDAL_RELEASE=3
ARG ALMALINUX_VERSION=10

# --- Install Dependencies ---
RUN dnf install -y epel-release && \
    dnf groupinstall -y "Development Tools" && \
    dnf install -y \
    cmake \
    git \
    python3 \
    python3-pip \
    python3-devel \
    libtiff-devel \
    sqlite-devel \
    wget \
    curl && \
    dnf clean all

# Install Pre-compiled GIBS GDAL
ENV LD_LIBRARY_PATH=/usr/local/lib
RUN wget -P /tmp/ https://github.com/nasa-gibs/gibs-gdal/releases/download/v${GDAL_VERSION}-${GIBS_GDAL_RELEASE}/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    dnf install -y /tmp/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    rm -rf /tmp/*

# Download the missing private marfa.h header
# This file is required by mrf_insert but not included in the GDAL RPM.
RUN curl -L "https://raw.githubusercontent.com/OSGeo/gdal/v${GDAL_VERSION}/frmts/mrf/marfa.h" -o /usr/local/include/marfa.h

# Set the main working directory for the application.
WORKDIR /app

# Copy project files.
COPY . .

# Build the C++ utilities, which will link against the RPM-installed GDAL.
RUN cd mrf_apps && make

# Create and populate Python virtual environment and set the PATH.
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:/app/mrf_apps:$PATH"
# Tell GDAL where to find its data files.
ENV GDAL_DATA="/usr/local/share/gdal"

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e .

# =====================================================================
# Stage 2: creates clean distributable image
# =====================================================================
FROM almalinux:10

# Install only Runtime Dependencies
RUN dnf install -y python3 wget && dnf clean all

ARG GDAL_VERSION=3.6.4
ARG GIBS_GDAL_RELEASE=3
ARG ALMALINUX_VERSION=10
RUN wget -P /tmp/ https://github.com/nasa-gibs/gibs-gdal/releases/download/v${GDAL_VERSION}-${GIBS_GDAL_RELEASE}/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    dnf install -y /tmp/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    rm -rf /tmp/*

WORKDIR /app

# Copy Artifacts from Stage 1
COPY --from=builder /app/mrf_apps/can /usr/local/bin/
COPY --from=builder /app/mrf_apps/jxl /usr/local/bin/
COPY --from=builder /app/mrf_apps/mrf_insert /usr/local/bin/
COPY --from=builder /app/venv /app/venv
COPY . .

# Set Final Environment Variables
ENV PATH="/app/venv/bin:$PATH"
ENV GDAL_DATA="/usr/local/share/gdal"

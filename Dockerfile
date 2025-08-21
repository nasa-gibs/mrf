# Dockerfile

# Start from a base image with AlmaLinux 10.
FROM almalinux:10

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

# --- Install Pre-compiled GIBS GDAL ---
ENV LD_LIBRARY_PATH=/usr/local/lib
RUN wget -P /tmp/ https://github.com/nasa-gibs/gibs-gdal/releases/download/v${GDAL_VERSION}-${GIBS_GDAL_RELEASE}/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    dnf install -y /tmp/gibs-gdal-${GDAL_VERSION}-${GIBS_GDAL_RELEASE}.el${ALMALINUX_VERSION}.x86_64.rpm && \
    rm -rf /tmp/*

# --- ADDED STEP: Download the missing private marfa.h header ---
# This file is required by mrf_insert but not included in the GDAL RPM.
RUN curl -L "https://raw.githubusercontent.com/OSGeo/gdal/v${GDAL_VERSION}/frmts/mrf/marfa.h" -o /usr/local/include/marfa.h

# Set the main working directory for the application.
WORKDIR /app

# Copy your project files.
COPY . .

# Build the C++ utilities, which will link against the RPM-installed GDAL.
RUN cd mrf_apps && make

# Create a Python virtual environment and set the PATH.
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:/app/mrf_apps:$PATH"
# Tell GDAL where to find its data files.
ENV GDAL_DATA="/usr/local/share/gdal"

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e .

# Define the default command to run when the container starts.
CMD ["pytest"]

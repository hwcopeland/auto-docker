# Base image for building
FROM ubuntu:20.04 AS builder
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
WORKDIR /autodock/

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    git \
    cmake \
    libnetcdf-dev \
    libboost-all-dev 

# Download AutoDock4
ADD https://autodock.scripps.edu/wp-content/uploads/sites/56/2021/10/autodocksuite-4.2.6-x86_64Linux2.tar ./ 
RUN tar xf autodocksuite-4.2.6-x86_64Linux2.tar

# Runtime image
FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Increase file limit
RUN ulimit -n 65536

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    wget \
    openbabel \
    nano \
    parallel \
    libnetcdf-dev \
    libboost-filesystem-dev \
    libboost-system-dev \
    libboost-program-options-dev \
    python3 \
    python3-pip \
    libpython2.7

WORKDIR /autodock/
# Copy binaries from builder stage
COPY --from=builder /autodock/x86_64Linux2/autogrid4 ./autogrid4
COPY --from=builder /usr/local/lib/libfpocket.so* /usr/local/lib/
RUN ldconfig

# Install python2.7 pip2
RUN wget https://bootstrap.pypa.io/pip/2.7/get-pip.py


# Download and install MGLTools
COPY mgltools_x86_64Linux2_1.5.7p1.tar.gz ./ 
RUN tar xzf mgltools_x86_64Linux2_1.5.7p1.tar.gz \
    && mv mgltools_x86_64Linux2_1.5.7/ mgltools/ \
    && cd mgltools/ \
    && ./install.sh
RUN rm mgltools_x86_64Linux2_1.5.7p1.tar.gz


# Install Python3 dependencies
COPY requirements.txt ./ 
RUN pip3 install --no-cache-dir -r requirements.txt 

# Copy script files
ADD scripts/ ./scripts/

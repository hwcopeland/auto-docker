FROM ubuntu:20.04 AS builder
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
WORKDIR /autodock/

# Install necessary build tools and dependencies for fpocket
RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    git \
    cmake \
    libnetcdf-dev \
    libboost-all-dev 

# Download AutoDock4 (for autogrid4)
ADD https://autodock.scripps.edu/wp-content/uploads/sites/56/2021/10/autodocksuite-4.2.6-x86_64Linux2.tar ./
RUN tar xf autodocksuite-4.2.6-x86_64Linux2.tar

# Download AutoDock Vina (CPU version)
ADD https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.5/vina_1.2.5_linux_x86_64 ./vina
RUN chmod +x vina

# Download and install fpocket
WORKDIR /autodock/fpocket/
RUN git clone https://github.com/Discngine/fpocket.git . \
    && make \
    && make install

FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Increase file limit
RUN ulimit -n 65536

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    wget \
    openbabel \
    parallel \
    libnetcdf-dev \
    libboost-filesystem-dev \
    libboost-system-dev \
    libboost-program-options-dev \
    python3 \
    python3-pip

WORKDIR /autodock/
# Copy Vina and AutoGrid from builder stage
COPY --from=builder /autodock/vina ./vina
COPY --from=builder /autodock/x86_64Linux2/autogrid4 ./autogrid4

# Copy fpocket binaries and libraries from builder stage
COPY --from=builder /usr/local/bin/fpocket /usr/local/bin/fpocket
COPY --from=builder /usr/local/bin/dpocket /usr/local/bin/dpocket
COPY --from=builder /usr/local/bin/tpocket /usr/local/bin/tpocket
COPY --from=builder /usr/local/lib/libfpocket.so* /usr/local/lib/
RUN ldconfig

# Download and install MGLTools
COPY mgltools_x86_64Linux2_1.5.7p1.tar.gz ./
RUN tar xzf mgltools_x86_64Linux2_1.5.7p1.tar.gz \
    && mv mgltools_x86_64Linux2_1.5.7/ mgltools/ \
    && cd mgltools/ \
    && ./install.sh
RUN rm mgltools_x86_64Linux2_1.5.7p1.tar.gz

# Install Python dependencies from requirements.txt
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy script files
ADD scripts/ ./scripts/
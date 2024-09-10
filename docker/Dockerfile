FROM nvidia/cuda:11.2.0-devel-ubuntu20.04 AS builder
WORKDIR /autodock/
RUN apt-get update && apt-get install -y wget

# download AutoDock4 (for autogrid4)
ADD https://autodock.scripps.edu/wp-content/uploads/sites/56/2021/10/autodocksuite-4.2.6-x86_64Linux2.tar ./
RUN tar xf autodocksuite-4.2.6-x86_64Linux2.tar

# download AutoDock-GPU source, and build it
ADD https://github.com/ccsb-scripps/AutoDock-GPU/archive/refs/tags/v1.5.3.tar.gz ./
RUN \
    tar xzf v1.5.3.tar.gz \
    && cd AutoDock-GPU-1.5.3/ \
    && GPU_LIBRARY_PATH=/usr/local/cuda/lib64 GPU_INCLUDE_PATH=/usr/local/cuda/include make DEVICE=GPU NUMWI=64


FROM nvidia/cuda:11.2.0-runtime-ubuntu20.04
RUN apt-get update && apt-get install -y wget openbabel
WORKDIR /autodock/
COPY --from=builder /autodock/AutoDock-GPU-1.5.3/bin/autodock_gpu_64wi ./autodock_gpu
COPY --from=builder /autodock/x86_64Linux2/autogrid4 ./autogrid4

# download and install mgltools
ADD https://ccsb.scripps.edu/mgltools/download/491/ ./
RUN tar xzf mgltools_x86_64Linux2_1.5.7p1.tar.gz \
    && mv mgltools_x86_64Linux2_1.5.7/ mgltools/ \
    && cd mgltools/ \
    && ./install.sh
RUN rm mgltools_x86_64Linux2_1.5.7p1.tar.gz

ADD scripts/ ./scripts/

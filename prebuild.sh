# install ansible and undocumented AVD requirements
pip install ansible netaddr paramiko deepmerge cvprac md-toc

ansible-galaxy collection install arista.avd

# Install containerlab
bash -c "$(curl -sL https://get.containerlab.dev)"

# Download and import CEOS
git lfs pull
docker import ceos.tar ceosimage:4.29.0.2F

# Fetch AVD labs, build host emulator image
git clone https://github.com/arista-netdevops-community/avd-cEOS-Lab

# Clone infrahub
git clone -b develop https://github.com/opsmill/infrahub.git

cd avd-cEOS-Lab/alpine_host
chmod +x build.sh
./build.sh

cd ../..

pip install poetry toml

cd infrahub

poetry install

poetry run invoke demo.build

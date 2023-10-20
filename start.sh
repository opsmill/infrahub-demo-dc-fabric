pip install ansible
ansible-galaxy collection install arista.av
bash -c "$(curl -sL https://get.containerlab.dev)"

curl https://www.arista.com/surl/kc3FX6Rv0v --output ceos.tar.xz
docker import ceos.tar.xz ceosimage:4.29.0.2F

git clone https://github.com/arista-netdevops-community/avd-cEOS-Lab

cd avd-cEOS-Lab/alpine_host && chmod +x build.sh && ./build.sh

cd ../..

sudo containerlab deploy -t avd-cEOS-Lab/labs/evpn/avd_asym_irb/topology.yaml

ansible-playbook avd-cEOS-Lab/labs/evpn/avd_asym_irb/playbooks/fabric-deploy-config.yaml --inventory avd-cEOS-Lab/labs/evpn/avd_asym_irb/inventory.yaml

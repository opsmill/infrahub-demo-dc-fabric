pip install ansible
ansible-galaxy collection install arista.avd
bash -c "$(curl -sL https://get.containerlab.dev)"

git lfs pull
docker import ceos.tar ceosimage:4.29.0.2F

git clone https://github.com/arista-netdevops-community/avd-cEOS-Lab

cd avd-cEOS-Lab/alpine_host
chmod +x build.sh
./build.sh

cd ../..

sudo containerlab deploy -t avd-cEOS-Lab/labs/evpn/avd_asym_irb/topology.yaml

ansible-playbook avd-cEOS-Lab/labs/evpn/avd_asym_irb/playbooks/fabric-deploy-config.yaml --inventory avd-cEOS-Lab/labs/evpn/avd_asym_irb/inventory.yaml

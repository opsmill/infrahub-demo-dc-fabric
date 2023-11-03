cd infrahub

# Stand up infrahub, loading schema (memgraph should be stable after containerlab deploys)
poetry run invoke demo.init

cd ..

docker login --username $HARBOR_USERNAME --password $HARBOR_PASSWORD $HARBOR_HOST

# Deploy the lab!
sudo containerlab deploy -t topology/demo.clab.yml

cd infrahub

# Start infrahub
poetry run invoke demo.start

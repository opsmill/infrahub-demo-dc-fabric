# infrahub-demo-dc-fabric

![infrahub-demo-dc-fabric drawing](./infrahub-demo-dc-fabric.excalidraw.svg)

## Playbook

### 1. Set env vars if needed
```
export INFRAHUB_ADDRESS="http://localhost:8000"
export INFRAHUB_API_TOKEN="06438eb2-8019-4776-878c-0941b1f1d1ec"
```
### 2. Startup empty DB
```
invoke demo.destroy demo.build demo.init demo.start 
```
### 3. Log into UI
### 4. Paste API key
```
mutation {
  CoreRepositoryCreate(
    data: {
      name: { value: "naf-demo" }
      location: { value: "https://github.com/fooelisa/infrahub-demo-dc-fabric.git" }
      username: { value: "fooelisa" }
      password: { value: "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" }
    }
  ) {
    ok
    object {
      id
    }
  }
}
```
### 5. Show schema extensibility
```
infrahubctl schema load infrastructure_topology.yml
```
### 6. Load in topology data only
```
infrahubctl run infrastructure_topology.py
```
### 7. Load in first pod of devices 
```
infrahubctl run infrastructure_devices.py
```
### 8. Rfiles
```
infrahubctl render device_startup device=atl-spine1
```
### 9. Show a proposed change
  - All checks here should pass
### 10. Show a check 
  - Delete a device via the UI
  - Create a PC
  - Check should fail now
### 11. Load in second pod of devices
```
infrahubctl run infrastructure_devices_2.py
```
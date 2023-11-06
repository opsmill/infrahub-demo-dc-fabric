# naf-demo

![naf demo drawing](./naf-demo.excalidraw.svg)

```
mutation {
  CoreRepositoryCreate(
    data: {
      name: { value: "naf-demo" }
      location: { value: "https://github.com/fooelisa/naf-demo.git" }
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
